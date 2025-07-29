import os
import re
import json
from datetime import date
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError
from slack_sdk.web import WebClient
from docx import Document
import pypandoc
from openai import OpenAI
from google_pdf import convert_docx_to_pdf_google as convert_docx_to_pdf


# Load environment variables
load_dotenv()
SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Initialize clients
app = App(token=SLACK_BOT_TOKEN)
client = WebClient(token=SLACK_BOT_TOKEN)
openai = OpenAI(api_key=OPENAI_API_KEY)
bot_user_id = app.client.auth_test().get("user_id")


REQUIRED_FIELDS = [
    "brand_name", "company_name", "company_address",
    "industry", "flat_fee", "deposit", "deposit_in_words"
]
thread_memory = {}

# ---------- UTILS ----------

def clean_slack_text(text):
    return re.sub(r"<@[\w]+>", "", text).strip()

def format_currency(value):
    try:
        return "₹{:,.0f}".format(float(value)).replace(",", ",")
    except:
        return value


def fill_docx_template(template_path, output_path, values):
    doc = Document(template_path)
    for p in doc.paragraphs:
        for key, val in values.items():
            p.text = p.text.replace(f"{{{{{key}}}}}", str(val))
    doc.save(output_path)

def extract_agreement_fields(message_text):
    system_prompt = (
        "You are Sara, a sales ops AI assistant. Extract agreement details from user message and return only raw JSON "
        "with keys: brand_name, company_name, company_address, industry, flat_fee, deposit, deposit_in_words. "
        "Omit explanations or formatting. Assume today's date as start_date."
    )

    chat = openai.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message_text}
        ]
    )

    content = chat.choices[0].message.content
    try:
        json_str = content.strip().split("```json")[-1].split("```")[0] if "```json" in content else content
        values = json.loads(json_str)
        values["start_date"] = str(date.today())
        missing = [field for field in REQUIRED_FIELDS if field not in values or not values[field]]
        return values, missing
    except json.JSONDecodeError as e:
        print("❌ GPT returned invalid JSON:\n", content)
        raise e

def generate_agreement(values):
    values["company_name"] = values["company_name"].upper()
    values["flat_fee"] = format_currency(values["flat_fee"])
    values["deposit"] = format_currency(values["deposit"])
    values["start_date"] = str(date.today())

    brand = values["brand_name"]
    safe_brand = re.sub(r'\W+', '_', brand.lower())
    docx_path = f"{safe_brand}_agreement.docx"
    pdf_path = f"{safe_brand}_agreement.pdf"

    fill_docx_template("Partnership Agreement Template.docx", docx_path, values)
    if convert_docx_to_pdf(docx_path, pdf_path):
        return pdf_path, f"{brand.title()} Agreement (PDF)"
    else:
        return docx_path, f"{brand.title()} Agreement (.docx fallback)"

def upload_file_to_slack(path, title, channel, thread_ts):
    with open(path, "rb") as f:
        client.files_upload_v2(
            channel=channel,
            thread_ts=thread_ts,
            file=f,
            title=title,
            filename=os.path.basename(path),
            initial_comment=f"📎 Here's your file: *{title}*"
        )

# ---------- MAIN FLOW ----------

def process_agreement_request(message_text, event, say):
    message_text = clean_slack_text(message_text)
    thread_ts = event.get("thread_ts") or event["ts"]
    channel = event["channel"]

    key = f"{channel}_{thread_ts}"
    prev = thread_memory.get(key, {})
    try:
        values, missing = extract_agreement_fields(message_text)
        prev.update(values)
        still_missing = [f for f in REQUIRED_FIELDS if not prev.get(f)]
        thread_memory[key] = prev

        if still_missing:
            say(f"🤖 I need a few more details to finish the agreement: *{', '.join(still_missing)}*", thread_ts=thread_ts)
            return

        filepath, title = generate_agreement(prev)
        upload_file_to_slack(filepath, title, channel, thread_ts)
        say(f"✅ Agreement for *{prev['brand_name']}* is ready!", thread_ts=thread_ts)
        del thread_memory[key]

    except Exception as e:
        say(f":x: Error creating agreement: {str(e)}", thread_ts=thread_ts)

# ---------- SLACK EVENTS ----------

@app.event("app_mention")
def handle_mention(event, say):
    say("👀 Got your request! Processing...", thread_ts=event["ts"])
    process_agreement_request(event["text"], event, say)

@app.event("message")
def handle_thread_reply(event, say, client):
    # Ignore messages from bots (including Sara)
    if event.get("bot_id"):
        return

    # Only care about thread replies
    thread_ts = event.get("thread_ts")
    if not thread_ts:
        return

    channel = event["channel"]
    try:
        # Fetch the first message in that thread
        result = client.conversations_replies(channel=channel, ts=thread_ts, limit=1)
        parent = result["messages"][0].get("text", "")

        # If the parent text mentioned your bot ID, merge the reply
        if f"<@{bot_user_id}>" in parent:
            say("🔄 Got it! Let me update that…", thread_ts=thread_ts)
            combined = parent + "\n" + event["text"]
            process_agreement_request(combined, event, say)
    except SlackApiError as e:
        print("Failed to fetch thread parent:", e)
        print("Slack thread fetch error:", e)

# ---------- START BOT ----------

if __name__ == "__main__":
    print("⚡ Sara is running via Socket Mode...")
    SocketModeHandler(app, SLACK_APP_TOKEN).start()
