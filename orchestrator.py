import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agreement_service import handle_agreement
from deposit_invoice_service_v2 import handle_deposit_invoice, is_in_deposit_invoice_flow
from utils import clean_slack_text
from intent_classifier import get_intent_from_text
from status_service import read_google_doc_text
from sheets_service import sheets_service
from direct_sheets_service import DirectSheetsService
from email_service import handle_email_request, handle_email_confirmation
from brand_info_service import BrandInfoService
from service_status_checker import ServiceStatusChecker


# 1️⃣ Load environment variables early
load_dotenv()

# 2️⃣ Initialize Slack Bolt in Socket Mode
app = App(token=os.getenv("SLACK_BOT_TOKEN"))
socket_handler = SocketModeHandler(app, os.getenv("SLACK_APP_TOKEN"))

# 3️⃣ Get bot ID for thread detection
bot_user_id = app.client.auth_test()["user_id"]

# 4️⃣ Initialize Direct Sheets Service
try:
    direct_sheets = DirectSheetsService()
    print("✅ Direct Sheets Service initialized")
except Exception as e:
    print(f"⚠️  Direct Sheets Service failed to initialize: {e}")
    direct_sheets = None

# 5️⃣ Initialize Brand Info Service
try:
    brand_info_service = BrandInfoService()
    print("✅ Brand Info Service initialized")
except Exception as e:
    print(f"⚠️  Brand Info Service failed to initialize: {e}")
    brand_info_service = None


# ─── Function: route_mention ─────────────────────────────────────────────
@app.event("app_mention")
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
    elif intent == "brand_info":
        say("🔍 Looking up brand information...", thread_ts=event["ts"])
        try:
            if brand_info_service:
                # Pass thread_ts as thread_id for confirmation handling
                response = brand_info_service.process_brand_query(cleaned_text, thread_id=event["ts"])
                say(f"🏢 {response}", thread_ts=event["ts"])
            else:
                say("❌ Brand information service is not available.", thread_ts=event["ts"])
        except Exception as e:
            say(f"❌ Error looking up brand information: {str(e)}", thread_ts=event["ts"])
    elif intent == "generate_deposit_invoice":
        # Check if we have cached brand data for this thread
        brand_data = None
        if brand_info_service and event["ts"] in brand_info_service.brand_data_cache:
            brand_data = brand_info_service.get_brand_data_for_invoice(event["ts"])
        
        # Handle deposit invoice generation
        handle_deposit_invoice(event, say, brand_data=brand_data)
    elif intent == "service_status":
        say("🔍 Checking all service statuses...", thread_ts=event["ts"])
        try:
            status_checker = ServiceStatusChecker()
            status_report = status_checker.format_status_report()
            say(status_report, thread_ts=event["ts"])
        except Exception as e:
            say(f"❌ Error checking service status: {str(e)}", thread_ts=event["ts"])
    elif intent == "help":
        help_message = """👋 **Hi! I'm Sara, your AI assistant. Here's what I can help you with:**

🤝 **Partnership Agreements**
• Generate custom partnership agreements
• *Example: "Generate an agreement for XYZ Company"*

🏢 **Brand Information**
• Fetch detailed brand information from the Brand Master sheet
• Get GST numbers, brand IDs, and other company details
• *Examples: "fetch Freakins info", "What's FAE's GST number", "Show me info for Yama Yoga"*

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

🔧 **Service Status**
• Check the health of all Sara services and diagnose issues
• *Example: "service status" or "health check"*

💡 **Tips:**
• You can share Google Sheets URLs for specific analysis
• I can access both public and private sheets (with proper permissions)
• Payment queries automatically check the Brand Balances sheet
• Brand queries use fuzzy matching to find similar names

Just mention me with `@Sara` and ask away! 🚀"""
        say(help_message, thread_ts=event["ts"])
    else:
        say("🤔 Sorry, I couldn't understand what you're asking. Can you rephrase?", thread_ts=event["ts"])


# ─── Function: handle_all_messages (thread replies) ──────────────────────
@app.event("message")
def handle_all_messages(body, say, client, logger):
    """
    Handle messages in threads where Sara was mentioned in the parent message.
    Maintains context from parent message for intent detection.
    """
    event = body.get("event", {})
    
    # Ignore bot messages
    if event.get("bot_id"):
        return

    thread_ts = event.get("thread_ts")
    
    # Only process if it's a thread reply (not a top-level message)
    if not thread_ts:
        return

    channel = event["channel"]
    user_text = event.get("text", "")
    
    print(f"📨 [THREAD] Received message in thread {thread_ts}")
    print(f"📨 [THREAD] User text: {user_text[:100]}...")

    # Fetch parent message to check context
    try:
        resp = client.conversations_replies(channel=channel, ts=thread_ts, limit=1)
        parent_text = resp["messages"][0].get("text", "")
        print(f"📨 [THREAD] Parent message: {parent_text[:100]}...")
    except Exception as e:
        logger.error("Failed to fetch thread replies: %s", e)
        return

    # Only process if Sara was mentioned in the parent message
    if f"<@{bot_user_id}>" not in parent_text:
        print(f"📨 [THREAD] Sara not mentioned in parent, ignoring")
        return
    
    print(f"📨 [THREAD] Sara was mentioned in parent, processing thread reply")

    # CRITICAL: Check if we're in an active deposit invoice flow BEFORE intent classification
    # If the user is expected to provide amount/invoice number, route directly to handler
    if is_in_deposit_invoice_flow(thread_ts):
        print(f"📨 [THREAD] Thread is in active deposit invoice flow - bypassing intent classification")
        say("🔄 Got it, one sec...", thread_ts=thread_ts)
        
        # Get cached brand data if available
        brand_data = None
        if brand_info_service and thread_ts in brand_info_service.brand_data_cache:
            brand_data = brand_info_service.get_brand_data_for_invoice(thread_ts)
        
        # Route directly to deposit invoice handler with user text only
        handle_deposit_invoice({**event, "text": user_text}, say, brand_data=brand_data)
        return

    # Combine parent and user text for context
    combined_text = parent_text + "\n" + user_text
    cleaned_text = clean_slack_text(combined_text).lower()
    
    # Get intent from combined text
    intent = get_intent_from_text(cleaned_text)
    print(f"📨 [THREAD] Detected intent: {intent}")

    say("🔄 Got it, one sec...", thread_ts=thread_ts)

    # First check if this is an email confirmation
    if handle_email_confirmation(event, say):
        print(f"📨 [THREAD] Email confirmation handled")
        return  # Email confirmation handled, don't process further
    
    #Process based on intent
    if intent == "generate_agreement":
        handle_agreement({**event, "text": combined_text}, say)
    elif intent == "get_status":
        say("📊 Status checks coming soon!", thread_ts=thread_ts)
    elif intent == "send_email":
        handle_email_request({**event, "text": combined_text}, say)
    elif intent == "brand_info":
        try:
            if brand_info_service:
                # Pass thread_ts as thread_id for confirmation handling
                # Use user_text only (not combined_text) to detect confirmation
                response = brand_info_service.process_brand_query(user_text.lower().strip(), thread_id=thread_ts)
                say(f"🏢 {response}", thread_ts=thread_ts)
            else:
                say("❌ Brand information service is not available.", thread_ts=thread_ts)
        except Exception as e:
            say(f"❌ Error looking up brand information: {str(e)}", thread_ts=thread_ts)
    elif intent == "generate_deposit_invoice":
        print(f"📨 [THREAD] Processing deposit invoice request")
        
        # Check if we have cached brand data for this thread
        brand_data = None
        if brand_info_service and thread_ts in brand_info_service.brand_data_cache:
            brand_data = brand_info_service.get_brand_data_for_invoice(thread_ts)
            print(f"📨 [THREAD] Found cached brand data: {bool(brand_data)}")
        else:
            print(f"📨 [THREAD] No cached brand data found")
        
        # Handle deposit invoice generation with combined text
        # IMPORTANT: Use combined_text which includes parent context
        print(f"📨 [THREAD] Calling handle_deposit_invoice with combined text")
        handle_deposit_invoice({**event, "text": combined_text}, say, brand_data=brand_data)
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


# ─── Start the Socket Mode App ───────────────────────────────────────────
if __name__ == "__main__":
    print("⚡️ Sara Orchestrator running…")
    socket_handler.start()
