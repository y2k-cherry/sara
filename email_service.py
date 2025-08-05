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
    
    def extract_email_details(self, message_text: str) -> dict:
        """Extract email purpose and recipient(s) from the message using simple regex"""
        try:
            # Simple direct extraction - no AI needed
            
            # Extract the recipient email - look for "to" followed by email OR "email" followed by email
            recipient_match = re.search(r'(?:to|email)\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,})', message_text, re.IGNORECASE)
            recipient_email = recipient_match.group(1) if recipient_match else ""
            
            # Extract purpose - look for multiple patterns
            purpose = ""
            is_verbatim = False
            
            # Check for quoted content (verbatim) with "saying"
            quote_match = re.search(r"saying\s+['\"]([^'\"]+)['\"]", message_text, re.IGNORECASE)
            if quote_match:
                purpose = quote_match.group(1)
                is_verbatim = True
            else:
                # Check for "saying" without quotes
                saying_match = re.search(r"saying\s+(.+?)(?:\s*$)", message_text, re.IGNORECASE)
                if saying_match:
                    purpose = saying_match.group(1).strip()
                else:
                    # Check for "about" pattern
                    about_match = re.search(r"about\s+(.+?)(?:\s*$)", message_text, re.IGNORECASE)
                    if about_match:
                        purpose = about_match.group(1).strip()
                    else:
                        # Check for "regarding" pattern
                        regarding_match = re.search(r"regarding\s+(.+?)(?:\s*$)", message_text, re.IGNORECASE)
                        if regarding_match:
                            purpose = regarding_match.group(1).strip()
                        else:
                            # If we have an email but no clear purpose, use a default
                            if recipient_email:
                                purpose = "Hello"
            
            # Extract custom subject
            subject_match = re.search(r"subject\s+is\s+['\"]([^'\"]+)['\"]", message_text, re.IGNORECASE)
            custom_subject = subject_match.group(1) if subject_match else ""
            
            result = {
                "purpose": purpose,
                "recipient_emails": [recipient_email] if recipient_email else [],
                "recipient_names": [],
                "custom_subject": custom_subject,
                "is_verbatim": is_verbatim,
                "additional_context": ""
            }
            
            return result
                
        except Exception as e:
            print(f"Error extracting email details: {e}")
            return {"purpose": "", "recipient_emails": [], "recipient_names": [], "additional_context": ""}
    
    def compose_email(self, purpose: str, recipient_name: str, additional_context: str = "", is_verbatim: bool = False, custom_subject: str = "") -> dict:
        """Compose a professional email based on the purpose"""
        try:
            # Simple email composition without AI
            subject = custom_subject if custom_subject else "Message from Yash Kewalramani"
            
            if is_verbatim:
                # Use verbatim content
                body = f"Hi {recipient_name},\n\n{purpose}\n\nBest regards,\nYash Kewalramani"
            else:
                # Simple professional template
                body = f"Hi {recipient_name},\n\n{purpose}\n\nBest regards,\nYash Kewalramani"
            
            return {"subject": subject, "body": body}
                
        except Exception as e:
            print(f"Error composing email: {e}")
            subject = custom_subject if custom_subject else "Message from Yash Kewalramani"
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
