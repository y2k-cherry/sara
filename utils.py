# utils.py

import re

def clean_slack_text(text: str) -> str:
    """Strip Slack’s user‑mention tokens like <@U12345> and trim whitespace."""
    return re.sub(r"<@[\w]+>", "", text).strip()

def format_currency(value: str) -> str:
    """Format a numeric string as Indian‑style ₹ currency."""
    try:
        num = float(value)
        return f"₹{num:,.0f}".replace(",", ",")
    except:
        return value

def generate_docx_filename(brand_name: str) -> str:
    """Turn a brand name into a safe filename, e.g. 'My Brand' → 'my_brand_agreement.docx'."""
    slug = re.sub(r"\W+", "_", brand_name.lower())
    return f"{slug}_agreement.docx"
