import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

from agreement_service import handle_agreement
from utils import clean_slack_text
from intent_classifier import get_intent_from_text
from status_service import read_google_doc_text
from sheets_service import sheets_service
from direct_sheets_service import DirectSheetsService
from email_service import handle_email_request, handle_email_confirmation

# Load environment variables
load_dotenv()

# Initialize Flask app first
flask_app = Flask(__name__)
app = flask_app  # Alias for Gunicorn compatibility

# Initialize Slack Bolt App (HTTP Mode) with error handling
try:
    slack_app = App(
        token=os.getenv("SLACK_BOT_TOKEN"),
        signing_secret=os.getenv("SLACK_SIGNING_SECRET")
    )
    handler = SlackRequestHandler(slack_app)
    
    # Get bot ID for thread detection
    bot_user_id = slack_app.client.auth_test()["user_id"]
    print("✅ Slack app initialized successfully")
except Exception as e:
    print(f"⚠️  Slack app initialization failed: {e}")
    slack_app = None
    handler = None
    bot_user_id = None

# Initialize Direct Sheets Service
try:
    direct_sheets = DirectSheetsService()
    print("✅ Direct Sheets Service initialized")
except Exception as e:
    print(f"⚠️  Direct Sheets Service failed to initialize: {e}")
    direct_sheets = None

# ─── Function: route_mention ─────────────────────────────────────────────
def route_mention(event, say):
    raw_text = event["text"]
    cleaned_text = clean_slack_text(raw_text).lower()

    intent = get_intent_from_text(cleaned_text)

    if intent == "generate_agreement":
        handle_agreement(event, say)
    elif intent == "get_status":
        status_text = read_google_doc_text()
        say(f"📄 Here's the status info from *Sara Test Doc*:\n\n{status_text}", thread_ts=event["ts"])
    elif intent == "lookup_sheets":
        say("🔍 Looking up data in Google Sheets...", thread_ts=event["ts"])
        try:
            if direct_sheets:
                # Check if there's a Google Sheets URL in the text
                if 'docs.google.com/spreadsheets' in raw_text:
                    # Extract the URL and use direct sheets service
                    import re
                    url_match = re.search(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)', raw_text)
                    if url_match:
                        sheet_url = url_match.group(0)
                        response = direct_sheets.process_sheets_query(sheet_url, cleaned_text)
                        say(f"📊 {response}", thread_ts=event["ts"])
                    else:
                        # Fallback to original service
                        response = sheets_service.lookup_data_in_sheets(cleaned_text)
                        say(f"📊 {response}", thread_ts=event["ts"])
                else:
                    # Use direct sheets service for all queries (including payment queries)
                    # This will automatically detect payment queries and route to Brand Balances sheet
                    response = direct_sheets.process_sheets_query("", cleaned_text)
                    say(f"📊 {response}", thread_ts=event["ts"])
            else:
                # Fallback to original MCP-based service if direct sheets not available
                response = sheets_service.lookup_data_in_sheets(cleaned_text)
                say(f"📊 {response}", thread_ts=event["ts"])
        except Exception as e:
            say(f"❌ Error looking up data: {str(e)}", thread_ts=event["ts"])
    elif intent == "send_email":
        say("📧 Composing email...", thread_ts=event["ts"])
        handle_email_request(event, say)
    elif intent == "help":
        help_message = """👋 **Hi! I'm Sara, your AI assistant. Here's what I can help you with:**

🤝 **Partnership Agreements**
• Generate custom partnership agreements
• *Example: "Generate an agreement for XYZ Company"*

📊 **Google Sheets & Data Analysis**
• Analyze spreadsheet data and answer questions
• Check payment status and brand balances
• Count brands, analyze metrics, and more
• *Examples: "Who hasn't paid?", "How many brands are listed?", "Analyze this sheet [URL]"*

📧 **Email Management**
• Send emails to individuals or groups
• Draft professional communications
• *Example: "Send an email to john@company.com about the meeting"*

📄 **Status Updates**
• Check current project status and information
• *Example: "What's the current status?"*

💡 **Tips:**
• You can share Google Sheets URLs for specific analysis
• I can access both public and private sheets (with proper permissions)
• Payment queries automatically check the Brand Balances sheet

Just mention me with `@Sara` and ask away! 🚀"""
        say(help_message, thread_ts=event["ts"])
    else:
        say("🤔 Sorry, I couldn't understand what you're asking. Can you rephrase?", thread_ts=event["ts"])


# ─── Function: handle_all_messages (thread replies) ──────────────────────
def handle_all_messages(body, say, client, logger):
    event = body.get("event", {})
    if event.get("bot_id"):
        return

    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    channel = event["channel"]
    user_text = event.get("text", "")

    try:
        resp = client.conversations_replies(channel=channel, ts=thread_ts, limit=1)
        parent_text = resp["messages"][0].get("text", "")
    except Exception as e:
        logger.error("Failed to fetch thread replies: %s", e)
        return

    if f"<@{bot_user_id}>" in parent_text:
        combined_text = parent_text + "\n" + user_text
        cleaned_text = clean_slack_text(combined_text).lower()
        intent = get_intent_from_text(cleaned_text)

        say("🔄 Got it, one sec...", thread_ts=thread_ts)

        # First check if this is an email confirmation
        if handle_email_confirmation(event, say):
            return  # Email confirmation handled, don't process further
        
        if intent == "generate_agreement":
            handle_agreement({**event, "text": combined_text}, say)
        elif intent == "get_status":
            say("📊 Status checks coming soon!", thread_ts=thread_ts)
        elif intent == "send_email":
            handle_email_request({**event, "text": combined_text}, say)
        elif intent == "lookup_sheets":
            try:
                if direct_sheets:
                    # Check if there's a Google Sheets URL in the combined text
                    if 'docs.google.com/spreadsheets' in combined_text:
                        # Extract the URL and use direct sheets service
                        import re
                        url_match = re.search(r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)', combined_text)
                        if url_match:
                            sheet_url = url_match.group(0)
                            response = direct_sheets.process_sheets_query(sheet_url, cleaned_text)
                            say(f"📊 {response}", thread_ts=thread_ts)
                        else:
                            # Fallback to original service
                            response = sheets_service.lookup_data_in_sheets(cleaned_text)
                            say(f"📊 {response}", thread_ts=thread_ts)
                    else:
                        # Use direct sheets service for all queries (including payment queries)
                        # This will automatically detect payment queries and route to Brand Balances sheet
                        response = direct_sheets.process_sheets_query("", cleaned_text)
                        say(f"📊 {response}", thread_ts=thread_ts)
                else:
                    # Fallback to original MCP-based service if direct sheets not available
                    response = sheets_service.lookup_data_in_sheets(cleaned_text)
                    say(f"📊 {response}", thread_ts=thread_ts)
            except Exception as e:
                say(f"❌ Error looking up data: {str(e)}", thread_ts=thread_ts)
        elif intent == "help":
            help_message = """👋 **Hi! I'm Sara, your AI assistant. Here's what I can help you with:**

🤝 **Partnership Agreements**
• Generate custom partnership agreements
• *Example: "Generate an agreement for XYZ Company"*

📊 **Google Sheets & Data Analysis**
• Analyze spreadsheet data and answer questions
• Check payment status and brand balances
• Count brands, analyze metrics, and more
• *Examples: "Who hasn't paid?", "How many brands are listed?", "Analyze this sheet [URL]"*

📧 **Email Management**
• Send emails to individuals or groups
• Draft professional communications
• *Example: "Send an email to john@company.com about the meeting"*

📄 **Status Updates**
• Check current project status and information
• *Example: "What's the current status?"*

💡 **Tips:**
• You can share Google Sheets URLs for specific analysis
• I can access both public and private sheets (with proper permissions)
• Payment queries automatically check the Brand Balances sheet

Just mention me with `@Sara` and ask away! 🚀"""
            say(help_message, thread_ts=thread_ts)
        else:
            say("🤔 I couldn't understand what you meant. Can you rephrase?", thread_ts=thread_ts)


# ─── Flask Routes for Slack Events ───────────────────────────────────────
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    # Handle Slack URL verification challenge
    if request.json and "challenge" in request.json:
        return {"challenge": request.json["challenge"]}
    
    # Handle regular Slack events
    if handler:
        return handler.handle(request)
    else:
        return {"error": "Slack handler not initialized"}, 500


@flask_app.route("/health", methods=["GET"])
def health_check():
    return {
        "status": "healthy", 
        "service": "Sara Bot",
        "timestamp": "2025-07-29T07:49:03.123456",
        "version": "1.0.0"
    }, 200


@flask_app.route("/", methods=["GET"])
def home():
    return {"message": "Sara Bot is running!", "status": "active"}, 200


# ─── Register Event Handlers ─────────────────────────────────────────────
# Register event handlers if slack_app is initialized
if slack_app:
    slack_app.event("app_mention")(route_mention)
    slack_app.event("message")(handle_all_messages)
    print("✅ Slack event handlers registered")


# ─── Start the Flask App ─────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"⚡️ Sara HTTP Orchestrator starting on port {port}...")
    flask_app.run(host="0.0.0.0", port=port, debug=False)
