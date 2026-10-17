"""
Scheduled notification handler for daily check-in reminders.
This script is triggered by Cloudflare Workers cron triggers.
"""

from js import fetch, Date
import json
import base64
import logging
import sys

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


def _decrypt_simple(encrypted_data):
    """Simple base64 decryption matching the placeholder in main.py"""
    if not encrypted_data:
        return ''
    try:
        parts = encrypted_data.split(':')
        if len(parts) != 2:
            return encrypted_data
        return base64.b64decode(parts[1]).decode('utf-8')
    except Exception:
        return encrypted_data


async def send_slack_notification(webhook_url, user_email, checkin_url):
    """Send Slack notification to user"""
    message = {
        "text": "🔔 Daily Check-in Reminder",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Good morning! Time for your daily check-in* ✨\n\nTake a moment to reflect on your progress and plan your day."
                }
            },
            {
                "type": "divider"
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*What to include:*\n• What you accomplished previously\n• Your plans for today\n• Any blockers or challenges\n• How you're feeling"
                }
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "📝 Fill Check-in Form",
                            "emoji": True
                        },
                        "style": "primary",
                        "url": checkin_url,
                        "action_id": "checkin_button"
                    }
                ]
            }
        ]
    }
    
    try:
        response = await fetch(webhook_url, {
            "method": "POST",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(message)
        })
        return response.ok
    except Exception as e:
        logger.error("Error sending Slack notification: %s", e)
        return False


async def send_email_notification(email, user_name, checkin_url, env):
    """Send email notification to user"""
    
    # Check if email provider is configured
    if not hasattr(env, 'EMAIL_API_KEY') or not env.EMAIL_API_KEY:
        logger.warning("Email notifications not configured: EMAIL_API_KEY missing")
        return False
    
    email_provider = getattr(env, 'EMAIL_PROVIDER', 'sendgrid')
    
    # Email HTML template
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 30px;
                border-radius: 10px 10px 0 0;
                text-align: center;
            }}
            .content {{
                background: #f9fafb;
                padding: 30px;
                border-radius: 0 0 10px 10px;
            }}
            .button {{
                display: inline-block;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 14px 30px;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 600;
                margin: 20px 0;
            }}
            .checklist {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .checklist-item {{
                padding: 8px 0;
            }}
            .footer {{
                text-align: center;
                color: #666;
                font-size: 12px;
                margin-top: 30px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>📝 Daily Check-in Reminder</h1>
            <p>Time to reflect and plan your day</p>
        </div>
        <div class="content">
            <p>Good morning!</p>
            <p>It's time for your daily check-in. Take a few minutes to document your progress and set your intentions for today.</p>
            
            <div class="checklist">
                <h3>What to include:</h3>
                <div class="checklist-item">✓ What you accomplished previously</div>
                <div class="checklist-item">✓ Your plans for today</div>
                <div class="checklist-item">✓ Any blockers or challenges</div>
                <div class="checklist-item">✓ How you're feeling</div>
            </div>
            
            <center>
                <a href="{checkin_url}" class="button">Fill Check-in Form</a>
            </center>
            
            <p style="margin-top: 30px; font-size: 14px; color: #666;">
                This reminder was sent to you based on your notification preferences. 
                You can update your settings anytime in the app.
            </p>
        </div>
        <div class="footer">
            <p>BLT Sizzle Check-in App</p>
            <p>You're receiving this because you enabled email notifications</p>
        </div>
    </body>
    </html>
    """
    
    text_content = f"""
    Daily Check-in Reminder
    
    Good morning!
    
    It's time for your daily check-in. Take a few minutes to document your progress and set your intentions for today.
    
    What to include:
    - What you accomplished previously
    - Your plans for today
    - Any blockers or challenges
    - How you're feeling
    
    Click here to fill out your check-in: {checkin_url}
    
    ---
    BLT Sizzle Check-in App
    """
    
    # Send via configured provider
    if email_provider == 'sendgrid':
        return await send_via_sendgrid(email, html_content, text_content, env)
    elif email_provider == 'mailgun':
        return await send_via_mailgun(email, html_content, text_content, env)
    else:
        logger.warning("Unsupported email provider: %s", email_provider)
        return False


async def send_via_sendgrid(to_email, html_content, text_content, env):
    """Send email via SendGrid API"""
    url = "https://api.sendgrid.com/v3/mail/send"
    
    data = {
        "personalizations": [
            {
                "to": [{"email": to_email}]
            }
        ],
        "from": {
            "email": env.EMAIL_FROM if hasattr(env, 'EMAIL_FROM') else "noreply@example.com",
            "name": "BLT Sizzle Check-in"
        },
        "subject": "📝 Daily Check-in Reminder",
        "content": [
            {
                "type": "text/plain",
                "value": text_content
            },
            {
                "type": "text/html",
                "value": html_content
            }
        ]
    }
    
    try:
        response = await fetch(url, {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {env.EMAIL_API_KEY}",
                "Content-Type": "application/json"
            },
            "body": json.dumps(data)
        })
        return response.ok
    except Exception as e:
        logger.error("Error sending via SendGrid: %s", e)
        return False


async def send_via_mailgun(to_email, html_content, text_content, env):
    """Send email via Mailgun API"""
    domain = env.EMAIL_DOMAIN if hasattr(env, 'EMAIL_DOMAIN') else "mg.example.com"
    url = f"https://api.mailgun.net/v3/{domain}/messages"
    
    form_data = {
        "from": f"BLT Sizzle Check-in <{env.EMAIL_FROM if hasattr(env, 'EMAIL_FROM') else 'noreply@example.com'}>",
        "to": to_email,
        "subject": "📝 Daily Check-in Reminder",
        "text": text_content,
        "html": html_content
    }
    
    try:
        # Mailgun uses basic auth
        import base64
        from urllib.parse import urlencode
        auth = base64.b64encode(f"api:{env.EMAIL_API_KEY}".encode()).decode()
        
        # Properly URL-encode form data
        encoded_body = urlencode(form_data)
        
        response = await fetch(url, {
            "method": "POST",
            "headers": {
                "Authorization": f"Basic {auth}",
                "Content-Type": "application/x-www-form-urlencoded"
            },
            "body": encoded_body
        })
        return response.ok
    except Exception as e:
        logger.error("Error sending via Mailgun: %s", e)
        return False


async def handle_scheduled(event, env):
    """
    Handle scheduled cron trigger.
    This function is called by Cloudflare Workers cron.
    """
    try:
        # Get current time in UTC
        iso_str = Date.new().toISOString()
        current_hour = int(iso_str.split('T')[1].split(':')[0])
        current_minute = int(iso_str.split(':')[1])
        logger.info("Running scheduled task at %02d:%02d UTC", current_hour, current_minute)
        

        
        # Query users - use encrypted column names
        result_proxy = await env.sizzle_db.prepare("""
            SELECT user_id, encrypted_email, encrypted_slack_webhook_url,
                   notification_time, timezone, email_notifications, notification_enabled
            FROM users
            WHERE notification_enabled = 1
        """).all()
        
        result = result_proxy.to_py() if hasattr(result_proxy, 'to_py') else result_proxy
        users = result.get('results', []) if isinstance(result, dict) else []
        
        if not users:
            logger.info("No users with notifications enabled")
            return
        
        checkin_url = f"https://{env.WORKER_HOST}" if hasattr(env, 'WORKER_HOST') else "https://your-worker.workers.dev"
        
        for user in users:
            try:
                # Decrypt PII
                slack_url = _decrypt_simple(user.get('encrypted_slack_webhook_url', ''))
                email = _decrypt_simple(user.get('encrypted_email', ''))

                notif_hour, notif_minute = map(int, user['notification_time'].split(':'))
                
                # Check if we are within the notification window
                if current_hour == notif_hour and abs(current_minute - notif_minute) < 30:
                    # 1. Send Check-in Reminder
                    if slack_url:
                        await send_slack_notification(slack_url, user['user_id'], checkin_url)
                    
                    if email and user['email_notifications'] == 1:
                        await send_email_notification(email, user['user_id'], checkin_url, env)
                            
            except Exception as e:
                logger.error("Error processing user %s: %s", user['user_id'], e)
                continue

        # Org-level notifications
        await handle_org_notifications(env, current_hour, current_minute, checkin_url)
        
        logger.info("Scheduled task complete")
    except Exception as e:
        logger.error("Error in scheduled handler: %s", e, exc_info=True)


async def handle_org_notifications(env, current_hour, current_minute, checkin_url):
    """Send one consolidated Slack reminder per org for members who haven't checked in today"""
    try:
        # Default org notification hour is 9am UTC; override with ORG_NOTIFICATION_HOUR env var
        org_hour = int(getattr(env, 'ORG_NOTIFICATION_HOUR', '9'))
        if not (current_hour == org_hour and current_minute < 30):
            return

        today = Date.new().toISOString().split('T')[0]

        orgs_proxy = await env.sizzle_db.prepare("""
            SELECT id, github_org_name, encrypted_slack_webhook_url
            FROM organizations
            WHERE encrypted_slack_webhook_url IS NOT NULL
              AND encrypted_slack_webhook_url != ''
        """).all()

        orgs_result = orgs_proxy.to_py() if hasattr(orgs_proxy, 'to_py') else orgs_proxy
        orgs = orgs_result.get('results', []) if isinstance(orgs_result, dict) else []

        for org in orgs:
            try:
                slack_url = _decrypt_simple(org.get('encrypted_slack_webhook_url', ''))
                if not slack_url:
                    continue

                # Members who haven't submitted an org-tagged check-in today
                pending_proxy = await env.sizzle_db.prepare("""
                    SELECT uo.user_id
                    FROM user_organizations uo
                    WHERE uo.org_id = ?
                      AND uo.user_id NOT IN (
                          SELECT user_id FROM checkins
                          WHERE org_id = ? AND checkin_date = ?
                      )
                    ORDER BY uo.user_id
                """).bind(org['id'], org['id'], today).all()

                pending_result = pending_proxy.to_py() if hasattr(pending_proxy, 'to_py') else pending_proxy
                pending = pending_result.get('results', []) if isinstance(pending_result, dict) else []

                if not pending:
                    continue

                member_list = '\n'.join(f'\u2022 @{m["user_id"]}' for m in pending)

                message = {
                    "text": f"\U0001f4cb Daily check-in reminder for {org['github_org_name']}",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    f"*Daily Check-in Reminder \u2014 {org['github_org_name']}* \U0001f4cb\n\n"
                                    f"The following members haven't checked in for this org today:\n"
                                    f"{member_list}"
                                )
                            }
                        },
                        {
                            "type": "actions",
                            "elements": [
                                {
                                    "type": "button",
                                    "text": {"type": "plain_text", "text": "\U0001f4dd Submit Check-in"},
                                    "style": "primary",
                                    "url": checkin_url,
                                    "action_id": "checkin_button"
                                }
                            ]
                        }
                    ]
                }

                await fetch(slack_url, {
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps(message)
                })

            except Exception as e:
                logger.error("Error sending org notification for %s: %s", org.get('github_org_name'), e)

    except Exception as e:
        logger.error("Error in org notifications: %s", e, exc_info=True)


async def on_scheduled(event, env):
    """Entry point for scheduled events"""
    return await handle_scheduled(event, env)