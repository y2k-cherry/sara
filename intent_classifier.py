# intent_classifier.py
import os
import openai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_intent_from_text(text: str) -> str:
    """
    Uses LLM to classify the user's intent.
    Returns one of: 'generate_agreement', 'get_status', 'get_payment_info', 'lookup_sheets', 'send_email', 'unknown'
    """
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

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
    )

    return response.choices[0].message.content.strip()
