# agreement_service.py

import os
import re
import json
from datetime import date

from slack_sdk import WebClient
from openai import OpenAI
from docx import Document


from dotenv import load_dotenv

load_dotenv()

# Google Docs–based PDF exporter
from google_pdf import convert_docx_to_pdf_google as convert_docx_to_pdf

# load your environment variables (ensure .env is loaded in orchestrator)
SLACK_TOKEN      = os.getenv("SLACK_BOT_TOKEN")
OPENAI_API_KEY   = os.getenv("OPENAI_API_KEY")
TEMPLATE_PATH    = "Partnership Agreement Template.docx"

# init clients
slack_client = WebClient(token=SLACK_TOKEN)

# Initialize OpenAI client lazily to avoid import-time errors
openai_client = None

def get_openai_client():
    global openai_client
    if openai_client is None:
        try:
            openai_client = OpenAI(api_key=OPENAI_API_KEY)
        except Exception as e:
            print(f"⚠️  OpenAI client initialization failed in agreement_service: {e}")
            # Create a mock client that tries to parse the message manually
            print("⚠️  Using mock OpenAI client for agreement service")
            def mock_create(*args, **kwargs):
                # Try to extract basic info from the message
                messages = kwargs.get('messages', [])
                user_message = ""
                for msg in messages:
                    if msg.get('role') == 'user':
                        user_message = msg.get('content', '')
                        break
                
                # Manual field extraction from the message
                import re
                
                # Extract brand name
                brand_match = re.search(r'(?:for|with|brand)\s+([A-Za-z0-9\s&]+?)(?:,|$|\s+Legal)', user_message, re.IGNORECASE)
                brand_name = brand_match.group(1).strip() if brand_match else ""
                
                # Extract legal name/company name
                legal_match = re.search(r'Legal name:\s*([^,]+)', user_message, re.IGNORECASE)
                company_name = legal_match.group(1).strip() if legal_match else ""
                
                # Extract address
                address_match = re.search(r'Address:\s*([^.]+\.)', user_message, re.IGNORECASE)
                company_address = address_match.group(1).strip() if address_match else ""
                
                # Extract deposit
                deposit_match = re.search(r'Deposit:\s*Rs\.?\s*([0-9,]+)', user_message, re.IGNORECASE)
                deposit = deposit_match.group(1).replace(',', '') if deposit_match else ""
                
                # Extract fee - handle multiple separators including semicolon
                fee_patterns = [
                    r'Flat\s+Fee[;\s:,]*Rs\.?\s*([0-9,]+)',  # Added comma separator
                    r'(?:Flat\s+)?Fee[;\s:,]*Rs\.?\s*([0-9,]+)',  # Added comma separator
                    r'Fee[;\s:,]*Rs\.?\s*([0-9,]+)',  # Added comma separator
                    r'Rs\.?\s*([0-9,]+).*(?:fee|Fee)',
                    r'Rs\.?\s*([0-9,]+)(?:\s*[,.]|\s*$)',  # More flexible end pattern
                    r'(?:fee|Fee)[;\s:,]*Rs\.?\s*([0-9,]+)',  # Fee before Rs
                    r'([0-9,]+)\s*(?:rs|Rs|RS)\.?\s*(?:fee|Fee)',  # Number before Rs fee
                ]
                flat_fee = ""
                for i, pattern in enumerate(fee_patterns):
                    fee_match = re.search(pattern, user_message, re.IGNORECASE)
                    if fee_match:
                        flat_fee = fee_match.group(1).replace(',', '')
                        print(f"🔍 DEBUG: Mock client found fee with pattern {i+1} '{pattern}': {flat_fee}")
                        break
                
                if not flat_fee:
                    print(f"🔍 DEBUG: Mock client could not find fee in message: {user_message}")
                    # Try even more aggressive patterns as last resort
                    aggressive_patterns = [
                        r'(\d+)\s*(?:rs|Rs|RS)',  # Any number followed by rs
                        r'Rs\.?\s*(\d+)',  # Rs followed by number
                        r'(\d+).*(?:fee|Fee)',  # Any number with fee somewhere after
                    ]
                    for i, pattern in enumerate(aggressive_patterns):
                        fee_match = re.search(pattern, user_message, re.IGNORECASE)
                        if fee_match:
                            potential_fee = fee_match.group(1)
                            # Only accept if it's a reasonable fee amount (not deposit-like)
                            if int(potential_fee) < 10000:  # Assume fees are less than 10k
                                flat_fee = potential_fee
                                print(f"🔍 DEBUG: Mock client found fee with aggressive pattern {i+1}: {flat_fee}")
                                break
                
                # Extract industry/field
                field_match = re.search(r'Field:\s*([^,\n]+)', user_message, re.IGNORECASE)
                industry = field_match.group(1).strip() if field_match else ""
                
                # Convert deposit to words
                deposit_in_words = ""
                if deposit:
                    try:
                        deposit_num = int(deposit)
                        deposit_in_words = convert_number_to_words(str(deposit_num))
                    except:
                        pass
                
                result_json = {
                    "brand_name": brand_name,
                    "company_name": company_name,
                    "company_address": company_address,
                    "industry": industry,
                    "flat_fee": flat_fee,
                    "deposit": deposit,
                    "deposit_in_words": deposit_in_words
                }
                
                return type('Response', (), {
                    'choices': [type('Choice', (), {
                        'message': type('Message', (), {
                            'content': json.dumps(result_json)
                        })()
                    })()]
                })()
            
            openai_client = type('MockClient', (), {
                'chat': type('Chat', (), {
                    'completions': type('Completions', (), {
                        'create': mock_create
                    })()
                })()
            })()
    return openai_client

# which fields we need
REQUIRED_FIELDS = [
    "brand_name",
    "company_name",
    "company_address",
    "industry",
    "flat_fee",
    "deposit",
    "deposit_in_words"
]


def clean_text(text: str) -> str:
    """Strip Slack mentions and extra whitespace."""
    return re.sub(r"<@[\w]+>", "", text).strip()


def format_currency(value: str) -> str:
    """Format an integer/float string as Indian-rupee currency."""
    try:
        num = float(value)
        return f"₹{num:,.0f}".replace(",", ",")
    except:
        return value


def convert_number_to_words(number_str: str) -> str:
    """Convert a number string to words (Indian numbering system)."""
    try:
        num = int(float(number_str))
        
        # Handle common amounts
        if num == 0:
            return "zero"
        elif num < 0:
            return "negative " + convert_number_to_words(str(-num))
        
        # Indian numbering system
        ones = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
        teens = ["ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", 
                "sixteen", "seventeen", "eighteen", "nineteen"]
        tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
        
        def convert_hundreds(n):
            result = ""
            if n >= 100:
                result += ones[n // 100] + " hundred "
                n %= 100
            if n >= 20:
                result += tens[n // 10] + " "
                n %= 10
            elif n >= 10:
                result += teens[n - 10] + " "
                n = 0
            if n > 0:
                result += ones[n] + " "
            return result.strip()
        
        if num >= 10000000:  # 1 crore
            crores = num // 10000000
            result = convert_hundreds(crores) + " crore "
            num %= 10000000
        else:
            result = ""
            
        if num >= 100000:  # 1 lakh
            lakhs = num // 100000
            result += convert_hundreds(lakhs) + " lakh "
            num %= 100000
            
        if num >= 1000:  # 1 thousand
            thousands = num // 1000
            result += convert_hundreds(thousands) + " thousand "
            num %= 1000
            
        if num > 0:
            result += convert_hundreds(num)
            
        return result.strip()
        
    except:
        return number_str  # Return original if conversion fails


def extract_agreement_fields(message_text: str):
    print(f"🔍 DEBUG: Starting field extraction for message: {message_text[:100]}...")
    
    # Check environment variables
    openai_key = os.getenv("OPENAI_API_KEY")
    print(f"🔍 DEBUG: OpenAI API key present: {bool(openai_key)}")
    if openai_key:
        print(f"🔍 DEBUG: OpenAI API key length: {len(openai_key)}")
    
    sys_prompt = (
        "You are Sara, a sales ops AI assistant. Extract agreement details from this message "
        "and return ONLY raw JSON (no markdown, no code fences) with keys: "
        "brand_name, company_name, company_address, industry, flat_fee, deposit, deposit_in_words. "
        
        "CRITICAL FIELD DISTINCTION RULES:\n"
        "- 'deposit' is ONLY the amount explicitly labeled as 'Deposit:' in the message\n"
        "- 'flat_fee' is ONLY the amount explicitly labeled as 'Flat Fee:', 'Fee:', or similar fee-related terms\n"
        "- NEVER use the deposit amount as the flat fee, even if flat fee is missing\n"
        "- NEVER use the flat fee amount as the deposit, even if deposit is missing\n"
        "- If either field is not explicitly mentioned, leave it as an empty string\n"
        
        "EXAMPLES:\n"
        "- 'Deposit: Rs 10,000, Flat Fee: Rs 320' → deposit='10000', flat_fee='320'\n"
        "- 'Deposit: Rs 10,000' (no fee mentioned) → deposit='10000', flat_fee=''\n"
        "- 'Flat Fee: Rs 320' (no deposit mentioned) → deposit='', flat_fee='320'\n"
        
        "For brand_name, extract it from the message even if other details are missing. "
        "If you find a deposit amount in numbers, automatically convert it to words for deposit_in_words. "
        "For example: 10000 becomes 'ten thousand', 50000 becomes 'fifty thousand'. "
        "If information is missing, use empty strings for missing fields. "
        "ALWAYS return valid JSON, never explanatory text."
    )

    # First try OpenAI, but with better error handling for production
    try:
        print("🔍 DEBUG: Attempting to get OpenAI client...")
        client = get_openai_client()
        print(f"🔍 DEBUG: OpenAI client type: {type(client)}")
        
        # Check if this is the mock client by looking at the class name
        is_mock_client = "Mock" in str(type(client))
        print(f"🔍 DEBUG: Using {'mock' if is_mock_client else 'real'} OpenAI client")
        
        # If it's the mock client, we know it will work, so proceed
        # If it's the real client, add timeout and error handling
        if not is_mock_client:
            print("🔍 DEBUG: Making real OpenAI API call...")
            import time
            start_time = time.time()
        
        chat = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": message_text}
            ],
            temperature=0.1,  # Lower temperature for more consistent JSON output
            timeout=30  # Add timeout for production
        )
        
        if not is_mock_client:
            elapsed = time.time() - start_time
            print(f"🔍 DEBUG: OpenAI API call completed in {elapsed:.2f} seconds")
        
        content = chat.choices[0].message.content.strip()
        print(f"🔍 DEBUG: OpenAI response: {content}")

        # If GPT prepended text, extract just the JSON object
        # This regex grabs the first {...} block in the response
        m = re.search(r"(\{.*\})", content, re.DOTALL)
        if not m:
            print("🔍 DEBUG: No JSON found in OpenAI response, using manual extraction")
            raise ValueError("No JSON found in OpenAI response")
        
        json_str = m.group(1)
        print(f"🔍 DEBUG: Extracted JSON string: {json_str}")

        try:
            data = json.loads(json_str)
            print(f"🔍 DEBUG: Parsed JSON data: {data}")
        except Exception as e:
            print(f"🔍 DEBUG: JSON parsing failed: {e}")
            raise ValueError(f"Invalid JSON from GPT:\n{json_str}\nError: {e}")
    
    except Exception as e:
        print(f"🔍 DEBUG: OpenAI approach failed: {e}")
        print("🔍 DEBUG: Falling back to manual regex extraction")
        
        # Manual extraction as fallback - this should always work
        data = {}
        
        # Extract brand name - improved patterns for the exact format in the image
        brand_patterns = [
            r'(?:for|with|brand)\s+([A-Za-z0-9\s&]+?)(?:\s*\n|\s*flat|\s*deposit|$)',  # Stop at newline or next field
            r'agreement for\s+([A-Za-z0-9\s&]+?)(?:\s*\n|\s*flat|\s*deposit|$)',
            r'generate.*?for\s+([A-Za-z0-9\s&]+?)(?:\s*\n|\s*flat|\s*deposit|$)',
        ]
        data["brand_name"] = ""
        for pattern in brand_patterns:
            brand_match = re.search(pattern, message_text, re.IGNORECASE)
            if brand_match:
                data["brand_name"] = brand_match.group(1).strip()
                print(f"🔍 DEBUG: Manual extraction found brand: '{data['brand_name']}'")
                break
        
        if not data["brand_name"]:
            print("🔍 DEBUG: No brand found with standard patterns, trying fallback")
            # Fallback: look for any word after "for" that's not a common word
            fallback_match = re.search(r'for\s+([A-Za-z0-9]+)', message_text, re.IGNORECASE)
            if fallback_match:
                potential_brand = fallback_match.group(1).strip()
                if potential_brand.lower() not in ['the', 'a', 'an', 'this', 'that']:
                    data["brand_name"] = potential_brand
                    print(f"🔍 DEBUG: Manual extraction found brand via fallback: '{data['brand_name']}'")
        
        # Extract company name - handle both "Legal name:" and "company name is" formats
        company_patterns = [
            r'Legal name:\s*([^,\n]+)',  # "Legal name: XYZ"
            r'company name is\s+([^\n]+)',  # "company name is XYZ"
            r'company name:\s*([^\n]+)',  # "company name: XYZ"
        ]
        data["company_name"] = ""
        for pattern in company_patterns:
            company_match = re.search(pattern, message_text, re.IGNORECASE)
            if company_match:
                data["company_name"] = company_match.group(1).strip()
                print(f"🔍 DEBUG: Manual extraction found company: '{data['company_name']}'")
                break
        
        # Extract address - handle both "Address:" and "Address is" formats
        address_patterns = [
            r'Address is\s+([^\n]+?)(?:\s*industry|\s*company|\s*$)',  # "Address is XYZ" until next field
            r'Address:\s*([^.]+\.)',  # "Address: XYZ."
            r'Address:\s*([^,]+(?:,[^,]+)*)\s*(?:industry|company|deposit|field|$)',  # Until next field
        ]
        data["company_address"] = ""
        for pattern in address_patterns:
            address_match = re.search(pattern, message_text, re.IGNORECASE)
            if address_match:
                data["company_address"] = address_match.group(1).strip()
                print(f"🔍 DEBUG: Manual extraction found address: '{data['company_address']}'")
                break
        
        # Extract deposit - handle both "deposit 5000" and "Deposit: Rs 5000" formats
        deposit_patterns = [
            r'deposit\s+(\d+)',  # "deposit 5000"
            r'Deposit:\s*Rs\.?\s*([0-9,]+)',  # "Deposit: Rs 5000"
            r'Deposit\s+Rs\.?\s*([0-9,]+)',  # "Deposit Rs 5000"
        ]
        data["deposit"] = ""
        for pattern in deposit_patterns:
            deposit_match = re.search(pattern, message_text, re.IGNORECASE)
            if deposit_match:
                data["deposit"] = deposit_match.group(1).replace(',', '')
                print(f"🔍 DEBUG: Manual extraction found deposit: '{data['deposit']}'")
                break
        
        # Extract fee - handle both "flat fee 300" and "Flat Fee: Rs 300" formats
        fee_patterns = [
            r'flat fee\s+(\d+)',  # "flat fee 300"
            r'Flat\s+Fee[;\s:,]*Rs\.?\s*([0-9,]+)',  # "Flat Fee: Rs 320"
            r'(?:Flat\s+)?Fee[;\s:,]*Rs\.?\s*([0-9,]+)',  # "Fee: Rs 320"
            r'Commission[;\s:,]*Rs\.?\s*([0-9,]+)',  # "Commission: Rs 320"
            r'Rate[;\s:,]*Rs\.?\s*([0-9,]+)',  # "Rate: Rs 320"
        ]
        data["flat_fee"] = ""
        for i, pattern in enumerate(fee_patterns):
            fee_match = re.search(pattern, message_text, re.IGNORECASE)
            if fee_match:
                potential_fee = fee_match.group(1).replace(',', '')
                # Double-check this isn't the same as the deposit amount
                if potential_fee != data["deposit"]:
                    data["flat_fee"] = potential_fee
                    print(f"🔍 DEBUG: Manual extraction found fee with pattern {i+1}: {data['flat_fee']}")
                    break
                else:
                    print(f"🔍 DEBUG: Rejected fee candidate '{potential_fee}' - matches deposit amount")
        
        if not data["flat_fee"]:
            print("🔍 DEBUG: No explicit fee found in manual extraction - leaving empty")
        
        # Extract industry - handle both "Field:" and "industry" formats
        industry_patterns = [
            r'industry\s+([^\n]+)',  # "industry clothing and fashion"
            r'Field:\s*([^,\n]+)',  # "Field: clothing"
            r'Industry:\s*([^,\n]+)',  # "Industry: clothing"
        ]
        data["industry"] = ""
        for pattern in industry_patterns:
            industry_match = re.search(pattern, message_text, re.IGNORECASE)
            if industry_match:
                data["industry"] = industry_match.group(1).strip()
                print(f"🔍 DEBUG: Manual extraction found industry: '{data['industry']}'")
                break
        
        # Convert deposit to words
        data["deposit_in_words"] = ""
        if data.get("deposit"):
            try:
                deposit_num = int(data["deposit"])
                data["deposit_in_words"] = convert_number_to_words(str(deposit_num))
            except:
                pass
        
        print(f"🔍 DEBUG: Manual extraction completed: {data}")

    # Ensure all required fields exist
    for field in REQUIRED_FIELDS:
        if field not in data:
            data[field] = ""

    data["start_date"] = str(date.today())
    
    # Auto-convert deposit to words if we have deposit but not deposit_in_words
    if data.get("deposit") and not data.get("deposit_in_words"):
        data["deposit_in_words"] = convert_number_to_words(data["deposit"])
    
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    print(f"🔍 DEBUG: Final extracted data: {data}")
    print(f"🔍 DEBUG: Missing fields: {missing}")
    
    return data, missing


def fill_docx_template(values: dict, output_path: str):
    """
    Open the .docx template, replace placeholders like {{brand_name}},
    and save to output_path.
    """
    import html
    
    doc = Document(TEMPLATE_PATH)
    for p in doc.paragraphs:
        for key, val in values.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in p.text:
                # Decode HTML entities like &amp; to &
                decoded_val = html.unescape(str(val))
                p.text = p.text.replace(placeholder, decoded_val)
    doc.save(output_path)


def handle_agreement(event, say):
    """
    Full pull‑through: extract fields, prompt for missing,
    generate DOCX (+ PDF fallback), upload to Slack.
    """
    # prepare
    raw = event["text"]
    thread_ts = event.get("thread_ts") or event["ts"]
    channel   = event["channel"]

    # Send acknowledgement message first
    say("🤖 Got it - working on your agreement! ⚡", thread_ts=thread_ts)

    # clean and extract
    cleaned, _ = clean_text(raw), None
    values, missing = extract_agreement_fields(cleaned)

    if missing:
        say(f"🤖 I need a few more details: *{', '.join(missing)}*", thread_ts=thread_ts)
        return

    # post‑process formatting
    values["company_name"] = values["company_name"].upper()
    values["flat_fee"]    = format_currency(values["flat_fee"])
    values["deposit"]     = format_currency(values["deposit"])

    # safe filename
    brand_slug = re.sub(r"\W+", "_", values["brand_name"].lower())
    docx_path = f"{brand_slug}_agreement.docx"
    pdf_path  = f"{brand_slug}_agreement.pdf"

    # fill and save docx
    fill_docx_template(values, docx_path)

    # attempt PDF via Google Docs API
    pdf_ok = convert_docx_to_pdf(docx_path, pdf_path)

    # decide which to upload
    if pdf_ok:
        upload_path = pdf_path
        title = f"{values['brand_name']} Agreement (PDF)"
    else:
        upload_path = docx_path
        title = f"{values['brand_name']} Agreement (Word)"

    # upload to Slack thread
    with open(upload_path, "rb") as f:
        slack_client.files_upload_v2(
            channel=channel,
            thread_ts=thread_ts,
            file=f,
            filename=os.path.basename(upload_path),
            title=title,
            initial_comment=f"📎 Here’s your *{title}*"
        )
