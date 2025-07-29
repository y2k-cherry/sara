# 🚀 Deploy Sara to Render (100% Free)

**Render is the best free alternative to Railway** - no credit card required, 750 hours/month free tier (enough for 24/7 uptime).

## 🎯 **Why Render?**

- ✅ **Completely free** - No credit card required
- ✅ **750 hours/month** = 31+ days of continuous uptime
- ✅ **Auto-deploy from GitHub** - Push code = automatic updates
- ✅ **Built-in HTTPS** - Secure by default
- ✅ **Environment variables** - Secure secret management
- ✅ **Reliable infrastructure** - Better uptime than Heroku free tier

---

## 📋 **Prerequisites**

- ✅ Sara code is on GitHub: `y2k-cherry/sara`
- ✅ You have your API keys ready
- ✅ Slack app is configured

---

## 🚀 **Step-by-Step Deployment**

### **Step 1: Create Render Account**

1. Go to **https://render.com**
2. Click **"Get Started for Free"**
3. Sign up with your **GitHub account**
4. Authorize Render to access your repositories

### **Step 2: Create Web Service**

1. In Render dashboard, click **"New +"**
2. Select **"Web Service"**
3. Choose **"Build and deploy from a Git repository"**
4. Click **"Connect"** next to your GitHub account
5. Find and select **`y2k-cherry/sara`** repository
6. Click **"Connect"**

### **Step 3: Configure Service**

**Basic Settings:**
- **Name**: `sara-bot` (or any unique name)
- **Environment**: `Python 3`
- **Region**: Choose closest to you
- **Branch**: `main`

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`

### **Step 4: Add Environment Variables**

In the **Environment Variables** section, add:

```
OPENAI_API_KEY=sk-proj-your-openai-key-here
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_SIGNING_SECRET=your-slack-signing-secret-here
GOOGLE_CLIENT_ID=your-google-client-id-here
GOOGLE_CLIENT_SECRET=your-google-client-secret-here
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-email-app-password
```

**⚠️ Important**: Replace all `your-*-here` values with your actual credentials.

### **Step 5: Deploy**

1. Click **"Create Web Service"**
2. Render will start building and deploying
3. Wait for deployment to complete (usually 2-5 minutes)
4. You'll get a URL like: `https://sara-bot.onrender.com`

---

## 🔧 **Configure Slack for HTTP Mode**

### **Step 1: Update Slack App Settings**

1. Go to **https://api.slack.com/apps**
2. Select your Sara app
3. Go to **"Socket Mode"** → Turn it **OFF**
4. Go to **"Event Subscriptions"**:
   - Enable Events: **ON**
   - Request URL: `https://your-app-name.onrender.com/slack/events`
   - Subscribe to bot events: `message.channels`, `app_mention`
5. Go to **"Slash Commands"**:
   - Update each command's Request URL to: `https://your-app-name.onrender.com/slack/events`
6. **Save Changes**

### **Step 2: Get Slack Signing Secret**

1. In your Slack app settings
2. Go to **"Basic Information"**
3. Find **"Signing Secret"**
4. Copy it and add to Render environment variables as `SLACK_SIGNING_SECRET`

---

## ✅ **Verify Deployment**

### **Test Health Check**
Visit: `https://your-app-name.onrender.com/health`

Should return:
```json
{
  "status": "healthy",
  "timestamp": "2025-07-29T07:49:03.123456",
  "version": "1.0.0"
}
```

### **Test Slack Integration**
1. Go to your Slack workspace
2. Try: `@Sara help`
3. Try: `/sara_help`
4. Try: `/sara_status`

---

## 🔄 **Auto-Deployment Setup**

**Good news**: Auto-deployment is enabled by default!

- ✅ Push to GitHub → Automatic deployment
- ✅ View logs in Render dashboard
- ✅ Rollback to previous versions if needed

---

## 📊 **Monitor Your Deployment**

### **Render Dashboard Features:**
- ✅ **Logs** - Real-time application logs
- ✅ **Metrics** - CPU, memory, response times
- ✅ **Events** - Deployment history
- ✅ **Settings** - Update environment variables

### **Check Logs:**
1. Go to Render dashboard
2. Click on your service
3. Click **"Logs"** tab
4. Monitor for any errors

---

## 🆘 **Troubleshooting**

### **Common Issues:**

**1. Build Failed**
- Check `requirements.txt` is present
- Verify Python version compatibility

**2. App Won't Start**
- Check start command: `gunicorn wsgi:app --bind 0.0.0.0:$PORT`
- Verify `wsgi.py` and `orchestrator_http.py` exist

**3. Slack Events Not Working**
- Verify Request URL in Slack app settings
- Check `SLACK_SIGNING_SECRET` environment variable
- Ensure Socket Mode is OFF

**4. Environment Variables**
- Double-check all variables are set correctly
- No spaces around `=` in variable values
- Restart service after adding variables

### **Debug Steps:**
1. Check **Logs** in Render dashboard
2. Test **Health endpoint**: `/health`
3. Verify **Environment variables** are set
4. Test **locally first**: `python orchestrator_http.py`

---

## 💰 **Free Tier Limits**

**Render Free Tier:**
- ✅ **750 hours/month** (31+ days of 24/7 uptime)
- ✅ **512 MB RAM**
- ✅ **0.1 CPU**
- ✅ **Unlimited bandwidth**
- ✅ **Custom domains** (with upgrade)

**Perfect for Sara bot usage!**

---

## 🎉 **Success!**

Once deployed, your Sara bot will be:

- ✅ **Available 24/7** - No local terminal needed
- ✅ **Auto-updating** - Push to GitHub = automatic deployment
- ✅ **Secure** - HTTPS and environment variables
- ✅ **Monitored** - Logs and metrics in dashboard
- ✅ **Free** - No cost for standard usage

**Your Sara bot is now professionally hosted! 🚀**

---

## 📞 **Support**

- **Render Docs**: https://render.com/docs
- **Render Community**: https://community.render.com
- **Sara Issues**: Check the logs in Render dashboard

**Enjoy your 24/7 Sara bot on Render! 🎊**
