import os
import secrets

from dotenv import load_dotenv

# Load Environment Variables FIRST — before any os.getenv() calls
load_dotenv()

from fastapi import FastAPI, Depends, HTTPException, Request, Response, status
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Internal Imports
from app.api import upload

SPREADSHEET_ID: str | None = os.getenv("SPREADSHEET_ID")
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

# ---------------------------------------------------------------------------
# App Initialization
# ---------------------------------------------------------------------------
app = FastAPI(title="Resume.AI - SortyX Ventures")
security = HTTPBasic()

# Static Files & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Security Helper
# ---------------------------------------------------------------------------
def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Triggers a browser login popup for Admin routes."""
    correct_username = secrets.compare_digest(
        credentials.username, os.getenv("ADMIN_USERNAME", "admin")
    )
    correct_password = secrets.compare_digest(
        credentials.password, os.getenv("ADMIN_PASSWORD", "sortyx123")
    )

    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ---------------------------------------------------------------------------
# Public Routes (Candidates)
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """The public application form."""
    return templates.TemplateResponse("index.html", {"request": request})


# Include the upload router — handles POST /apply
app.include_router(upload.router)


# ---------------------------------------------------------------------------
# Protected Admin Routes (SortyX Team)
# ---------------------------------------------------------------------------

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_page(
    request: Request,
    username: str = Depends(get_current_admin),
):
    """Admin Dashboard — shows all applicant records from Google Sheets."""
    return templates.TemplateResponse("admin_jd.html", {"request": request})


@app.get("/admin/health-status")
async def get_admin_health(username: str = Depends(get_current_admin)):
    """Returns a detailed health status of Drive, Sheets, and token for the admin dashboard."""
    import json
    from datetime import datetime, timezone

    result = {
        "token": {"status": "unknown", "detail": ""},
        "drive": {"status": "unknown", "detail": ""},
        "sheets": {"status": "unknown", "detail": "", "row_count": None},
        "credentials_file": {"status": "unknown", "detail": ""},
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }

    # --- Credentials file check ---
    creds_path = "client_secrets1.json"
    if os.path.exists(creds_path):
        result["credentials_file"] = {"status": "ok", "detail": "client_secrets1.json found"}
    else:
        result["credentials_file"] = {"status": "error", "detail": "client_secrets1.json missing"}

    # --- Token file check ---
    token_path = "token.json"
    if not os.path.exists(token_path):
        result["token"] = {"status": "error", "detail": "token.json not found. Run the OAuth setup script to generate it."}
        result["drive"] = {"status": "error", "detail": "Cannot check — token missing"}
        result["sheets"] = {"status": "error", "detail": "Cannot check — token missing", "row_count": None}
        return JSONResponse(result)

    try:
        with open(token_path, "r") as f:
            token_data = json.load(f)
        expiry_str = token_data.get("expiry", "")
        has_refresh = bool(token_data.get("refresh_token"))

        # Check if expired
        token_expired = False
        if expiry_str:
            try:
                expiry_dt = datetime.fromisoformat(expiry_str.replace("Z", "+00:00"))
                token_expired = expiry_dt < datetime.now(timezone.utc)
            except Exception:
                pass

        if token_expired and not has_refresh:
            result["token"] = {
                "status": "error",
                "detail": f"Token EXPIRED on {expiry_str} and no refresh token found. Delete token.json and re-authorize.",
            }
            result["drive"] = {"status": "error", "detail": "Cannot check — token expired"}
            result["sheets"] = {"status": "error", "detail": "Cannot check — token expired", "row_count": None}
            return JSONResponse(result)

        status_note = "expired but has refresh token — will auto-renew on next API call" if token_expired else "valid"
        result["token"] = {
            "status": "ok" if not token_expired else "warn",
            "detail": f"Token {status_note}. Expiry: {expiry_str or 'N/A'}",
        }
    except Exception as e:
        result["token"] = {"status": "error", "detail": f"Could not read token: {e}"}
        result["drive"] = {"status": "error", "detail": "Cannot check — token unreadable"}
        result["sheets"] = {"status": "error", "detail": "Cannot check — token unreadable", "row_count": None}
        return JSONResponse(result)

    def friendly_error(e: Exception) -> str:
        msg = str(e)
        if "invalid_scope" in msg:
            return (
                "Scope mismatch — token was not authorized with required scopes "
                "(drive.file + spreadsheets). Fix: delete token.json and re-run OAuth setup."
            )
        if "invalid_grant" in msg:
            return "Token revoked or expired. Fix: delete token.json and re-run OAuth setup."
        if "invalid_client" in msg:
            return "Invalid OAuth client credentials. Check client_secrets1.json."
        return msg

    try:
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

        # --- Drive check ---
        # drive.about() needs a broad scope; instead use files().list() which works with drive.file
        try:
            drive = build("drive", "v3", credentials=creds)
            folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "")
            try:
                # Try to get the configured folder directly
                folder = drive.files().get(fileId=folder_id, fields="id,name").execute()
                result["drive"] = {"status": "ok", "detail": f"Drive folder accessible: '{folder.get('name', folder_id)}'"}
            except Exception:
                # Folder may not be app-created; just verify API is reachable
                drive.files().list(pageSize=1, fields="files(id)").execute()
                result["drive"] = {"status": "ok", "detail": "Drive API reachable (upload folder is external — normal)"}
        except Exception as e:
            result["drive"] = {"status": "error", "detail": friendly_error(e)}

        # --- Sheets check ---
        try:
            sheets = build("sheets", "v4", credentials=creds)
            sheet_result = (
                sheets.spreadsheets()
                .values()
                .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:A")
                .execute()
            )
            rows = sheet_result.get("values", [])
            data_rows = max(0, len(rows) - 1)  # subtract header
            result["sheets"] = {
                "status": "ok",
                "detail": f"Spreadsheet accessible (ID: ...{(SPREADSHEET_ID or '')[-6:]})",
                "row_count": data_rows,
            }
        except Exception as e:
            result["sheets"] = {"status": "error", "detail": friendly_error(e), "row_count": None}

    except Exception as e:
        result["token"] = {"status": "error", "detail": f"Credential build failed: {friendly_error(e)}"}

    return JSONResponse(result)


@app.get("/admin/data")
async def get_dashboard_data(username: str = Depends(get_current_admin)):
    """Returns all rows from the Google Sheet as JSON for the dashboard."""
    try:
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        sheets = build("sheets", "v4", credentials=creds)
        result = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=SPREADSHEET_ID, range="Sheet1!A:L")
            .execute()
        )
        rows = result.get("values", [])
        if not rows:
            return JSONResponse({"headers": [], "rows": [], "total": 0})

        headers = rows[0]          # first row is the header
        data_rows = rows[1:]       # everything else
        return JSONResponse({
            "headers": headers,
            "rows": data_rows,
            "total": len(data_rows),
        })
    except Exception as e:
        print(f"[ERR] Dashboard data fetch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Utility Routes
# ---------------------------------------------------------------------------

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    return Response(status_code=204)


@app.get("/health")
def health_check():
    """Lightweight health check — verifies Google credential file presence."""
    health_status: dict = {"status": "ok", "checks": {}}

    credentials_path = "client_secrets1.json"
    if os.path.exists(credentials_path):
        health_status["checks"]["google_creds"] = "File Found ✅"
    else:
        health_status["checks"]["google_creds"] = "Missing ❌"
        health_status["status"] = "error"

    token_path = "token.json"
    if os.path.exists(token_path):
        health_status["checks"]["token"] = "Found ✅"
    else:
        health_status["checks"]["token"] = "Missing ❌"
        health_status["status"] = "error"

    return health_status


# ---------------------------------------------------------------------------
# Startup Banner
# ---------------------------------------------------------------------------
CREDENTIALS_PATH = "client_secrets1.json"

if os.path.exists(CREDENTIALS_PATH):
    print(f"[OK] Found Secret File at: {os.path.abspath(CREDENTIALS_PATH)}")
else:
    print(f"[ERROR] {CREDENTIALS_PATH} NOT FOUND! Check Render Secret Files tab.")
