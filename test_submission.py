"""
Full end-to-end diagnostic: tests Drive upload + Sheets append exactly
as the /apply endpoint does, so we can see the exact error.
"""
import os, json, tempfile
from dotenv import load_dotenv
load_dotenv()

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")
FOLDER_ID      = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

print("="*60)
print("ENV CHECK")
print(f"  SPREADSHEET_ID     : {SPREADSHEET_ID}")
print(f"  DRIVE_FOLDER_ID    : {FOLDER_ID}")

# ── Load & refresh credentials ──────────────────────────────────
print("\nCREDENTIALS CHECK")
creds = Credentials.from_authorized_user_file("token.json", SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    print("  Token refreshed")
print(f"  Valid   : {creds.valid}")
print(f"  Expired : {creds.expired}")
print(f"  Scopes  : {list(creds.scopes)}")

# ── Drive folder check ───────────────────────────────────────────
print("\nDRIVE FOLDER CHECK")
drive = build("drive", "v3", credentials=creds)
try:
    folder = drive.files().get(fileId=FOLDER_ID, fields="id,name,mimeType").execute()
    print(f"  [OK] Folder found: '{folder.get('name')}' ({folder.get('mimeType')})")
except Exception as e:
    print(f"  [ERR] Cannot access folder: {e}")

# ── Drive upload test ────────────────────────────────────────────
print("\nDRIVE UPLOAD TEST")
try:
    # Create a tiny dummy PDF-like file
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    tmp.write(b"%PDF-1.4 test resume content")
    tmp.close()

    metadata = {"name": "TEST_Resume.pdf", "parents": [FOLDER_ID]}
    media    = MediaFileUpload(tmp.name, mimetype="application/pdf", resumable=True)
    result   = drive.files().create(body=metadata, media_body=media, fields="id,webViewLink").execute()
    file_id  = result.get("id")
    link     = result.get("webViewLink", f"https://drive.google.com/file/d/{file_id}/view")
    print(f"  [OK] Uploaded! File ID: {file_id}")
    print(f"       Link: {link}")

    # Clean up test file from Drive
    drive.files().delete(fileId=file_id).execute()
    print("  [OK] Test file deleted from Drive")
    os.unlink(tmp.name)

except Exception as e:
    print(f"  [ERR] Upload failed: {e}")

# ── Sheets check ─────────────────────────────────────────────────
print("\nSHEETS CHECK")
sheets = build("sheets", "v4", credentials=creds)
try:
    r = sheets.spreadsheets().values().get(
        spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:A"
    ).execute()
    rows = r.get("values", [])
    print(f"  [OK] Sheet readable. Rows (incl. header): {len(rows)}")
except Exception as e:
    print(f"  [ERR] Sheets read failed: {e}")

# ── Sheets append test ───────────────────────────────────────────
print("\nSHEETS APPEND TEST")
try:
    test_row = [["TEST", "Diagnostic Test", "9999999999", "test@test.com",
                 "Test College", "CS", "1st Year", "Chennai",
                 "Python Development", "Yes", "https://test.com", "auto-test"]]
    sheets.spreadsheets().values().append(
        spreadsheetId=SPREADSHEET_ID,
        range="Sheet1!A:L",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": test_row},
    ).execute()
    print("  [OK] Test row appended to Sheet successfully!")
    print("  NOTE: Please manually delete the TEST row from your sheet.")
except Exception as e:
    print(f"  [ERR] Sheets append failed: {e}")

print("\n" + "="*60)
print("DONE")
