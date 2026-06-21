import html


def render_newsletter_issue_email(title, summary, markdown_body, archive_url, unsubscribe_url):
    safe_title = escape_text(title)
    safe_summary = escape_text(summary)
    body_html = render_markdown(markdown_body)
    safe_archive_url = escape_attr(archive_url)
    safe_unsubscribe_url = escape_attr(unsubscribe_url)

    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>{safe_title}</title>
  </head>
  <body style="margin:0;background:#f8fafc;color:#0f172a;font-family:Inter,Arial,sans-serif;">
    <div style="display:none;max-height:0;overflow:hidden;">{safe_summary}</div>
    <main style="max-width:680px;margin:0 auto;padding:32px 16px;">
      <div style="border:1px solid #e2e8f0;background:#ffffff;border-radius:8px;overflow:hidden;">
        <header style="padding:24px 28px;border-bottom:3px solid #dc2626;">
          <p style="margin:0 0 8px;color:#dc2626;font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;">OWASP BLT Newsletter</p>
          <h1 style="margin:0;color:#0f172a;font-size:28px;line-height:1.2;">{safe_title}</h1>
          <p style="margin:12px 0 0;color:#475569;font-size:15px;line-height:1.6;">{safe_summary}</p>
        </header>
        <section style="padding:28px;color:#0f172a;font-size:16px;line-height:1.65;">
          {body_html}
          <p style="margin:28px 0 0;">
            <a href="{safe_archive_url}" style="color:#dc2626;font-weight:600;">Read this issue in the archive</a>
          </p>
        </section>
        <footer style="padding:20px 28px;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;line-height:1.6;">
          You are receiving this because you subscribed to BLT Newsletter.
          <a href="{safe_unsubscribe_url}" style="color:#dc2626;">Unsubscribe</a>
        </footer>
      </div>
    </main>
  </body>
</html>"""


def render_markdown(markdown_body):
    lines = str(markdown_body or "").splitlines()
    blocks = []
    paragraph = []
    bullets = []

    def flush_paragraph():
        if paragraph:
            text = " ".join(item.strip() for item in paragraph if item.strip())
            if text:
                blocks.append(f"<p>{escape_text(text)}</p>")
            paragraph.clear()

    def flush_bullets():
        if bullets:
            items = "".join(f"<li>{escape_text(item)}</li>" for item in bullets)
            blocks.append(f"<ul>{items}</ul>")
            bullets.clear()

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            flush_paragraph()
            flush_bullets()
            continue

        if line.startswith("## "):
            flush_paragraph()
            flush_bullets()
            blocks.append(f"<h2>{escape_text(line[3:].strip())}</h2>")
            continue

        if line.startswith("# "):
            flush_paragraph()
            flush_bullets()
            blocks.append(f"<h1>{escape_text(line[2:].strip())}</h1>")
            continue

        if line.startswith("- ") or line.startswith("* "):
            flush_paragraph()
            bullets.append(line[2:].strip())
            continue

        flush_bullets()
        paragraph.append(line)

    flush_paragraph()
    flush_bullets()
    return "\n".join(blocks)


def escape_text(value):
    return html.escape(str(value or ""), quote=False)


def escape_attr(value):
    return html.escape(str(value or ""), quote=True)
