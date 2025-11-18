import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from flask import Flask, request

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

# Load environment variables
load_dotenv()

# Initialize Flask app first - MUST be available for Gunicorn
flask_app = Flask(__name__)

# Initialize Slack Bolt App (HTTP Mode) with error handling
slack_app = None
handler = None
bot_user_id = None

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
    print("⚠️  Continuing with Flask app only...")

# Ensure app variable is always available for Gunicorn
app = flask_app

# Initialize Direct Sheets Service
try:
    direct_sheets = DirectSheetsService()
    print("✅ Direct Sheets Service initialized")
except Exception as e:
    print(f"⚠️  Direct Sheets Service failed to initialize: {e}")
    print("⚠️  Creating fallback DirectSheetsService...")
    # Create a minimal fallback service
    class FallbackDirectSheetsService:
        def process_sheets_query(self, sheet_url, query):
            return "I couldn't connect to Google Drive. Please run the authentication setup: `python3 setup_auth.py`"
    direct_sheets = FallbackDirectSheetsService()

# Initialize Brand Info Service
try:
    brand_info_service = BrandInfoService()
    print("✅ Brand Info Service initialized")
except Exception as e:
    print(f"⚠️  Brand Info Service failed to initialize: {e}")
    brand_info_service = None

# State management for pending agreements (thread_ts -> original_message)
pending_agreement_info = {}

# State management for expected response types (thread_ts -> response_type)
# Types: 'agreement_details', 'brand_confirmation', 'email_confirmation', etc.
expected_response_context = {}

# ─── Function: route_mention ─────────────────────────────────────────────
def route_mention(event, say):
    print(f"🎯 route_mention called with event: {event}")
    raw_text = event["text"]
    cleaned_text = clean_slack_text(raw_text).lower()
    print(f"🎯 Raw text: {raw_text}")
    print(f"🎯 Cleaned text: {cleaned_text}")

    intent = get_intent_from_text(cleaned_text)
    print(f"🎯 Detected intent: {intent}")
    
    # Extra debug for agreement generation
    if "agreement" in cleaned_text.lower():
        print(f"🔍 AGREEMENT DEBUG: Message contains 'agreement'")
        print(f"🔍 AGREEMENT DEBUG: Intent classification result: {intent}")
        print(f"🔍 AGREEMENT DEBUG: Should route to agreement handler: {intent == 'generate_agreement'}")

    if intent == "generate_agreement":
        handle_agreement(event, say)
    elif intent == "generate_deposit_invoice":
        # Check if we have brand data from recent lookup
        if brand_info_service and event["ts"] in brand_info_service.brand_data_cache:
            brand_data = brand_info_service.get_brand_data_for_invoice(event["ts"])
            handle_deposit_invoice(event, say, brand_data)
        else:
            handle_deposit_invoice(event, say)
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
                
                # Send follow-up action prompt in a separate message with options
                if "✅ Found information for" in response:
                    # Mark that we're waiting for a choice
                    if brand_info_service:
                        brand_info_service.pending_agreement[event["ts"]] = True
                        brand_info_service.pending_invoice[event["ts"]] = True
                    say("📋 **What would you like to do next?**\n\n• Type 'agreement' to generate a partnership agreement\n• Type 'invoice' to generate a deposit invoice\n• Or just continue with another query", thread_ts=event["ts"])
            else:
                say("❌ Brand information service is not available.", thread_ts=event["ts"])
        except Exception as e:
            say(f"❌ Error looking up brand information: {str(e)}", thread_ts=event["ts"])
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

        # CRITICAL: Check ALL expected response contexts BEFORE intent classification
        # This ensures context-aware responses don't get misrouted
        
        # Check if user is choosing between agreement or invoice after brand lookup
        if brand_info_service and thread_ts in brand_info_service.pending_agreement and thread_ts in brand_info_service.pending_invoice:
            user_choice = user_text.lower().strip()
            
            if 'agreement' in user_choice:
                say("🔄 Got it, one sec...", thread_ts=thread_ts)
                # User chose agreement - generate it
                brand_data = brand_info_service.get_brand_data_for_agreement(thread_ts)
                if brand_data:
                    # Clear pending states
                    del brand_info_service.pending_agreement[thread_ts]
                    del brand_info_service.pending_invoice[thread_ts]
                    
                    # Format message with brand data for agreement service
                    agreement_message = f"Generate an agreement for {brand_data['company_name']}\n"
                    agreement_message += f"Legal name: {brand_data['registered_company_name']}\n"
                    agreement_message += f"Address: {brand_data['address']}"
                    
                    # Store the original agreement message for potential follow-up
                    pending_agreement_info[thread_ts] = agreement_message
                    
                    # Mark that we're expecting agreement details as follow-up
                    expected_response_context[thread_ts] = 'agreement_details'
                    
                    # Create a modified event with the formatted message
                    agreement_event = {**event, "text": agreement_message}
                    say("📝 Generating partnership agreement using brand information...", thread_ts=thread_ts)
                    handle_agreement(agreement_event, say)
                    return
                    
            elif 'invoice' in user_choice:
                say("🔄 Got it, one sec...", thread_ts=thread_ts)
                # User chose invoice - ask for amount
                brand_data = brand_info_service.get_brand_data_for_agreement(thread_ts)
                if brand_data:
                    # Clear pending states
                    del brand_info_service.pending_agreement[thread_ts]
                    del brand_info_service.pending_invoice[thread_ts]
                    
                    # Ask for deposit amount
                    say("💰 Please provide the deposit amount (e.g., '5000' or 'Rs 5000')", thread_ts=thread_ts)
                    
                    # Store brand data for invoice generation
                    # We'll use expected_response_context to catch the amount
                    expected_response_context[thread_ts] = 'invoice_amount'
                    return
            else:
                # User said something else - clear pending states
                del brand_info_service.pending_agreement[thread_ts]
                del brand_info_service.pending_invoice[thread_ts]
                say("👍 No problem! Let me know if you need anything else.", thread_ts=thread_ts)
                return
        
        # Legacy check for old yes/no confirmation (for backward compatibility)
        if brand_info_service and thread_ts in brand_info_service.pending_agreement:
            confirmation_words = ['yes', 'yeah', 'yep', 'yup', 'sure', 'ok', 'okay', 'confirm', 'correct', 'right']
            if user_text.lower().strip() in confirmation_words:
                say("🔄 Got it, one sec...", thread_ts=thread_ts)
                # User confirmed - generate agreement
                brand_data = brand_info_service.get_brand_data_for_agreement(thread_ts)
                if brand_data:
                    # Clear pending state
                    del brand_info_service.pending_agreement[thread_ts]
                    
                    # Format message with brand data for agreement service
                    agreement_message = f"Generate an agreement for {brand_data['company_name']}\n"
                    agreement_message += f"Legal name: {brand_data['registered_company_name']}\n"
                    agreement_message += f"Address: {brand_data['address']}"
                    
                    # Store the original agreement message for potential follow-up
                    pending_agreement_info[thread_ts] = agreement_message
                    
                    # Mark that we're expecting agreement details as follow-up
                    expected_response_context[thread_ts] = 'agreement_details'
                    
                    # Create a modified event with the formatted message
                    agreement_event = {**event, "text": agreement_message}
                    say("📝 Generating partnership agreement using brand information...", thread_ts=thread_ts)
                    handle_agreement(agreement_event, say)
                    return
            else:
                # User declined or said something else
                del brand_info_service.pending_agreement[thread_ts]
                say("👍 No problem! Let me know if you need anything else.", thread_ts=thread_ts)
                return
        
        say("🔄 Got it, one sec...", thread_ts=thread_ts)

        # First check if this is an email confirmation
        if handle_email_confirmation(event, say):
            return  # Email confirmation handled, don't process further
        
        # Check expected response context FIRST (before intent classification)
        if thread_ts in expected_response_context:
            context_type = expected_response_context[thread_ts]
            
            if context_type == 'agreement_details' and thread_ts in pending_agreement_info:
                # User is providing missing agreement details
                original_message = pending_agreement_info[thread_ts]
                combined_agreement_text = f"{original_message}\n{user_text}"
                
                # Create event with combined text
                combined_event = {**event, "text": combined_agreement_text}
                say("📝 Adding the details and generating agreement...", thread_ts=thread_ts)
                handle_agreement(combined_event, say)
                
                # Clean up both pending states
                del pending_agreement_info[thread_ts]
                del expected_response_context[thread_ts]
                return
            
            elif context_type == 'invoice_amount':
                # User is providing deposit amount for invoice
                brand_data = brand_info_service.get_brand_data_for_invoice(thread_ts) if brand_info_service else None
                
                if brand_data:
                    # Create invoice message with brand data and amount
                    invoice_message = f"generate invoice for {user_text}"
                    
                    # Create event with combined text
                    invoice_event = {**event, "text": invoice_message}
                    say("🧾 Generating deposit invoice...", thread_ts=thread_ts)
                    handle_deposit_invoice(invoice_event, say, brand_data)
                    
                    # Clean up context state
                    del expected_response_context[thread_ts]
                else:
                    say("❌ Sorry, I lost the brand data. Please start over by fetching the brand info first.", thread_ts=thread_ts)
                    del expected_response_context[thread_ts]
                return
        
        # Check if there's a pending agreement that needs more info (fallback)
        if thread_ts in pending_agreement_info:
            # User is providing missing info - combine with original message
            original_message = pending_agreement_info[thread_ts]
            combined_agreement_text = f"{original_message}\n{user_text}"
            
            # Create event with combined text
            combined_event = {**event, "text": combined_agreement_text}
            say("📝 Adding the details and generating agreement...", thread_ts=thread_ts)
            handle_agreement(combined_event, say)
            
            # Clean up pending state
            del pending_agreement_info[thread_ts]
            return
        
        # NOW perform intent classification (only after all context checks passed)
        intent = get_intent_from_text(cleaned_text)
        
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

💡 **Tips:**
• You can share Google Sheets URLs for specific analysis
• I can access both public and private sheets (with proper permissions)
• Payment queries automatically check the Brand Balances sheet
• Brand queries use fuzzy matching to find similar names

Just mention me with `@Sara` and ask away! 🚀"""
            say(help_message, thread_ts=thread_ts)
        else:
            say("🤔 I couldn't understand what you meant. Can you rephrase?", thread_ts=thread_ts)


# ─── Flask Routes for Slack Events ───────────────────────────────────────
@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    try:
        # Log all incoming requests for debugging
        print(f"🔍 Received POST to /slack/events")
        print(f"🔍 Request headers: {dict(request.headers)}")
        print(f"🔍 Request data: {request.get_data(as_text=True)}")
        
        # Handle Slack URL verification challenge
        if request.json and "challenge" in request.json:
            challenge = request.json["challenge"]
            print(f"✅ Slack challenge received: {challenge}")
            return {"challenge": challenge}, 200
        
        # Handle regular Slack events
        if handler:
            print("📨 Processing Slack event with handler...")
            try:
                result = handler.handle(request)
                print(f"✅ Handler processed event successfully: {result}")
                return result
            except Exception as handler_error:
                print(f"❌ Handler error: {handler_error}")
                import traceback
                print(f"❌ Handler traceback: {traceback.format_exc()}")
                return {"error": f"Handler error: {str(handler_error)}"}, 500
        else:
            print("❌ Slack handler not initialized")
            return {"error": "Slack handler not initialized"}, 500
            
    except Exception as e:
        print(f"❌ Error in slack_events endpoint: {e}")
        import traceback
        print(f"❌ Full traceback: {traceback.format_exc()}")
        return {"error": str(e)}, 500


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


@flask_app.route("/slack/events", methods=["GET"])
def slack_events_get():
    """Handle GET requests to /slack/events for debugging"""
    return {
        "message": "Slack events endpoint is working",
        "method": "GET",
        "slack_handler_initialized": handler is not None,
        "slack_app_initialized": slack_app is not None
    }, 200


# ─── Register Event Handlers ─────────────────────────────────────────────
# Register event handlers if slack_app is initialized
if slack_app:
    slack_app.event("app_mention")(route_mention)
    slack_app.event("message")(handle_all_messages)
    print("✅ Slack event handlers registered")
    
    # Send startup notification only to testing channel
    try:
        startup_message = "👋 Hi! I have restarted and I'm ready to help!"
        channel = "#sara-testing"
        
        try:
            slack_app.client.chat_postMessage(
                channel=channel,
                text=startup_message
            )
            print(f"✅ Startup notification sent to {channel}")
        except Exception as channel_error:
            print(f"⚠️  Failed to send startup notification to {channel}: {channel_error}")
    except Exception as e:
        print(f"⚠️  Failed to send startup notification: {e}")


# ─── Start the Flask App ─────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    print(f"⚡️ Sara HTTP Orchestrator starting on port {port}...")
    flask_app.run(host="0.0.0.0", port=port, debug=False)
