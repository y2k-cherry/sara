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
            print(f"⚠️  OpenAI client initialization failed: {e}")
            # Try with minimal parameters
            try:
                openai_client = OpenAI(
                    api_key=OPENAI_API_KEY,
                    timeout=30.0
                )
            except Exception as e2:
                print(f"⚠️  OpenAI client fallback initialization failed: {e2}")
                raise e2
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
    sys_prompt = (
        "You are Sara, a sales ops AI assistant. Extract agreement details from this message "
        "and return ONLY raw JSON (no markdown, no code fences) with keys: "
        "brand_name, company_name, company_address, industry, flat_fee, deposit, deposit_in_words. "
        "If information is missing, use empty strings for missing fields. "
        "For brand_name, extract it from the message even if other details are missing. "
        "If you find a deposit amount in numbers, automatically convert it to words for deposit_in_words. "
        "For example: 10000 becomes 'ten thousand', 50000 becomes 'fifty thousand'. "
        "ALWAYS return valid JSON, never explanatory text."
    )

    try:
        client = get_openai_client()
        chat = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user",   "content": message_text}
            ],
            temperature=0.1  # Lower temperature for more consistent JSON output
        )
        content = chat.choices[0].message.content.strip()

        # If GPT prepended text, extract just the JSON object
        # This regex grabs the first {...} block in the response
        import re
        m = re.search(r"(\{.*\})", content, re.DOTALL)
        if not m:
            # Fallback: try to create a basic JSON with just the brand name
            brand_match = re.search(r'(?:for|with|brand)\s+([A-Za-z0-9\s]+)', message_text, re.IGNORECASE)
            if brand_match:
                brand_name = brand_match.group(1).strip()
                fallback_data = {
                    "brand_name": brand_name,
                    "company_name": "",
                    "company_address": "",
                    "industry": "",
                    "flat_fee": "",
                    "deposit": "",
                    "deposit_in_words": ""
                }
                return fallback_data, [f for f in REQUIRED_FIELDS if f != "brand_name"]
            else:
                raise ValueError(f"GPT did not return JSON. Full response:\n{content!r}")
        
        json_str = m.group(1)

        try:
            data = json.loads(json_str)
        except Exception as e:
            raise ValueError(f"Invalid JSON from GPT:\n{json_str}\nError: {e}")
    
    except Exception as e:
        # If OpenAI call fails completely, try to extract brand name manually
        brand_match = re.search(r'(?:for|with|brand)\s+([A-Za-z0-9\s]+)', message_text, re.IGNORECASE)
        if brand_match:
            brand_name = brand_match.group(1).strip()
            fallback_data = {
                "brand_name": brand_name,
                "company_name": "",
                "company_address": "",
                "industry": "",
                "flat_fee": "",
                "deposit": "",
                "deposit_in_words": ""
            }
            return fallback_data, [f for f in REQUIRED_FIELDS if f != "brand_name"]
        else:
            raise e

    data["start_date"] = str(date.today())
    
    # Auto-convert deposit to words if we have deposit but not deposit_in_words
    if data.get("deposit") and not data.get("deposit_in_words"):
        data["deposit_in_words"] = convert_number_to_words(data["deposit"])
    
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    return data, missing


def fill_docx_template(values: dict, output_path: str):
    """
    Open the .docx template, replace placeholders like {{brand_name}},
    and save to output_path.
    """
    doc = Document(TEMPLATE_PATH)
    for p in doc.paragraphs:
        for key, val in values.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in p.text:
                p.text = p.text.replace(placeholder, str(val))
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
