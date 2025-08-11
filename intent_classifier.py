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
    Uses pattern matching first, then LLM as fallback to classify the user's intent.
    Returns one of: 'generate_agreement', 'get_status', 'lookup_sheets', 'send_email', 'brand_info', 'help', 'unknown'
    """
    text_lower = text.lower().strip()
    
    # PRIORITY 1: Payment/Sheets queries (most critical - must work reliably)
    payment_patterns = [
        "who hasn't paid", "who hasnt paid", "who has not paid", "havent paid", "haven't paid",
        "unpaid brands", "negative balance", "outstanding balance", "who owes", "payment due",
        "brands that owe", "overdue", "brands with negative", "who needs to pay",
        "payment status", "outstanding payments", "negative balances"
    ]
    
    # Check payment patterns first (exact matches)
    for pattern in payment_patterns:
        if pattern in text_lower:
            return 'lookup_sheets'
    
    # Additional sheets patterns
    sheets_patterns = [
        "sheet", "spreadsheet", "data", "how many", "count", "analyze", 
        "lookup", "check", "brands", "metrics", "numbers", "balance"
    ]
    
    # If contains sheets keywords, likely a sheets query
    if any(pattern in text_lower for pattern in sheets_patterns):
        return 'lookup_sheets'
    
    # PRIORITY 2: Brand information queries
    import re
    
    # Specific brand patterns (regex for precise matching)
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
    
    for pattern in brand_specific_patterns:
        if re.search(pattern, text_lower):
            return 'brand_info'
    
    # Brand info keyword combinations
    brand_info_indicators = [
        ('fetch', 'info'), ('fetch', 'details'), ('show', 'info'), 
        ('what\'s', 'gst'), ('what is', 'gst'), ('gst', 'number'), 
        ('gst', 'details'), ('brand', 'id'), ('company', 'info'),
        ('brand', 'info'), ('brand', 'details')
    ]
    
    for word1, word2 in brand_info_indicators:
        if word1 in text_lower and word2 in text_lower:
            return 'brand_info'
    
    # Known brand names with info requests
    brand_keywords = ['freakins', 'yama yoga', 'fae', 'inde wild', 'theater']
    info_keywords = ['info', 'details', 'gst', 'brand id', 'information']
    
    has_brand = any(brand in text_lower for brand in brand_keywords)
    has_info_request = any(info_word in text_lower for info_word in info_keywords)
    
    if has_brand and has_info_request:
        return 'brand_info'
    
    # PRIORITY 3: Other specific intents
    
    # Agreement generation
    agreement_patterns = ['generate agreement', 'create agreement', 'agreement for', 'partnership agreement']
    if any(pattern in text_lower for pattern in agreement_patterns):
        return 'generate_agreement'
    
    # Email sending
    email_patterns = ['send email', 'email to', 'send an email', 'draft email', 'compose email', 'email about']
    if any(pattern in text_lower for pattern in email_patterns):
        return 'send_email'
    
    # Status queries
    status_patterns = ['status', 'current status', 'what\'s the status', 'project status']
    if any(pattern in text_lower for pattern in status_patterns):
        return 'get_status'
    
    # Help requests
    help_patterns = [
        'help', 'what can you do', 'what all can you do', 'capabilities', 
        'functions', 'services', 'how can you help', 'what are your capabilities',
        'what functions do you have', 'what services do you provide'
    ]
    if any(pattern in text_lower for pattern in help_patterns):
        return 'help'
    
    # FALLBACK: Try OpenAI only if pattern matching fails
    try:
        openai_client = get_openai_client()
        
        # Only use OpenAI if we have a working client (not the mock)
        if hasattr(openai_client, 'chat') and hasattr(openai_client.chat, 'completions'):
            # Check if it's the real OpenAI client by testing a method
            if not hasattr(openai_client.chat.completions.create, '__self__'):  # Real method, not mock
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

CRITICAL: Payment queries like "who hasn't paid", "unpaid brands", "negative balance" should ALWAYS be classified as "lookup_sheets".
"""

                response = openai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0,
                )
                result = response.choices[0].message.content.strip()
                
                # Validate the result is one of our expected intents
                valid_intents = ['generate_agreement', 'get_status', 'lookup_sheets', 'send_email', 'brand_info', 'help', 'unknown']
                if result in valid_intents:
                    return result
    except Exception as e:
        print(f"OpenAI fallback failed: {e}")
    
    # Final fallback: return 'unknown' if nothing matches
    return 'unknown'
