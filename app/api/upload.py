import os
import sys
import uuid
import shutil

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from app.core.config import settings

router = APIRouter()

# ---------------------------------------------------------------------------
# Google API Scopes  (Drive + Sheets aggregated in one token)
# ---------------------------------------------------------------------------
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# Runtime config â€” set SPREADSHEET_ID in your .env file
SPREADSHEET_ID: str | None = os.getenv("SPREADSHEET_ID")

# Target sheet range (columns Aâ€“L):
# A: S.No | B: Full Name | C: Mobile Number | D: Email | E: College
# F: Department | G: Year of Study | H: City | I: Internship Domain
# J: Fee Payment | K: Resume Link | L: Notes
SHEET_RANGE = "Sheet1!A:L"


# ---------------------------------------------------------------------------
# Helper: build authenticated Google service clients
# ---------------------------------------------------------------------------
def _get_credentials() -> Credentials:
    """Load OAuth2 credentials from token.json with the combined scope set."""
    return Credentials.from_authorized_user_file("token.json", SCOPES)


def _drive_service():
    return build("drive", "v3", credentials=_get_credentials())


def _sheets_service():
    return build("sheets", "v4", credentials=_get_credentials())


def _next_row_number(sheets_svc) -> int:
    """Return the next sequential S.No by counting existing data rows."""
    try:
        result = (
            sheets_svc.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:A")
            .execute()
        )
        rows = result.get("values", [])
        # rows[0] is the header row, so data rows = len(rows) - 1
        return max(len(rows), 1)  # at least 1 if sheet is empty / no header yet
    except Exception:
        return 1


# ---------------------------------------------------------------------------
# POST /apply  â€” candidate submission endpoint
# ---------------------------------------------------------------------------
@router.post("/apply")
async def apply(
    # Name fields â€” backend accepts both combined and split variants
    name: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),

    # Contact
    email: str = Form(...),
    phone: str = Form(...),
    city: str = Form(...),

    # Academic
    college: str = Form(...),
    department: str = Form(...),
    year_of_study: str = Form(...),          # "1st Year" / "2nd Year" / "3rd Year" / "4th Year" / "Passed Out"
    passed_out_year: str = Form(None),       # Only populated when year_of_study == "Passed Out"

    # Internship
    internship_domain: str = Form(...),
    fee_payment: str = Form(...),            # "Yes" or "No"

    # Files & extras
    file: UploadFile = File(...),
    notes: str = Form(None),
):
    # ------------------------------------------------------------------
    # 0. Resolve full name
    # ------------------------------------------------------------------
    if not name and (first_name or last_name):
        name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    if not name:
        name = "Unknown Candidate"

    # ------------------------------------------------------------------
    # 1. Build the Year of Study display value
    #    â€” If "Passed Out", append the year they provided
    # ------------------------------------------------------------------
    if year_of_study == "Passed Out" and passed_out_year and passed_out_year.strip() not in ("", "N/A"):
        year_display = f"Passed Out ({passed_out_year.strip()})"
    elif year_of_study == "Passed Out":
        year_display = "Passed Out"
    else:
        year_display = year_of_study

    # ------------------------------------------------------------------
    # 2. Validate file extension
    # ------------------------------------------------------------------
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in [".pdf", ".docx"]:
        raise HTTPException(status_code=400, detail="Only PDF or DOCX files are accepted.")

    # ------------------------------------------------------------------
    # 3. Save file locally with a unique name
    # ------------------------------------------------------------------
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    unique_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, unique_name))

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as save_err:
        print(f"âŒ File Save Error: {save_err}", file=sys.stderr)
        raise HTTPException(status_code=500, detail="Could not save file locally.")

    # ------------------------------------------------------------------
    # 4. Google Drive upload â†’ Sheets append pipeline
    # ------------------------------------------------------------------
    try:
        # â”€â”€ 4a. Upload to Google Drive â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        drive_filename = f"{name.replace(' ', '_')}_Resume{file_ext}"
        drive = _drive_service()

        file_metadata = {
            "name": drive_filename,
            "parents": [settings.GOOGLE_DRIVE_FOLDER_ID],
        }

        # Reset stream cursor before upload (critical for UploadFile)
        await file.seek(0)

        media = MediaFileUpload(file_path, resumable=True)

        uploaded_file = (
            drive.files()
            .create(body=file_metadata, media_body=media, fields="id, webViewLink")
            .execute()
        )

        # Close the MediaFileUpload file handle so Windows releases the lock
        try:
            media._fd.close()
        except Exception:
            pass

        drive_id: str = uploaded_file.get("id", "")
        drive_link: str = uploaded_file.get(
            "webViewLink",
            f"https://drive.google.com/file/d/{drive_id}/view" if drive_id else "",
        )

        print(f"âœ… Drive upload complete â€” ID: {drive_id}")

        # â”€â”€ 4b. Get the next sequential S.No â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        sheets = _sheets_service()
        sno = _next_row_number(sheets)

        # â”€â”€ 4c. Append row to Google Sheets â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
        # Column mapping:
        # A: S.No  | B: Full Name       | C: Mobile Number | D: Email
        # E: College | F: Department    | G: Year of Study | H: City
        # I: Internship Domain | J: Fee Payment | K: Resume Link | L: Notes
        row: list[list] = [
            [
                sno,                            # A â€” S.No
                name,                           # B â€” Full Name
                phone,                          # C â€” Mobile Number
                email,                          # D â€” Email
                college,                        # E â€” College
                department,                     # F â€” Department
                year_display,                   # G â€” Year of Study
                city,                           # H â€” City
                internship_domain,              # I â€” Internship Domain
                fee_payment,                    # J â€” Fee Payment
                drive_link,                     # K â€” Resume Link
                notes or "",                    # L â€” Notes
            ]
        ]

        sheets.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=SHEET_RANGE,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": row},
        ).execute()

        print(f"âœ… Sheets row #{sno} appended for: {name}")

        return {
            "status": "success",
            "message": "Application received and logged successfully.",
            "sno": sno,
            "drive_id": drive_id,
            "drive_link": drive_link,
        }

    except Exception as pipeline_err:
        print(f"âŒ PIPELINE ERROR: {pipeline_err}", file=sys.stderr)
        return {
            "status": "error",
            "message": "An error occurred while processing your application.",
            "detail": str(pipeline_err),
        }

    finally:
        # Always clean up the locally saved file
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except OSError:
            pass  # Non-fatal: Windows may still hold a handle briefly

