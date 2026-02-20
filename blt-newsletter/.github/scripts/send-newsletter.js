const sgMail = require('@sendgrid/mail');
const fs = require('fs');
const path = require('path');
const { marked } = require('marked');

// Configure SendGrid
const apiKey = process.env.SENDGRID_API_KEY;
const fromEmail = process.env.SENDGRID_FROM_EMAIL || 'newsletter@blt.owasp.org';
const subject = process.env.NEWSLETTER_SUBJECT || 'BLT Newsletter';
const contentFile = process.env.NEWSLETTER_CONTENT_FILE || 'newsletters/latest.md';

if (!apiKey) {
  console.error('SENDGRID_API_KEY is not set');
  process.exit(1);
}

sgMail.setApiKey(apiKey);

async function sendNewsletter() {
  try {
    // Read subscribers
    const subscribersData = fs.readFileSync('subscribers.json', 'utf8');
    const subscribers = JSON.parse(subscribersData);
    
    if (subscribers.length === 0) {
      console.log('No subscribers found');
      return;
    }
    
    console.log(`Sending newsletter to ${subscribers.length} subscribers...`);
    
    // Read newsletter content
    let htmlContent = '';
    let textContent = '';
    
    if (fs.existsSync(contentFile)) {
      const markdown = fs.readFileSync(contentFile, 'utf8');
      textContent = markdown;
      
      // Convert markdown to HTML if marked is available
      try {
        const marked = require('marked');
        htmlContent = marked.parse(markdown);
      } catch (e) {
        htmlContent = `<pre>${markdown}</pre>`;
      }
    } else {
      textContent = 'Newsletter content not found';
      htmlContent = '<p>Newsletter content not found</p>';
    }
    
    // Wrap in BLT email template
    const wrappedHtml = `
      <!DOCTYPE html>
      <html>
      <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
          body {
            font-family: Inter, system-ui, -apple-system, sans-serif;
            line-height: 1.6;
            color: #334155;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background: #f8fafc;
          }
          .header {
            background: linear-gradient(135deg, #feeae9 0%, #fff 100%);
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
            text-align: center;
          }
          .header h1 {
            margin: 0;
            color: #dc2626;
            font-size: 28px;
            font-weight: 700;
          }
          .content {
            background: white;
            padding: 30px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
            margin-bottom: 20px;
          }
          .footer {
            text-align: center;
            margin-top: 30px;
            color: #64748b;
            font-size: 14px;
          }
          a {
            color: #dc2626;
            text-decoration: none;
          }
          a:hover {
            text-decoration: underline;
          }
        </style>
      </head>
      <body>
        <div class="header">
          <h1>🐛 BLT Newsletter</h1>
        </div>
        <div class="content">
          ${htmlContent}
        </div>
        <div class="footer">
          <p>You're receiving this because you subscribed to the BLT Newsletter.</p>
          <p><a href="https://owasp-blt.github.io/BLT-Newsletter/">Visit our website</a> | <a href="https://github.com/OWASP-BLT">GitHub</a></p>
        </div>
      </body>
      </html>
    `;
    
    // Send emails
    const emailPromises = subscribers.map(async (subscriber) => {
      try {
        await sgMail.send({
          to: subscriber.email,
          from: fromEmail,
          subject: subject,
          text: textContent,
          html: wrappedHtml
        });
        console.log(`✓ Sent to ${subscriber.email}`);
        return { success: true, email: subscriber.email };
      } catch (error) {
        console.error(`✗ Failed to send to ${subscriber.email}:`, error.message);
        return { success: false, email: subscriber.email, error: error.message };
      }
    });
    
    const results = await Promise.all(emailPromises);
    const successful = results.filter(r => r.success).length;
    const failed = results.filter(r => !r.success).length;
    
    console.log(`\n✅ Newsletter sent successfully to ${successful} subscribers`);
    if (failed > 0) {
      console.log(`❌ Failed to send to ${failed} subscribers`);
    }
    
  } catch (error) {
    console.error('Error sending newsletter:', error);
    process.exit(1);
  }
}

sendNewsletter();
