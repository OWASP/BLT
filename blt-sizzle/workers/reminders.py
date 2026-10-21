"""Daily check-in reminder rules: when a reminder is due, and what the email says.

Pure Python so it runs the same in the Workers runtime and in local tests. The only
runtime-specific piece is the timezone conversion: Pyodide ships ``zoneinfo`` without
the tz database, so ``to_local`` falls back to the JavaScript ``Intl`` API there.
"""

import html
import re
from datetime import datetime, timedelta, timezone

try:
    from zoneinfo import ZoneInfo
except Exception:  # pragma: no cover
    ZoneInfo = None


# ISO weekdays: Monday = 1 ... Sunday = 7 (datetime.isoweekday()).
ALL_DAYS = (1, 2, 3, 4, 5, 6, 7)
DEFAULT_DAYS = "1,2,3,4,5,6,7"
DAY_NAMES = {1: "Mon", 2: "Tue", 3: "Wed", 4: "Thu", 5: "Fri", 6: "Sat", 7: "Sun"}

# A reminder is sent on the first scheduler run at or after its local time, as long as
# that run is no later than this. blt-cron calls every 15 minutes, so the window covers
# a few missed runs without sending a 09:00 reminder in the evening.
GRACE_MINUTES = 120

_TIME_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


def parse_days(value):
    """'1,2,3' (or None/'' for the column default) -> sorted tuple of ISO weekdays."""
    if value is None or str(value).strip() == "":
        return ALL_DAYS
    days = set()
    for part in str(value).split(","):
        part = part.strip()
        if part.isdigit() and 1 <= int(part) <= 7:
            days.add(int(part))
    return tuple(sorted(days))


def normalize_days(value):
    """Validate days from the settings API (list of ints/strings, or a comma string).

    Returns the canonical column value ('1,2,3,4,5,6'). Raises ValueError on anything
    outside 1-7 or an empty selection.
    """
    if value is None:
        return DEFAULT_DAYS
    if isinstance(value, str):
        items = [item for item in value.split(",") if item.strip() != ""]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        raise ValueError("Invalid reminder days")
    days = set()
    for item in items:
        if isinstance(item, bool):
            raise ValueError("Invalid reminder days")
        try:
            day = int(str(item).strip())
        except ValueError:
            raise ValueError("Invalid reminder days")
        if day < 1 or day > 7:
            raise ValueError("Invalid reminder days")
        days.add(day)
    if not days:
        raise ValueError("Choose at least one reminder day")
    return ",".join(str(day) for day in sorted(days))


def parse_time(value):
    match = _TIME_RE.match(str(value or "").strip())
    if not match:
        raise ValueError("Invalid notification time")
    hour, minute = int(match.group(1)), int(match.group(2))
    if hour > 23 or minute > 59:
        raise ValueError("Invalid notification time")
    return hour, minute


def _js_local_parts(now_utc, tz_name):  # pragma: no cover - Workers runtime only
    from js import Date, Intl, Object
    from pyodide.ffi import to_js

    options = to_js({
        "timeZone": tz_name,
        "hourCycle": "h23",
        "year": "numeric",
        "month": "2-digit",
        "day": "2-digit",
        "hour": "2-digit",
        "minute": "2-digit",
        "second": "2-digit",
    }, dict_converter=Object.fromEntries)
    formatter = Intl.DateTimeFormat.new("en-US", options)
    parts = formatter.formatToParts(Date.new(int(now_utc.timestamp() * 1000)))
    values = {}
    for part in parts:
        values[str(part.type)] = str(part.value)
    hour = int(values["hour"]) % 24
    return datetime(int(values["year"]), int(values["month"]), int(values["day"]),
                    hour, int(values["minute"]), int(values["second"]))


def to_local(now_utc, tz_name):
    """Wall-clock time (naive datetime) in tz_name for an aware UTC datetime."""
    if now_utc.tzinfo is None:
        now_utc = now_utc.replace(tzinfo=timezone.utc)
    tz_name = tz_name or "UTC"
    if tz_name == "UTC":
        return now_utc.astimezone(timezone.utc).replace(tzinfo=None)
    if ZoneInfo is not None:
        try:
            return now_utc.astimezone(ZoneInfo(tz_name)).replace(tzinfo=None)
        except Exception:
            pass
    return _js_local_parts(now_utc, tz_name)


def reminder_due(now_utc, tz_name, notification_time, days, last_reminder_date,
                 grace_minutes=GRACE_MINUTES, local_now=None):
    """Decide whether a user's reminder should go out on this run.

    Returns (due, local_date_iso, reason). ``last_reminder_date`` is the user's local
    date of the last reminder already claimed, so a second run on the same local day
    (another cron tick, a DST fall-back hour that repeats) never sends twice.
    """
    local = local_now or to_local(now_utc, tz_name)
    local_date = local.date().isoformat()
    try:
        hour, minute = parse_time(notification_time or "09:00")
    except ValueError:
        return False, local_date, "bad_time"
    if local.isoweekday() not in parse_days(days):
        return False, local_date, "day_off"
    scheduled = local.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if local < scheduled:
        return False, local_date, "not_yet"
    # On a spring-forward day a 02:30 reminder has no wall-clock instant; the first
    # run after the gap (03:00) is still inside the window, so it goes out then.
    if local - scheduled > timedelta(minutes=grace_minutes):
        return False, local_date, "window_passed"
    if last_reminder_date and str(last_reminder_date) == local_date:
        return False, local_date, "already_sent"
    return True, local_date, "due"


def describe_days(days):
    days = parse_days(days)
    if days == ALL_DAYS:
        return "every day"
    if days == (1, 2, 3, 4, 5):
        return "Monday to Friday"
    if days == (1, 2, 3, 4, 5, 6):
        return "Monday to Saturday"
    return ", ".join(DAY_NAMES[d] for d in days)


def render_reminder_email(app_url, display_name="", local_date="", notification_time="",
                          days=None, tz_name=""):
    """Return (subject, html, text) for a daily check-in reminder."""
    base = (app_url or "").rstrip("/")
    checkin_url = base + "/app"
    settings_url = base + "/settings"
    name = str(display_name or "").strip()
    greeting = f"Hi {name}," if name else "Hi,"
    when = ""
    if notification_time:
        when = f"{notification_time}"
        if tz_name:
            when += f" ({tz_name})"
        if days is not None:
            when += f", {describe_days(days)}"
    subject = "Daily check-in reminder" + (f" for {local_date}" if local_date else "")

    e = html.escape
    schedule_line_html = (
        f'<p style="margin:0;color:#64748b;font-size:13px;line-height:1.6;">You get this reminder at {e(when)}.</p>'
        if when else ""
    )
    html_body = f"""<!doctype html>
<html lang="en">
  <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(subject)}</title></head>
  <body style="margin:0;background:#f8fafc;font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#0f172a;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;padding:32px 16px;">
      <tr><td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;">
          <tr><td style="padding:28px 28px 8px;">
            <p style="margin:0 0 10px;color:#dc2626;font-size:12px;font-weight:800;letter-spacing:.16em;text-transform:uppercase;">BLT Sizzle</p>
            <h1 style="margin:0;font-size:24px;line-height:1.3;color:#111827;">Time for your daily check-in</h1>
            <p style="margin:16px 0 0;color:#475569;font-size:15px;line-height:1.6;">{e(greeting)} take a few minutes to note what you finished, what you plan to do today, and anything blocking you.</p>
          </td></tr>
          <tr><td style="padding:20px 28px;">
            <a href="{e(checkin_url)}" style="display:inline-block;background:#dc2626;color:#ffffff;text-decoration:none;font-weight:700;padding:12px 22px;border-radius:10px;">Fill in today's check-in</a>
            <p style="margin:12px 0 0;color:#64748b;font-size:13px;">Or open {e(checkin_url)}</p>
          </td></tr>
          <tr><td style="padding:0 28px 28px;">
            {schedule_line_html}
            <p style="margin:8px 0 0;color:#64748b;font-size:13px;line-height:1.6;">To change the time or days, or to stop these emails, go to <a href="{e(settings_url)}" style="color:#dc2626;">your reminder settings</a>.</p>
          </td></tr>
        </table>
      </td></tr>
    </table>
  </body>
</html>"""

    text_lines = [
        "Time for your daily check-in",
        "",
        f"{greeting} take a few minutes to note what you finished, what you plan to do today, and anything blocking you.",
        "",
        f"Fill in today's check-in: {checkin_url}",
        "",
    ]
    if when:
        text_lines.append(f"You get this reminder at {when}.")
    text_lines.append(f"To change the time or days, or to stop these emails: {settings_url}")
    text_lines += ["", "-- ", "BLT Sizzle"]
    return subject, html_body, "\n".join(text_lines) + "\n"
