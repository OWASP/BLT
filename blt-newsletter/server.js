const express = require('express');
const bodyParser = require('body-parser');
const sgMail = require('@sendgrid/mail');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 3000;

// Configure SendGrid
if (process.env.SENDGRID_API_KEY) {
  sgMail.setApiKey(process.env.SENDGRID_API_KEY);
}

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));
app.use(express.static('public'));

// Newsletter subscription endpoint
app.post('/api/subscribe', async (req, res) => {
  const { email, name } = req.body;

  // Validate input
  if (!email || !email.includes('@')) {
    return res.status(400).json({ 
      success: false, 
      message: 'Please provide a valid email address.' 
    });
  }

  // Check if SendGrid is configured
  if (!process.env.SENDGRID_API_KEY) {
    console.error('SendGrid API key not configured');
    return res.status(500).json({ 
      success: false, 
      message: 'Newsletter service is not configured. Please try again later.' 
    });
  }

  try {
    // Add contact to SendGrid mailing list
    const data = {
      contacts: [
        {
          email: email,
          first_name: name || ''
        }
      ]
    };

    // Use SendGrid Marketing Campaigns API to add contact to list
    const request = {
      method: 'PUT',
      url: '/v3/marketing/contacts',
      body: JSON.stringify(data)
    };

    await sgMail.client.request(request);

    // Send welcome email
    const welcomeMsg = {
      to: email,
      from: process.env.SENDGRID_FROM_EMAIL || 'newsletter@blt.owasp.org',
      subject: 'Welcome to BLT Newsletter!',
      text: `Hi ${name || 'there'},\n\nThank you for subscribing to the BLT Newsletter! You'll receive updates about:\n\n- Stats and insights from the BLT platform\n- New features and improvements we're working on\n- Security tips and vulnerability disclosure best practices\n- Community highlights and success stories\n\nStay tuned for our upcoming newsletters!\n\nBest regards,\nThe OWASP BLT Team`,
      html: `
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
            }
            .header {
              background: linear-gradient(135deg, #feeae9 0%, #fff 100%);
              padding: 30px;
              border-radius: 12px;
              margin-bottom: 30px;
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
            }
            .highlight {
              background: #fef2f2;
              border-left: 4px solid #dc2626;
              padding: 15px;
              margin: 20px 0;
              border-radius: 4px;
            }
            ul {
              padding-left: 20px;
            }
            li {
              margin: 8px 0;
            }
            .footer {
              text-align: center;
              margin-top: 30px;
              color: #64748b;
              font-size: 14px;
            }
          </style>
        </head>
        <body>
          <div class="header">
            <h1>🎉 Welcome to BLT Newsletter!</h1>
          </div>
          <div class="content">
            <p>Hi ${name || 'there'},</p>
            <p>Thank you for subscribing to the BLT Newsletter! We're excited to have you as part of our community.</p>
            <div class="highlight">
              <strong>What you'll receive:</strong>
              <ul>
                <li>📊 Stats and insights from the BLT platform</li>
                <li>🚀 New features and improvements we're working on</li>
                <li>🔒 Security tips and vulnerability disclosure best practices</li>
                <li>⭐ Community highlights and success stories</li>
              </ul>
            </div>
            <p>Stay tuned for our upcoming newsletters packed with valuable content!</p>
            <p>Best regards,<br><strong>The OWASP BLT Team</strong></p>
          </div>
          <div class="footer">
            <p>You're receiving this because you subscribed to the BLT Newsletter.</p>
          </div>
        </body>
        </html>
      `
    };

    await sgMail.send(welcomeMsg);

    res.json({ 
      success: true, 
      message: 'Successfully subscribed! Check your email for confirmation.' 
    });

  } catch (error) {
    console.error('SendGrid Error:', error.response ? error.response.body : error.message);
    res.status(500).json({ 
      success: false, 
      message: 'Failed to subscribe. Please try again later.' 
    });
  }
});

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    sendgridConfigured: !!process.env.SENDGRID_API_KEY 
  });
});

app.listen(PORT, () => {
  console.log(`Newsletter server running on http://localhost:${PORT}`);
  console.log(`SendGrid configured: ${!!process.env.SENDGRID_API_KEY}`);
});
