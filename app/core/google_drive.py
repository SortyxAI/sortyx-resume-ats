import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from app.core.config import settings

def upload_to_drive(file_path, custom_filename):
    # Load your personal 2TB token
    creds = Credentials.from_authorized_user_file('token.json', ['https://www.googleapis.com/auth/drive.file'])
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': custom_filename, # 🚀 This is where the magic happens
        'parents': [settings.GOOGLE_DRIVE_FOLDER_ID]
    }

    media = MediaFileUpload(file_path, resumable=True)

    try:
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        return file.get('id')
    except Exception as e:
        print(f"❌ Drive Error: {e}")
        return None