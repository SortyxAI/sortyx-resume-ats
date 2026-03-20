import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings

# 1. Setup Scopes and Credentials
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'

def upload_to_drive(file_path, filename):
    """
    Uploads a file to a SPECIFIC Google Drive folder.
    """
    # Create Credentials
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    
    # Build Service
    service = build('drive', 'v3', credentials=creds)

    # 🚨 CRITICAL: The metadata MUST include the Parent Folder ID
    file_metadata = {
        'name': filename,
        'parents': [settings.GOOGLE_DRIVE_FOLDER_ID] 
    }

    # 🚨 CRITICAL: The media must point to the actual file on your E: drive
    media = MediaFileUpload(file_path, resumable=True)

    try:
        # 🚀 THE EXECUTION: We MUST pass 'body=file_metadata'
        file = service.files().create(
            body=file_metadata,    # This tells it WHERE to go
            media_body=media,      # This is WHAT to upload
            fields='id, parents'   # This asks for the ID and Parent back for verification
        ).execute()

        print(f"✅ File ID: {file.get('id')} | Uploaded to Parent: {file.get('parents')}")
        return file.get('id')

    except Exception as e:
        print(f"❌ Google API Error during create: {e}")
        raise e