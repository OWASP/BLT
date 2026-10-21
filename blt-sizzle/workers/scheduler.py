"""
Scheduled daily check-in reminders.

blt-cron calls POST /__scheduled every 15 minutes (see blt-cron/src/jobs.js), and main.py
passes the event here. Each run:

1. loads users with reminders on;
2. works out, in each user's own timezone, whether their reminder time has come today
   and today is one of their reminder days (reminders.reminder_due);
3. skips users who already checked in today;
4. claims the day by setting users.last_reminder_date with a conditional UPDATE, so two
   runs (or a repeated DST hour) can never send twice;
5. sends email and/or Slack, each retried at most once, and records the outcome.
"""

import base64
import json
import logging
import sys
from datetime import datetime, timezone

from email_service import EmailService, http_post, mask_emails
from reminders import reminder_due, render_reminder_email
from url_safety import is_slack_webhook_url

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

# One consolidated Slack message per org, once a day at this UTC hour (ORG_NOTIFICATION_HOUR).
DEFAULT_ORG_HOUR = 9


def _decrypt_simple(encrypted_data):
    """Mirror of main.decrypt_data (base64 payload after an 'iv:' prefix)."""
    if not encrypted_data:
        return ''
    try:
        parts = encrypted_data.split(':')
        if len(parts) != 2:
            return encrypted_data
        return base64.b64decode(parts[1]).decode('utf-8')
    except Exception:
        return encrypted_data


def _rows(result_proxy):
    result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
    if isinstance(result, dict):
        return result.get('results', []) or []
    return []


def _changes(result_proxy):
    result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
    if isinstance(result, dict):
        if 'changes' in result:
            return int(result.get('changes') or 0)
        meta = result.get('meta')
        if isinstance(meta, dict):
            return int(meta.get('changes') or 0)
    return 0


def _event_time(event):
    """UTC datetime for this run: the dispatcher's scheduledTime, else now."""
    try:
        ms = int(getattr(event, 'scheduledTime', None))
        return datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
    except (TypeError, ValueError, OverflowError, OSError):
        return datetime.now(timezone.utc)


def app_url(env):
    host = str(getattr(env, 'APP_URL', '') or getattr(env, 'WORKER_HOST', '') or '').strip()
    if not host:
        return "https://sizzle.owaspblt.org"
    if not host.startswith("http://") and not host.startswith("https://"):
        host = "https://" + host
    return host.rstrip("/")


def reminder_email_address(user):
    """Address for reminder email: a verified sign-in email, else the GitHub email on file."""
    email = str(user.get('email') or '').strip()
    if email and int(user.get('email_verified') or 0) == 1:
        return email
    legacy = _decrypt_simple(user.get('encrypted_email') or '').strip()
    if legacy and '@' in legacy:
        return legacy
    return ''


def slack_reminder_message(checkin_url, settings_url, test=False):
    title = "Test reminder" if test else "Daily check-in reminder"
    return {
        "text": f"{title}: time for your daily check-in {checkin_url}",
        "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": (
                f"*{title}*\nTake a few minutes to note what you finished, what you plan "
                "to do today, and anything blocking you."
            )}},
            {"type": "actions", "elements": [{
                "type": "button",
                "text": {"type": "plain_text", "text": "Fill in today's check-in"},
                "style": "primary",
                "url": checkin_url,
                "action_id": "checkin_button",
            }]},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": f"<{settings_url}|Change reminder settings>"}]},
        ],
    }


async def send_slack(webhook_url, message, post=None, max_attempts=2):
    """POST to a Slack webhook (hooks.slack.com only), retrying a transient failure once."""
    if not is_slack_webhook_url(webhook_url):
        return {"success": False, "status": 0, "attempts": 0, "error": "Slack webhook URL is not allowed."}
    post = post or http_post
    status = 0
    for attempt in range(1, max_attempts + 1):
        status, _ = await post(webhook_url, {"Content-Type": "application/json"}, json.dumps(message))
        if 200 <= status < 300:
            return {"success": True, "status": status, "attempts": attempt, "error": ""}
        if not (status in (0, 408, 429) or status >= 500):
            break
    return {"success": False, "status": status, "attempts": attempt, "error": f"Slack returned status {status}."}


async def send_reminder(env, user, local_date, email_service=None, slack_post=None, test=False):
    """Send one user's reminder on every channel they turned on. Returns per-channel results."""
    base = app_url(env)
    results = {}
    if int(user.get('email_notifications') or 0) == 1:
        address = reminder_email_address(user)
        if address:
            service = email_service or EmailService.from_env(env)
            subject, html_body, text_body = render_reminder_email(
                base,
                display_name=_decrypt_simple(user.get('encrypted_display_name') or ''),
                local_date=local_date,
                notification_time=user.get('notification_time') or '09:00',
                days=user.get('notification_days'),
                tz_name=user.get('timezone') or 'UTC',
            )
            if test:
                subject = "Test: " + subject
            results['email'] = await service.send_email(
                address, subject, html_body, text_content=text_body,
                custom_args={"purpose": "test_reminder" if test else "daily_reminder", "app": "sizzle"},
            )
            if not results['email'].get('success'):
                logger.error(
                    "Reminder email failed: user=%s provider=%s status=%s attempts=%s error=%s detail=%s",
                    user.get('user_id'), results['email'].get('provider'), results['email'].get('status'),
                    results['email'].get('attempts'), results['email'].get('error'),
                    mask_emails(results['email'].get('detail')),
                )
        else:
            results['email'] = {"success": False, "status": 0, "attempts": 0,
                                "error": "No email address on file."}
            logger.warning("Reminder email skipped: user=%s has no email address on file", user.get('user_id'))
    slack_url = _decrypt_simple(user.get('encrypted_slack_webhook_url') or '').strip()
    if slack_url:
        message = slack_reminder_message(base + "/app", base + "/settings", test=test)
        results['slack'] = await send_slack(slack_url, message, post=slack_post)
        if not results['slack'].get('success'):
            logger.error("Reminder Slack post failed: user=%s status=%s attempts=%s",
                         user.get('user_id'), results['slack'].get('status'), results['slack'].get('attempts'))
    return results


def has_channel(user):
    if int(user.get('email_notifications') or 0) == 1:
        return True
    return bool(_decrypt_simple(user.get('encrypted_slack_webhook_url') or '').strip())


USERS_SQL = """
    SELECT user_id, email, email_verified, encrypted_email, encrypted_display_name,
           encrypted_slack_webhook_url, notification_time, notification_days, timezone,
           email_notifications, last_reminder_date
    FROM users
    WHERE notification_enabled = 1
      AND COALESCE(status, 'active') = 'active'
      AND (email_notifications = 1
           OR (encrypted_slack_webhook_url IS NOT NULL AND encrypted_slack_webhook_url != ''))
"""

CLAIM_SQL = """
    UPDATE users
    SET last_reminder_date = ?, last_reminder_status = 'sending', last_reminder_at = CURRENT_TIMESTAMP
    WHERE user_id = ? AND (last_reminder_date IS NULL OR last_reminder_date != ?)
"""


async def run_user_reminders(env, now_utc, email_service=None, slack_post=None):
    """Send every reminder due at now_utc. Returns a summary dict (for logs and tests)."""
    db = env.sizzle_db
    users = _rows(await db.prepare(USERS_SQL).all())
    summary = {"checked": len(users), "due": 0, "sent": 0, "failed": 0, "skipped_checked_in": 0}
    for user in users:
        user_id = user.get('user_id')
        try:
            due, local_date, _reason = reminder_due(
                now_utc, user.get('timezone') or 'UTC', user.get('notification_time') or '09:00',
                user.get('notification_days'), user.get('last_reminder_date'),
            )
            if not due or not has_channel(user):
                continue
            summary["due"] += 1
            checked_in = await db.prepare(
                "SELECT 1 AS found FROM checkins WHERE user_id = ? AND checkin_date = ? LIMIT 1"
            ).bind(user_id, local_date).first()
            if checked_in:
                summary["skipped_checked_in"] += 1
                continue
            claim = await db.prepare(CLAIM_SQL).bind(local_date, user_id, local_date).run()
            if _changes(claim) != 1:
                continue  # another run claimed today's reminder
            results = await send_reminder(env, user, local_date, email_service=email_service, slack_post=slack_post)
            ok = [r.get('success') for r in results.values()]
            status = 'sent' if ok and all(ok) else ('partial' if any(ok) else 'failed')
            summary["sent" if status != 'failed' else "failed"] += 1
            await db.prepare(
                "UPDATE users SET last_reminder_status = ? WHERE user_id = ?"
            ).bind(status, user_id).run()
            logger.info("Reminder %s: user=%s local_date=%s channels=%s", status, user_id, local_date,
                        ",".join(f"{k}:{'ok' if v.get('success') else v.get('status')}" for k, v in results.items()))
        except Exception as e:
            summary["failed"] += 1
            logger.error("Error processing reminder for %s: %s", user_id, mask_emails(e))
    return summary


async def handle_scheduled(event, env):
    """Run one scheduler tick (called through POST /__scheduled by blt-cron)."""
    now_utc = _event_time(event)
    logger.info("Running scheduled task at %s UTC", now_utc.strftime("%H:%M"))
    try:
        summary = await run_user_reminders(env, now_utc)
        logger.info("Reminders: %s", summary)
    except Exception as e:
        logger.error("Error in reminder run: %s", mask_emails(e), exc_info=True)
    await handle_org_notifications(env, now_utc)
    logger.info("Scheduled task complete")


async def handle_org_notifications(env, now_utc, post=None):
    """One consolidated Slack reminder per org for members who haven't checked in today.

    Runs only in the first 15-minute slot of ORG_NOTIFICATION_HOUR (UTC), which the
    15-minute cron hits exactly once a day.
    """
    try:
        try:
            org_hour = int(getattr(env, 'ORG_NOTIFICATION_HOUR', '') or DEFAULT_ORG_HOUR)
        except ValueError:
            org_hour = DEFAULT_ORG_HOUR
        if not (now_utc.hour == org_hour and now_utc.minute < 15):
            return

        today = now_utc.date().isoformat()
        base = app_url(env)
        orgs = _rows(await env.sizzle_db.prepare("""
            SELECT id, COALESCE(name, github_org_name) AS org_name, encrypted_slack_webhook_url
            FROM organizations
            WHERE encrypted_slack_webhook_url IS NOT NULL
              AND encrypted_slack_webhook_url != ''
        """).all())

        for org in orgs:
            try:
                slack_url = _decrypt_simple(org.get('encrypted_slack_webhook_url', '')).strip()
                if not is_slack_webhook_url(slack_url):
                    continue

                pending = _rows(await env.sizzle_db.prepare("""
                    SELECT uo.user_id
                    FROM user_organizations uo
                    WHERE uo.org_id = ?
                      AND COALESCE(uo.status, 'approved') = 'approved'
                      AND uo.user_id NOT IN (
                          SELECT user_id FROM checkins
                          WHERE org_id = ? AND checkin_date = ?
                      )
                    ORDER BY uo.user_id
                """).bind(org['id'], org['id'], today).all())

                if not pending:
                    continue

                member_list = '\n'.join(f'• @{m["user_id"]}' for m in pending)
                message = {
                    "text": f"Daily check-in reminder for {org['org_name']}",
                    "blocks": [
                        {"type": "section", "text": {"type": "mrkdwn", "text": (
                            f"*Daily check-in reminder: {org['org_name']}*\n\n"
                            f"These members haven't checked in for this org today:\n{member_list}"
                        )}},
                        {"type": "actions", "elements": [{
                            "type": "button",
                            "text": {"type": "plain_text", "text": "Submit check-in"},
                            "style": "primary",
                            "url": base + "/app",
                            "action_id": "checkin_button",
                        }]},
                    ],
                }
                result = await send_slack(slack_url, message, post=post)
                if not result.get('success'):
                    logger.error("Org Slack reminder failed: org=%s status=%s", org.get('org_name'), result.get('status'))
            except Exception as e:
                logger.error("Error sending org notification for %s: %s", org.get('org_name'), e)

    except Exception as e:
        logger.error("Error in org notifications: %s", e, exc_info=True)


async def on_scheduled(event, env):
    """Entry point for scheduled events"""
    return await handle_scheduled(event, env)
