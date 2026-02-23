#!/usr/bin/env python3
"""
BLT Newsletter Sender
Sends newsletters to subscribers via SendGrid
"""

import os
import sys
import json
import logging
import markdown2
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Configuration
API_KEY = os.environ.get('SENDGRID_API_KEY')
FROM_EMAIL = os.environ.get('SENDGRID_FROM_EMAIL', 'newsletter@blt.owasp.org')
if not os.environ.get('SENDGRID_FROM_EMAIL'):
    logger.warning(
        "SENDGRID_FROM_EMAIL is not set. Using default "
        "'{FROM_EMAIL}'. Make sure this address is verified in SendGrid "
        "or emails will be rejected."
    )
SUBJECT = os.environ.get('NEWSLETTER_SUBJECT', 'BLT Newsletter')
CONTENT_FILE = os.environ.get('NEWSLETTER_CONTENT_FILE', 'newsletters/latest.md')

def convert_markdown_to_html(markdown_text):
    """
    Convert markdown to HTML using the markdown2 library.
    Handles headings, bold, italic, bullet lists, ordered lists, links,
    and paragraphs correctly — without producing invalid nested block elements.
    """
    return markdown2.markdown(
        markdown_text,
        extras=["fenced-code-blocks", "tables", "strike", "task_list"]
    )

def create_email_template(content_html):
    """
    Wrap content in BLT-branded email template
    """
    template = f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      font-family: Inter, system-ui, -apple-system, sans-serif;
      line-height: 1.6;
      color: #334155;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background: #f8fafc;
    }}
    .header {{
      background: linear-gradient(135deg, #feeae9 0%, #fff 100%);
      padding: 30px;
      border-radius: 12px;
      margin-bottom: 30px;
      text-align: center;
    }}
    .header h1 {{
      margin: 0;
      color: #dc2626;
      font-size: 28px;
      font-weight: 700;
    }}
    .content {{
      background: white;
      padding: 30px;
      border-radius: 12px;
      border: 1px solid #e2e8f0;
      margin-bottom: 20px;
    }}
    .footer {{
      text-align: center;
      margin-top: 30px;
      color: #64748b;
      font-size: 14px;
    }}
    a {{
      color: #dc2626;
      text-decoration: none;
    }}
    a:hover {{
      text-decoration: underline;
    }}
  </style>
</head>
<body>
  <div class="header">
    <h1>🐛 BLT Newsletter</h1>
  </div>
  <div class="content">
    {content_html}
  </div>
  <div class="footer">
    <p>You're receiving this because you subscribed to the BLT Newsletter.</p>
    <p>
      <a href="https://owasp-blt.github.io/BLT-Newsletter/">Visit our website</a> | 
      <a href="https://github.com/OWASP-BLT">GitHub</a>
    </p>
    <p style="margin-top: 20px; font-size: 12px;">
      To unsubscribe, please <a href="https://github.com/OWASP-BLT/BLT-Newsletter/issues?q=is%3Aissue+is%3Aopen+label%3Anewsletter-subscription">close your subscription issue</a> 
      on GitHub or reply to this email with "Unsubscribe".
    </p>
  </div>
</body>
</html>
    """
    return template.strip()

def send_newsletter():
    """
    Main function to send newsletter to all subscribers
    """
    # Validate API key
    if not API_KEY:
        logger.error('SENDGRID_API_KEY is not set')
        sys.exit(1)
    
    # Initialize SendGrid client
    sg = SendGridAPIClient(API_KEY)
    
    # Read subscribers
    subscribers = []
    single_recipient = os.environ.get('SINGLE_RECIPIENT')
    single_name = os.environ.get('SINGLE_NAME', 'Subscriber')

    if single_recipient:
        subscribers = [{'email': single_recipient, 'name': single_name}]
        logger.info(f'Sending single email to {single_recipient}...')
    else:
        try:
            with open('subscribers.json', 'r') as f:
                subscribers = json.load(f)
        except FileNotFoundError:
            logger.error('subscribers.json not found')
            sys.exit(1)
        
        if not subscribers:
            logger.info('No subscribers found')
            return
        
        logger.info(f'Sending newsletter to {len(subscribers)} subscribers...')
    
    # Read newsletter content
    text_content = ''
    html_content = ''
    
    if os.path.exists(CONTENT_FILE):
        with open(CONTENT_FILE, 'r') as f:
            markdown_content = f.read()
            text_content = markdown_content
            html_content = convert_markdown_to_html(markdown_content)
    else:
        text_content = 'Newsletter content not found'
        html_content = '<p>Newsletter content not found</p>'
    
    # Wrap in email template
    wrapped_html = create_email_template(html_content)
    
    # Send emails
    successful = 0
    failed = 0
    
    for subscriber in subscribers:
        email = subscriber.get('email')
        name = subscriber.get('name', 'Subscriber')
        
        if not email:
            continue
        
        try:
            message = Mail(
                from_email=FROM_EMAIL,
                to_emails=email,
                subject=SUBJECT,
                plain_text_content=text_content,
                html_content=wrapped_html
            )
            
            response = sg.send(message)
            
            if response.status_code in [200, 201, 202]:
                logger.info(f'Sent to {email}')
                successful += 1
            else:
                logger.error(f'Failed to send to {email}: Status {response.status_code}')
                failed += 1
                
        except Exception as e:
            logger.error(f'Failed to send to {email}: {str(e)}')
            failed += 1
    
    # Print summary
    logger.info(f'Newsletter sent successfully to {successful} subscribers')
    if failed > 0:
        logger.error(f'Failed to send to {failed} subscribers')
        sys.exit(1)

if __name__ == '__main__':
    send_newsletter()
