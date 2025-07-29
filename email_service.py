#!/usr/bin/env python3
"""
Email service for Sara - handles email composition, review, and sending
"""

import os
import smtplib
import re
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import openai

load_dotenv()

class EmailService:
    """Service for handling email composition and sending"""
    
    def __init__(self):
        self.openai_client = None
        self.sender_email = "partnerships@cherryapp.in"
        self.sender_name = "Yash Kewalramani"
        
        # Email credentials - will need to be added to .env
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_password = os.getenv('EMAIL_PASSWORD')
        
        if not self.email_password:
            print("⚠️  EMAIL_PASSWORD not found in environment variables")
    
    def _get_openai_client(self):
        """Get OpenAI client with lazy initialization"""
        if self.openai_client is None:
            try:
                self.openai_client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            except Exception as e:
                print(f"⚠️  OpenAI client initialization failed in email_service: {e}")
                # Create a mock client that tries to parse the message manually
                print("⚠️  Using mock OpenAI client for email service")
                def mock_create(*args, **kwargs):
                    # Try to extract basic info from the message
                    messages = kwargs.get('messages', [])
                    user_message = ""
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            user_message = msg.get('content', '')
                            break
                    
                    # Manual extraction for email details
                    import re
                    
                    # Extract email addresses
                    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
                    emails = re.findall(email_pattern, user_message)
                    
                    # Extract purpose - look for "saying", "about", quoted content
                    purpose = ""
                    is_verbatim = False
                    custom_subject = ""
                    
                    # Check for quoted content (verbatim)
                    quote_match = re.search(r"saying\s+['\"]([^'\"]+)['\"]", user_message, re.IGNORECASE)
                    if quote_match:
                        purpose = quote_match.group(1)
                        is_verbatim = True
                    else:
                        # Check for "about" pattern
                        about_match = re.search(r"about\s+(.+?)(?:\s+and\s+subject|$)", user_message, re.IGNORECASE)
                        if about_match:
                            purpose = about_match.group(1).strip()
                        else:
                            # Check for "saying" without quotes
                            saying_match = re.search(r"saying\s+(.+?)(?:\s+and\s+subject|$)", user_message, re.IGNORECASE)
                            if saying_match:
                                purpose = saying_match.group(1).strip()
                    
                    # Extract custom subject
                    subject_match = re.search(r"subject\s+is\s+['\"]([^'\"]+)['\"]", user_message, re.IGNORECASE)
                    if subject_match:
                        custom_subject = subject_match.group(1)
                    
                    # If this is a composition request, return email content
                    if "compose" in user_message.lower() or "subject line" in user_message.lower():
                        # This is an email composition request
                        subject = custom_subject if custom_subject else "Message from Yash Kewalramani"
                        body = f"Hi,\n\n{purpose}\n\nBest regards,\nYash Kewalramani"
                        return type('Response', (), {
                            'choices': [type('Choice', (), {
                                'message': type('Message', (), {
                                    'content': json.dumps({"subject": subject, "body": body})
                                })()
                            })()]
                        })()
                    else:
                        # This is an extraction request
                        result = {
                            "purpose": purpose,
                            "recipient_emails": emails,
                            "recipient_names": [],
                            "custom_subject": custom_subject,
                            "is_verbatim": is_verbatim,
                            "additional_context": ""
                        }
                        return type('Response', (), {
                            'choices': [type('Choice', (), {
                                'message': type('Message', (), {
                                    'content': json.dumps(result)
                                })()
                            })()]
                        })()
                
                self.openai_client = type('MockClient', (), {
                    'chat': type('Chat', (), {
                        'completions': type('Completions', (), {
                            'create': mock_create
                        })()
                    })()
                })()
        return self.openai_client
    
    def extract_email_details(self, message_text: str) -> dict:
        """Extract email purpose and recipient(s) from the message"""
        try:
            prompt = f"""
Extract email details from this Slack message. The user wants to send an email.

Message: "{message_text}"

IMPORTANT RULES:
1. If text is in quotes (single or double), extract it EXACTLY as written - this is verbatim content
2. Look for explicit subject specification like "subject is 'xyz'" or "subject: 'xyz'"
3. Text in quotes should NOT be processed or modified - use exactly as provided

Extract and return ONLY a JSON object with these keys:
- purpose: The purpose/content of the email. If in quotes, use EXACTLY as written. Look for "saying", "about", "regarding", "to tell them", or quoted content.
- recipient_emails: Array of email addresses (even if just one recipient, return as array)
- recipient_names: Array of recipient names (if mentioned, otherwise use emails)
- custom_subject: If user specifies subject explicitly (like "subject is 'xyz'"), extract the EXACT quoted text. Otherwise empty string.
- is_verbatim: true if the purpose content is in quotes (should be used exactly as written), false if it should be processed by AI
- additional_context: Any additional context or details mentioned

Examples:
- "send email to john@test.com saying 'Hello there'" → purpose: "Hello there", is_verbatim: true
- "email sara@company.com saying exactly 'Yo sup this is via Sara', subject is 'MCP Zindabad'" → purpose: "Yo sup this is via Sara", custom_subject: "MCP Zindabad", is_verbatim: true
- "send email to client@business.com about the meeting" → purpose: "the meeting", is_verbatim: false

If you can't find recipient emails, set to empty array.
If you can't determine the purpose, set it to empty string.

Return ONLY the JSON, no other text.
"""
            
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                # Ensure backward compatibility - convert single values to arrays if needed
                if "recipient_emails" not in result and "recipient_email" in result:
                    result["recipient_emails"] = [result["recipient_email"]] if result["recipient_email"] else []
                if "recipient_names" not in result and "recipient_name" in result:
                    result["recipient_names"] = [result["recipient_name"]] if result["recipient_name"] else []
                return result
            else:
                return {"purpose": "", "recipient_emails": [], "recipient_names": [], "additional_context": ""}
                
        except Exception as e:
            print(f"Error extracting email details: {e}")
            return {"purpose": "", "recipient_emails": [], "recipient_names": [], "additional_context": ""}
    
    def compose_email(self, purpose: str, recipient_name: str, additional_context: str = "", is_verbatim: bool = False, custom_subject: str = "") -> dict:
        """Compose a professional email based on the purpose"""
        try:
            if is_verbatim:
                # Use verbatim content - don't process through AI
                subject = custom_subject if custom_subject else "Message from Yash Kewalramani"
                body = f"Hi {recipient_name},\n\n{purpose}\n\nBest regards,\nYash Kewalramani"
                return {"subject": subject, "body": body}
            
            # Regular AI-composed email
            subject_instruction = f"Use this exact subject: '{custom_subject}'" if custom_subject else "Generate an appropriate subject line"
            
            prompt = f"""
You are Sara, an AI assistant helping Yash Kewalramani (yash@cherryapp.in) compose a professional email.

Email Details:
- Purpose: {purpose}
- Recipient: {recipient_name}
- Additional Context: {additional_context}
- Sender: Yash Kewalramani
- Subject Instruction: {subject_instruction}

Compose a concise, professional email with:
1. Subject line: {subject_instruction}
2. A well-structured body that is brief but complete
3. Professional tone suitable for business communication

Return ONLY a JSON object with:
- subject: The email subject line
- body: The email body (use \\n for line breaks)

Keep it concise - aim for 3-4 sentences maximum unless more detail is specifically needed.
"""
            
            client = self._get_openai_client()
            response = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3
            )
            
            content = response.choices[0].message.content.strip()
            
            # Extract JSON from response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                result = json.loads(json_match.group(0))
                # Override subject if custom subject is provided
                if custom_subject:
                    result["subject"] = custom_subject
                return result
            else:
                subject = custom_subject if custom_subject else purpose
                return {"subject": subject, "body": f"Hi {recipient_name},\n\nI hope this email finds you well.\n\nBest regards,\nYash Kewalramani"}
                
        except Exception as e:
            print(f"Error composing email: {e}")
            subject = custom_subject if custom_subject else purpose
            return {"subject": subject, "body": f"Hi {recipient_name},\n\nI hope this email finds you well.\n\nBest regards,\nYash Kewalramani"}
    
    def send_email(self, recipient_emails, subject: str, body: str) -> bool:
        """Send the email via SMTP to single or multiple recipients"""
        if not self.email_password:
            print("❌ Email password not configured")
            return False
        
        # Handle both single string and list of emails
        if isinstance(recipient_emails, str):
            recipient_emails = [recipient_emails]
        elif not isinstance(recipient_emails, list):
            print(f"❌ Invalid recipient format: {type(recipient_emails)}")
            return False
            
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = f"{self.sender_name} <{self.sender_email}>"
            msg['To'] = ', '.join(recipient_emails)  # Join multiple recipients with comma
            msg['Cc'] = self.sender_email  # CC yourself
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.sender_email, self.email_password)
            
            # Send to all recipients plus CC
            all_recipients = recipient_emails + [self.sender_email]
            text = msg.as_string()
            server.sendmail(self.sender_email, all_recipients, text)
            server.quit()
            
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
    
    def format_email_preview(self, recipient_emails, subject: str, body: str) -> str:
        """Format email for preview in Slack"""
        # Handle both single string and list of emails
        if isinstance(recipient_emails, str):
            recipient_display = recipient_emails
        elif isinstance(recipient_emails, list):
            recipient_display = ', '.join(recipient_emails)
        else:
            recipient_display = str(recipient_emails)
            
        preview = f"""📧 **Email Preview**

**To:** {recipient_display}
**CC:** {self.sender_email}
**Subject:** {subject}

**Body:**
{body}

**From:** {self.sender_name} <{self.sender_email}>

---
Reply with "✅ send" to send this email, or "❌ cancel" to cancel.
"""
        return preview

# Global variable to store pending emails (in production, use a database)
pending_emails = {}

def handle_email_request(event, say):
    """Handle email requests from Slack"""
    try:
        email_service = EmailService()
        message_text = event["text"]
        thread_ts = event.get("thread_ts") or event["ts"]
        user_id = event["user"]
        
        # Extract email details
        details = email_service.extract_email_details(message_text)
        
        # Check if we have required information
        if not details.get("purpose"):
            say("❌ I couldn't determine the purpose of the email. Please specify what the email should be about.", thread_ts=thread_ts)
            return
        
        # Check for recipients (support both old and new format)
        recipient_emails = details.get("recipient_emails", [])
        if not recipient_emails and details.get("recipient_email"):
            recipient_emails = [details["recipient_email"]]
            
        if not recipient_emails:
            say("❌ I couldn't find the recipient's email address. Please provide the email address of who you want to send this to.", thread_ts=thread_ts)
            return
        
        # Get recipient names (support both old and new format)
        recipient_names = details.get("recipient_names", [])
        if not recipient_names and details.get("recipient_name"):
            recipient_names = [details["recipient_name"]]
        if not recipient_names:
            recipient_names = recipient_emails  # Use emails as names if no names provided
        
        # Create display name for email composition
        if len(recipient_names) == 1:
            recipient_display = recipient_names[0]
        elif len(recipient_names) == 2:
            recipient_display = f"{recipient_names[0]} and {recipient_names[1]}"
        else:
            recipient_display = f"{', '.join(recipient_names[:-1])}, and {recipient_names[-1]}"
        
        # Handle case where recipient_names might be empty or contain emails
        if not recipient_display or '@' in recipient_display:
            # Extract names from emails if no proper names provided
            name_parts = []
            for email in recipient_emails:
                name_part = email.split('@')[0].replace('.', ' ').replace('_', ' ').title()
                name_parts.append(name_part)
            
            if len(name_parts) == 1:
                recipient_display = name_parts[0]
            elif len(name_parts) == 2:
                recipient_display = f"{name_parts[0]} and {name_parts[1]}"
            else:
                recipient_display = f"{', '.join(name_parts[:-1])}, and {name_parts[-1]}"
        
        # Compose the email
        email_content = email_service.compose_email(
            details["purpose"], 
            recipient_display,
            details.get("additional_context", ""),
            details.get("is_verbatim", False),
            details.get("custom_subject", "")
        )
        
        # Store email details for confirmation
        email_key = f"{user_id}_{thread_ts}"
        pending_emails[email_key] = {
            "recipient_emails": recipient_emails,
            "subject": email_content["subject"],
            "body": email_content["body"],
            "thread_ts": thread_ts
        }
        
        # Show preview
        preview = email_service.format_email_preview(
            recipient_emails,
            email_content["subject"],
            email_content["body"]
        )
        
        say(preview, thread_ts=thread_ts)
        
    except Exception as e:
        say(f"❌ Error processing email request: {str(e)}", thread_ts=thread_ts)

def handle_email_confirmation(event, say):
    """Handle email confirmation (send/cancel)"""
    try:
        message_text = event["text"].lower().strip()
        thread_ts = event.get("thread_ts")
        user_id = event["user"]
        
        if not thread_ts:
            return False  # Not a thread reply
        
        email_key = f"{user_id}_{thread_ts}"
        
        if email_key not in pending_emails:
            return False  # No pending email for this thread
        
        email_data = pending_emails[email_key]
        
        # Check for send confirmation - be more flexible
        is_send_command = (
            ("✅" in message_text and "send" in message_text) or
            (message_text == "send") or
            (message_text == "✅ send") or
            ("send it" in message_text) or
            ("yes" in message_text and "send" in message_text)
        )
        
        # Check for cancel confirmation
        is_cancel_command = (
            ("❌" in message_text and "cancel" in message_text) or
            (message_text == "cancel") or
            (message_text == "❌ cancel") or
            ("cancel it" in message_text) or
            ("no" in message_text and ("cancel" in message_text or "don't send" in message_text))
        )
        
        if is_send_command:
            # Send the email
            email_service = EmailService()
            
            # Support both old and new format
            recipient_emails = email_data.get("recipient_emails", [])
            if not recipient_emails and email_data.get("recipient_email"):
                recipient_emails = [email_data["recipient_email"]]
            
            success = email_service.send_email(
                recipient_emails,
                email_data["subject"],
                email_data["body"]
            )
            
            if success:
                if isinstance(recipient_emails, list):
                    recipient_display = ', '.join(recipient_emails)
                else:
                    recipient_display = str(recipient_emails)
                say(f"✅ Email sent successfully to {recipient_display}!", thread_ts=thread_ts)
            else:
                say("❌ Failed to send email. Please check email configuration.", thread_ts=thread_ts)
            
            # Remove from pending emails
            del pending_emails[email_key]
            return True
            
        elif is_cancel_command:
            # Cancel the email
            say("❌ Email cancelled.", thread_ts=thread_ts)
            del pending_emails[email_key]
            return True
        
        return False
        
    except Exception as e:
        say(f"❌ Error handling email confirmation: {str(e)}", thread_ts=thread_ts)
        return False
