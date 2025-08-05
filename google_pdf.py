import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive']

def convert_docx_to_pdf_google(docx_path, pdf_path):
    """
    Convert DOCX to PDF using Google Drive API.
    Returns True if successful, False if it fails (so DOCX can be used as fallback).
    """
    try:
        # Try to get credentials from environment variables first
        google_creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
        google_token_json = os.getenv('GOOGLE_TOKEN_JSON')
        
        creds = None
        
        if google_token_json:
            # Use token from environment variable
            print("🔍 DEBUG: Using Google token from environment variable")
            import json
            token_data = json.loads(google_token_json)
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        elif google_creds_json:
            # Use credentials from environment variable
            print("🔍 DEBUG: Using Google credentials from environment variable")
            import json
            creds_data = json.loads(google_creds_json)
            from google_auth_oauthlib.flow import InstalledAppFlow
            flow = InstalledAppFlow.from_client_config(creds_data, SCOPES)
            # This won't work in production without a browser, so we'll skip it
            print("⚠️  Cannot run OAuth flow in production environment")
            return False
        elif os.path.exists('token.json'):
            # Use local token file
            print("🔍 DEBUG: Using local token.json file")
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
        elif os.path.exists('credentials.json'):
            # Use local credentials file
            print("🔍 DEBUG: Using local credentials.json file")
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        else:
            print("⚠️  No Google credentials found - PDF conversion disabled")
            print("⚠️  Set GOOGLE_TOKEN_JSON environment variable for PDF support")
            print("⚠️  Will upload DOCX file instead")
            return False

        # Check if credentials are valid
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                print("🔍 DEBUG: Refreshing expired Google credentials")
                creds.refresh(Request())
            else:
                print("⚠️  Google credentials are invalid - PDF conversion disabled")
                return False

        print("🔍 DEBUG: Building Google Drive service")
        drive_service = build('drive', 'v3', credentials=creds)

        # Upload .docx as a Google Docs file
        file_metadata = {
            'name': f'Sara_Agreement_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            'mimeType': 'application/vnd.google-apps.document'
        }

        print("🔍 DEBUG: Uploading DOCX to Google Drive")
        media = MediaFileUpload(docx_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = uploaded_file.get('id')
        print(f"🔍 DEBUG: File uploaded with ID: {file_id}")

        # Export as PDF
        print("🔍 DEBUG: Exporting as PDF")
        request = drive_service.files().export_media(fileId=file_id, mimeType='application/pdf')
        with open(pdf_path, 'wb') as f:
            f.write(request.execute())

        # Clean up: delete uploaded file from Drive
        print("🔍 DEBUG: Cleaning up temporary file from Drive")
        drive_service.files().delete(fileId=file_id).execute()

        print("✅ PDF generated via Google Docs API.")
        return True
        
    except Exception as e:
        print(f"⚠️  PDF conversion failed: {e}")
        print("⚠️  Will upload DOCX file instead")
        return False
