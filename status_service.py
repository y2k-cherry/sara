# status_service.py
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os

SCOPES = [
    "https://www.googleapis.com/auth/documents.readonly",
    "https://www.googleapis.com/auth/drive.metadata.readonly"
]

SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")


def read_google_doc_text(doc_title="Sara Test Doc"):
    """
    Looks up a doc by title and returns its plain text content.
    """

    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    drive = build("drive", "v3", credentials=creds)
    
    # Step 1: Find document ID by name
    results = drive.files().list(q=f"name='{doc_title}' and mimeType='application/vnd.google-apps.document'",
                                 spaces='drive',
                                 fields="files(id, name)").execute()
    items = results.get("files", [])
    
    if not items:
        return "❌ Could not find the document 'Sara Test Doc'."
    
    doc_id = items[0]["id"]

    # Step 2: Read content from Google Docs
    docs = build("docs", "v1", credentials=creds)
    document = docs.documents().get(documentId=doc_id).execute()

    text = ""
    for element in document.get("body", {}).get("content", []):
        if "paragraph" in element:
            for run in element["paragraph"].get("elements", []):
                if "textRun" in run:
                    text += run["textRun"].get("content", "")

    return text.strip()


