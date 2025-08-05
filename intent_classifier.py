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
    Returns one of: 'generate_agreement', 'get_status', 'get_payment_info', 'lookup_sheets', 'send_email', 'brand_info', 'unknown'
    """
    # First try basic pattern matching for common intents (fallback when OpenAI fails)
    text_lower = text.lower().strip()
    
    # Check for brand information queries - PRIORITY CHECK
    import re
    
    # Specific patterns for brand queries (more precise matching)
    brand_specific_patterns = [
        r'fetch\s+\w+.*info',
        r'fetch\s+\w+.*details',
        r'show\s+me\s+info\s+for\s+\w+',
        r'what\'?s\s+\w+.*gst',
        r'do\s+we\s+have\s+\w+.*gst',
        r'what\s+is\s+\w+.*brand\s+id',
        r'\w+.*info$',
        r'info\s+for\s+\w+',
        r'get\s+\w+.*info',
        r'\w+.*details$'
    ]
    
    # Check specific brand patterns first
    for pattern in brand_specific_patterns:
        if re.search(pattern, text_lower):
            return 'brand_info'
    
    # Check for brand-related keywords combined with info requests
    brand_info_indicators = [
        ('fetch', 'info'), ('fetch', 'details'), ('show', 'info'), 
        ('what\'s', 'gst'), ('what is', 'gst'), ('gst', 'number'), 
        ('gst', 'details'), ('brand', 'id'), ('company', 'info'),
        ('brand', 'info'), ('brand', 'details')
    ]
    
    for word1, word2 in brand_info_indicators:
        if word1 in text_lower and word2 in text_lower:
            return 'brand_info'
    
    # Check for known brand names with info requests
    brand_keywords = ['freakins', 'yama yoga', 'fae', 'inde wild', 'theater']
    info_keywords = ['info', 'details', 'gst', 'brand id', 'information']
    
    has_brand = any(brand in text_lower for brand in brand_keywords)
    has_info_request = any(info_word in text_lower for info_word in info_keywords)
    
    if has_brand and has_info_request:
        return 'brand_info'
    
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
- brand_info (for fetching brand information, GST numbers, brand IDs, company details)
- help (for questions about what Sara can do or help requests)
- unknown

Examples of brand_info intent:
- "fetch Freakins info"
- "Show me info for Yama Yoga"
- "What's FAE's GST number"
- "Do we have inde wild's GST details"
- "What is Theater's brand ID"
- "Get brand information for XYZ Company"
- "Fetch company details for ABC Corp"
- Any request for brand/company information, GST numbers, brand IDs, or company details

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
