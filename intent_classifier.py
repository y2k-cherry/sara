# intent_classifier.py
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client lazily to avoid import-time errors
client = None

def get_openai_client():
    global client
    if client is None:
        try:
            # Try with just the API key first
            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            print(f"⚠️  OpenAI client initialization failed in intent_classifier: {e}")
            # Skip the second attempt that also fails - go straight to mock client
            print("⚠️  Using mock OpenAI client - defaulting to 'help' intent")
            client = type('MockClient', (), {
                'chat': type('Chat', (), {
                    'completions': type('Completions', (), {
                        'create': lambda *args, **kwargs: type('Response', (), {
                            'choices': [type('Choice', (), {
                                'message': type('Message', (), {
                                    'content': 'help'  # Default to help intent
                                })()
                            })()]
                        })()
                    })()
                })()
            })()
    return client

def get_intent_from_text(text: str) -> str:
    """
    Uses LLM to classify the user's intent.
    Returns one of: 'generate_agreement', 'get_status', 'get_payment_info', 'lookup_sheets', 'send_email', 'unknown'
    """
    # First try basic pattern matching for common intents (fallback when OpenAI fails)
    text_lower = text.lower().strip()
    
    # Check for agreement generation
    if any(word in text_lower for word in ['generate agreement', 'create agreement', 'agreement for']):
        return 'generate_agreement'
    
    # Check for email sending
    if any(word in text_lower for word in ['send email', 'email to', 'send an email', 'draft email', 'compose email']):
        return 'send_email'
    
    # Check for sheets/payment queries
    payment_patterns = ["who hasn't paid", "who has not paid", "unpaid brands", "negative balance", "outstanding balance", "who owes", "payment due"]
    sheets_patterns = ["sheet", "spreadsheet", "data", "brands", "how many", "count", "analyze", "lookup", "check"]
    
    if any(pattern in text_lower for pattern in payment_patterns):
        return 'lookup_sheets'
    
    if any(pattern in text_lower for pattern in sheets_patterns):
        return 'lookup_sheets'
    
    # Check for status queries
    if any(word in text_lower for word in ['status', 'current status', 'what\'s the status']):
        return 'get_status'
    
    # Check for help requests
    help_patterns = ['help', 'what can you do', 'what all can you do', 'capabilities', 'functions', 'services', 'how can you help']
    if any(pattern in text_lower for pattern in help_patterns):
        return 'help'
    
    # Try OpenAI if basic patterns don't match
    prompt = f"""
You are a Slack bot assistant. Classify the intent of the following message from a user.

Message: "{text}"

Respond with only one of the following:
- generate_agreement (for creating partnership agreements)
- get_status (for checking status information)
- lookup_sheets (for looking up data in Google Sheets, spreadsheets, payment info, or any data queries)
- send_email (for sending emails to people)
- help (for questions about what Sara can do or help requests)
- unknown

Examples of send_email intent:
- "Send an email to john@example.com about the meeting"
- "Email Sarah about the project update"
- "Send a follow-up email to the client"
- "Draft an email to the team about the deadline"
- "Email the vendor about the invoice"
- Any request to send, draft, or compose an email

Examples of lookup_sheets intent:
- "What's in the sales data sheet?"
- "Show me the Q4 numbers"
- "Look up customer information"
- "Check the inventory spreadsheet"
- "What are the latest metrics?"
- "Who hasn't paid?"
- "Who owes money?"
- "Payment status"
- "Outstanding balances"
- "Unpaid brands"
- Any query about data, numbers, payments, or information that might be in a spreadsheet

Examples of help intent:
- "What can you do?"
- "What all can you do?"
- "Help"
- "What are your capabilities?"
- "What functions do you have?"
- "How can you help me?"
- "What services do you provide?"
- Any question asking about Sara's capabilities or functionality
"""

    try:
        openai_client = get_openai_client()
        response = openai_client.chat.completions.create(
            model="gpt-4",  # or "gpt-3.5-turbo"
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return response.choices[0].message.content.strip()
    except:
        # If OpenAI fails completely, return 'unknown' instead of always 'help'
        return 'unknown'
