# 🚀 Sara Bot Railway Deployment Guide

This guide will help you deploy Sara to Railway's free tier for 24/7 hosting without needing to keep your terminal running.

## 📋 Prerequisites

1. **GitHub Account** - For code repository
2. **Railway Account** - Sign up at [railway.app](https://railway.app)
3. **Slack App Configuration** - You'll need to update your Slack app settings

## 🔧 Step 1: Prepare Your Code

### 1.1 Update Environment Variables
You need to add the `SLACK_SIGNING_SECRET` to your `.env` file:

1. Go to your Slack App settings at [api.slack.com/apps](https://api.slack.com/apps)
2. Select your Sara app
3. Go to **Basic Information** → **App Credentials**
4. Copy the **Signing Secret**
5. Add it to your `.env` file:

```env
SLACK_SIGNING_SECRET=your_signing_secret_here
```

### 1.2 Files Ready for Deployment
✅ `orchestrator_http.py` - HTTP version of Sara
✅ `requirements.txt` - Updated with Flask and Gunicorn
✅ `Procfile` - Railway startup command
✅ `railway.toml` - Railway configuration

## 🔄 Step 2: Switch Slack App from Socket Mode to HTTP Mode

### 2.1 Disable Socket Mode
1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Select your Sara app
3. Go to **Socket Mode**
4. Toggle **Enable Socket Mode** to **OFF**

### 2.2 Enable Event Subscriptions
1. Go to **Event Subscriptions**
2. Toggle **Enable Events** to **ON**
3. For **Request URL**, you'll add this AFTER deploying to Railway:
   ```
   https://your-app-name.up.railway.app/slack/events
   ```
   (Leave this blank for now, we'll come back to it)

### 2.3 Configure Event Subscriptions
Under **Subscribe to bot events**, add these events:
- `app_mention`
- `message.channels`
- `message.groups`
- `message.im`
- `message.mpim`

Click **Save Changes**

## 🚂 Step 3: Deploy to Railway

### 3.1 Create GitHub Repository
1. Create a new repository on GitHub (e.g., `sara-slack-bot`)
2. Push your Sara code to the repository:

```bash
git init
git add .
git commit -m "Initial Sara bot deployment"
git branch -M main
git remote add origin https://github.com/yourusername/sara-slack-bot.git
git push -u origin main
```

### 3.2 Deploy on Railway
1. Go to [railway.app](https://railway.app) and sign in
2. Click **New Project**
3. Select **Deploy from GitHub repo**
4. Choose your `sara-slack-bot` repository
5. Railway will automatically detect it's a Python app and start building

### 3.3 Configure Environment Variables
1. In your Railway project dashboard, go to **Variables**
2. Add all your environment variables from `.env`:

```
SLACK_BOT_TOKEN=xoxb-your-bot-token
SLACK_APP_TOKEN=xapp-your-app-token  
SLACK_SIGNING_SECRET=your-signing-secret
OPENAI_API_KEY=sk-proj-your-openai-key
CLIENT_ID=your-google-client-id
CLIENT_SECRET=your-google-client-secret
REDIRECT_URI=http://localhost:3001/oauth2callback
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_PASSWORD=your-app-password
```

**Important**: Don't include `GDRIVE_CREDS_DIR` as Railway will handle file paths differently.

### 3.4 Get Your Railway URL
1. After deployment, Railway will provide a URL like:
   ```
   https://sara-slack-bot-production.up.railway.app
   ```
2. Copy this URL - you'll need it for Slack configuration

## 🔗 Step 4: Complete Slack Configuration

### 4.1 Update Event Subscriptions URL
1. Go back to your Slack App settings
2. Go to **Event Subscriptions**
3. In **Request URL**, enter:
   ```
   https://your-railway-url.up.railway.app/slack/events
   ```
4. Slack will verify the URL (it should show a green checkmark)
5. Click **Save Changes**

### 4.2 Update OAuth Redirect URIs (if needed)
If you use Google OAuth features:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Navigate to your project → APIs & Services → Credentials
3. Edit your OAuth 2.0 Client ID
4. Add your Railway URL to authorized redirect URIs if needed

## ✅ Step 5: Test Your Deployment

### 5.1 Check Health Status
Visit your Railway URL in a browser:
```
https://your-railway-url.up.railway.app/health
```
You should see: `{"status": "healthy", "service": "Sara Bot"}`

### 5.2 Test Sara in Slack
1. Go to your Slack workspace
2. Mention Sara: `@Sara help`
3. Sara should respond with the help message

### 5.3 Test All Features
- **Help**: `@Sara what can you do`
- **Sheets**: `@Sara who hasn't paid`
- **Email**: `@Sara send email to test@example.com`
- **Agreements**: `@Sara generate agreement for Test Company`

## 🔍 Step 6: Monitor and Troubleshoot

### 6.1 View Logs
1. In Railway dashboard, go to **Deployments**
2. Click on your latest deployment
3. View logs to see Sara's activity and any errors

### 6.2 Common Issues

**Issue**: Slack events not reaching Sara
- **Solution**: Check that Event Subscriptions URL is correct and verified

**Issue**: Google Sheets not working
- **Solution**: Ensure all Google credentials are properly set in Railway environment variables

**Issue**: App sleeping/cold starts
- **Solution**: Railway free tier may have cold starts. Consider upgrading if needed.

## 🎉 Success!

Sara is now running 24/7 on Railway! Key benefits:

✅ **No terminal required** - Sara runs independently
✅ **Auto-deployment** - Push to GitHub = automatic updates
✅ **Free hosting** - Railway's generous free tier
✅ **Monitoring** - Built-in logs and health checks
✅ **Scalable** - Easy to upgrade if usage grows

## 📞 Support

If you encounter issues:
1. Check Railway logs for error messages
2. Verify all environment variables are set correctly
3. Ensure Slack Event Subscriptions URL is properly configured
4. Test the `/health` endpoint to confirm Sara is running

Your Sara bot is now professionally hosted and ready for production use! 🚀
