import os
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from datetime import datetime

SCOPES = ['https://www.googleapis.com/auth/drive']

def convert_docx_to_pdf_google(docx_path, pdf_path):
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    drive_service = build('drive', 'v3', credentials=creds)

    # Upload .docx as a Google Docs file
    file_metadata = {
        'name': f'Sara_Agreement_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
        'mimeType': 'application/vnd.google-apps.document'
    }

    media = MediaFileUpload(docx_path, mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
    uploaded_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = uploaded_file.get('id')

    # Export as PDF
    request = drive_service.files().export_media(fileId=file_id, mimeType='application/pdf')
    with open(pdf_path, 'wb') as f:
        f.write(request.execute())

    # Clean up: delete uploaded file from Drive
    drive_service.files().delete(fileId=file_id).execute()

    print("✅ PDF generated via Google Docs API.")
    return True
