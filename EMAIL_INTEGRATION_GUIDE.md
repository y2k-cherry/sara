# 📧 Sara Email Integration Guide

## Overview
Sara can now compose and send emails on your behalf! Simply mention Sara in Slack with the email purpose and recipient, and she'll craft a professional email for your review before sending.

## 🚀 How It Works

### 1. Request an Email
Mention Sara in Slack with:
- **Purpose**: What the email is about
- **Recipient**: Who to send it to

**Examples:**
```
@Sara send an email to john@company.com about the meeting tomorrow
@Sara email sarah@vendor.com regarding the invoice delay
@Sara draft an email to client@business.com about our project update
```

### 2. Review the Email
Sara will compose a professional email and show you a preview:

```
📧 Email Preview

To: john@company.com
CC: partnerships@cherryapp.in
Subject: Meeting Tomorrow to Discuss Quarterly Results

Body:
Dear John,

I hope this email finds you well. I would like to schedule a meeting 
tomorrow to discuss our recent quarterly results. Your insights and 
feedback would be greatly appreciated.

Best Regards,
Yash Kewalramani

From: Yash Kewalramani <partnerships@cherryapp.in>

---
Reply with "✅ send" to send this email, or "❌ cancel" to cancel.
```

### 3. Confirm or Cancel
- Reply with **"✅ send"** to send the email
- Reply with **"❌ cancel"** to cancel

## 🔧 Setup Instructions

### Step 1: Configure Email Password
1. Add your email app password to the `.env` file:
   ```
   EMAIL_PASSWORD=your_app_password_here
   ```

### Step 2: Generate Gmail App Password (if using Gmail)
1. Go to [Google Account Settings](https://myaccount.google.com/apppasswords)
2. Generate a new App Password for "Mail"
3. Use this password (not your regular Gmail password)

### Step 3: Test the Integration
Run the test script to verify everything works:
```bash
python3 test_email_service.py
```

## 📋 Features

### ✅ What Sara Can Do
- **Extract email details** from natural language requests
- **Compose professional emails** with appropriate subjects and content
- **Show email previews** for your review before sending
- **Send emails** with you automatically CC'd
- **Handle confirmations** (send/cancel) in thread replies
- **Support various email formats** (Gmail SMTP by default)

### 🎯 Smart Email Composition
Sara uses AI to:
- Generate appropriate subject lines
- Write professional, concise email bodies
- Maintain consistent tone and formatting
- Include proper greetings and signatures

### 🔒 Security Features
- **Always CC's you** on sent emails
- **Requires confirmation** before sending
- **Uses app passwords** (not your main password)
- **Preview before send** - no surprises

## 📝 Usage Examples

### Meeting Requests
```
@Sara send an email to team@company.com about the quarterly review meeting next week
```

### Follow-ups
```
@Sara email client@business.com following up on our proposal from last week
```

### Vendor Communications
```
@Sara draft an email to vendor@supplier.com regarding the delayed shipment
```

### Project Updates
```
@Sara send an email to stakeholders@project.com with an update on the development progress
```

## 🛠️ Technical Details

### Email Service Architecture
- **EmailService class**: Handles composition, extraction, and sending
- **Intent classification**: Recognizes email requests automatically
- **OpenAI integration**: Generates professional email content
- **SMTP support**: Gmail by default, configurable for other providers
- **Thread-based confirmations**: Maintains context in Slack threads

### Configuration Options
```env
# Email Settings
SMTP_SERVER=smtp.gmail.com    # Email server
SMTP_PORT=587                 # SMTP port
EMAIL_PASSWORD=               # Your app password
```

### Supported Email Providers
- **Gmail** (default configuration)
- **Outlook** (change SMTP_SERVER to smtp-mail.outlook.com)
- **Custom SMTP** (configure server and port as needed)

## 🔍 Troubleshooting

### Email Not Sending?
1. **Check password**: Ensure EMAIL_PASSWORD is set in .env
2. **Use app password**: Don't use your regular email password
3. **Check SMTP settings**: Verify server and port are correct
4. **Test connection**: Run the test script to diagnose issues

### Email Not Being Recognized?
1. **Check intent**: Make sure your message clearly indicates email sending
2. **Include recipient**: Always specify the recipient email address
3. **Be specific**: Mention the purpose of the email clearly

### Preview Not Showing?
1. **Check thread**: Confirmations work in thread replies
2. **Wait for processing**: Give Sara a moment to compose the email
3. **Check logs**: Look for error messages in the console

## 🎉 Success Indicators

When everything is working correctly, you'll see:
- ✅ Email extraction working (recipient and purpose identified)
- ✅ Professional email composition
- ✅ Proper preview formatting
- ✅ Successful sending with confirmation
- ✅ You receive a copy via CC

## 📞 Support

If you encounter issues:
1. Run `python3 test_email_service.py` to diagnose
2. Check the `.env` file configuration
3. Verify your app password is correct
4. Ensure Sara has the necessary permissions

---

**🎊 Sara Email Integration is Ready!**
You can now send professional emails through Slack with Sara's help!
