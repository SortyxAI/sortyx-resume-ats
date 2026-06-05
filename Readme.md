# SortyX Resume ATS — Setup & Deployment Guide

A FastAPI application that accepts internship applications via a web form, uploads resumes to **Google Drive**, and logs applicant data into a **Google Sheet**. An admin dashboard at `/admin` lets the SortyX team view all submissions.

---

## Project Structure

```
resume_ai/
├── app/
│   ├── api/
│   │   └── upload.py          # POST /apply — Drive upload + Sheets append
│   ├── core/
│   │   ├── config.py          # App settings (loaded from .env)
│   │   └── google_drive.py    # Drive helpers
│   ├── services/
│   │   ├── evaluator.py
│   │   └── parser.py
│   └── main.py                # FastAPI app, admin routes, health check
├── templates/
│   ├── index.html             # Candidate application form
│   └── admin_jd.html          # Admin dashboard
├── static/                    # Static assets (logo, etc.)
├── uploads/                   # Temporary local file storage (auto-cleaned)
├── client_secrets1.json       # OAuth client credentials (do NOT commit)
├── token.json                 # OAuth access/refresh token (do NOT commit)
├── generate_token.py          # One-time script to generate token.json
├── .env                       # Environment variables (do NOT commit)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

---

## Prerequisites

### 1. Google Cloud Project Setup

You need a Google Cloud project with the following **APIs enabled**:

| API | Why |
|:----|:----|
| **Google Drive API** | Upload resumes to a Drive folder |
| **Google Sheets API** | Append applicant data rows to a Sheet |

Enable them at:
- Drive: https://console.cloud.google.com/apis/library/drive.googleapis.com
- Sheets: https://console.cloud.google.com/apis/library/sheets.googleapis.com

> **Important:** Both APIs must be enabled in the **same project** as your OAuth client credentials (`client_secrets1.json`).

### 2. OAuth Client Credentials

1. In your GCP project, go to **APIs & Services → Credentials**
2. Create an **OAuth 2.0 Client ID** (Desktop app / Installed app type)
3. Download the JSON and save it as `client_secrets1.json` in the project root

### 3. Google Drive Folder & Sheet

- Create a folder in Google Drive to store resumes — copy its ID from the URL
- Create a Google Sheet for applicant data — copy its ID from the URL
- The Sheet must have a header row in `Sheet1` with these columns in order:

  `S.No | Full Name | Mobile Number | Email | College | Department | Year of Study | City | Internship Domain | Fee Payment | Resume Link | Notes`

---

## Local Setup

### 1. Clone & install dependencies

```bash
git clone https://github.com/SortyxAI/sortyx-resume-ats.git
cd sortyx-resume-ats
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

### 2. Create `.env` file

```env
GOOGLE_DRIVE_FOLDER_ID=your_drive_folder_id_here
SPREADSHEET_ID=your_google_sheet_id_here
ADMIN_USERNAME=sortyx_admin
ADMIN_PASSWORD=YourSecurePassword
```

### 3. Generate `token.json` (one-time OAuth setup)

This creates the OAuth token that allows the app to access Drive and Sheets on behalf of your Google account.

```bash
python generate_token.py
```

- A browser window will open — log in with the Google account that **owns** the Drive folder and Sheet
- Click **Allow** to grant both Drive and Sheets permissions
- `token.json` is written automatically with the correct scopes:
  - `https://www.googleapis.com/auth/drive`
  - `https://www.googleapis.com/auth/spreadsheets`

> **Note:** The token includes a refresh token and will auto-renew every hour. You only need to re-run this script if you revoke access or change OAuth scopes.

> **Windows note:** If you see a `UnicodeEncodeError` for emoji characters after the browser step, that is a display-only issue — `token.json` is still written successfully.

### 4. Run the development server

```bash
uvicorn app.main:app --reload
```

The app will be available at **http://localhost:8000**

| Route | Description |
|:------|:------------|
| `/` | Candidate application form |
| `/admin` | Admin dashboard (requires HTTP Basic Auth) |
| `/admin/health-status` | Detailed Drive / Sheets / token health check |
| `/admin/data` | Raw JSON of all applicant rows |
| `/health` | Lightweight credential file presence check |

---

## Re-generating the OAuth Token

You must re-run `generate_token.py` if:
- You changed the OAuth scopes in the code
- The refresh token was revoked (e.g. you removed app access via your Google account security settings)
- You switch to a different Google account

```bash
# Delete the old token first (recommended)
del token.json

python generate_token.py
```

---

## OAuth Scopes Used

| Scope | Purpose |
|:------|:--------|
| `https://www.googleapis.com/auth/drive` | Upload resumes to any Drive folder (including user-created folders) |
| `https://www.googleapis.com/auth/spreadsheets` | Read and append rows to the Google Sheet |

> **Why `drive` instead of `drive.file`?**
> The `drive.file` scope only allows access to files the app itself created. Since the target Drive folder is created manually by the user in Google Drive, the broader `drive` scope is required to access it.

---

## Deployment to Render.com

### Step 1: Push to GitHub

```bash
git add .
git commit -m "your commit message"
git push origin main
```

### Step 2: Add Secret Files on Render

The app requires two credential files that must **not** be committed to Git. Upload them as Render Secret Files:

1. In the Render dashboard, go to your Web Service → **Secret Files**
2. Add the following files:

| Filename | Content |
|:---------|:--------|
| `client_secrets1.json` | Paste the full contents of your local `client_secrets1.json` |
| `token.json` | Paste the full contents of your local `token.json` (generate it locally first) |

### Step 3: Set Environment Variables on Render

In your Web Service → **Environment**, add:

| Key | Value |
|:----|:------|
| `GOOGLE_DRIVE_FOLDER_ID` | Your Drive folder ID |
| `SPREADSHEET_ID` | Your Google Sheet ID |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD` | Admin login password |

### Step 4: Deploy

1. Click **New +** → **Web Service**
2. Connect your GitHub repository (`SortyxAI/sortyx-resume-ats`)
3. Set **Environment** to **Docker**
4. Select **Free** tier instance
5. Click **Create Web Service**

Render will build the Docker container and deploy. Once you see **`Your service is live`** in the logs, the app is accessible via the `.onrender.com` URL shown at the top of the dashboard.

---

## Bug Fixes Applied

| Issue | Root Cause | Fix |
|:------|:-----------|:----|
| `SPREADSHEET_ID` always `None` at startup | `load_dotenv()` was called **after** `os.getenv("SPREADSHEET_ID")` in `main.py` | Moved `load_dotenv()` to execute before any `os.getenv()` calls |
| Drive upload returns 404 on folder | `drive.file` scope cannot access user-created folders | Changed scope to `drive` (full access) in `upload.py`, `main.py`, and `generate_token.py` |
| Sheets API errors (403 SERVICE_DISABLED) | Google Sheets API was not enabled in the GCP project | Enable via GCP Console → APIs & Services → Library |
| `[WinError 32]` file locked after Drive upload on Windows | `MediaFileUpload` keeps the file handle open after upload | Added `media._fd.close()` after upload and wrapped `os.remove()` in `try/except` |
| Token expired with wrong scope | Old token only had `drive.file` scope and had expired | Re-generated via `generate_token.py` with correct `drive` + `spreadsheets` scopes |

---

## Security Notes

- `client_secrets1.json` and `token.json` are in `.gitignore` — **never commit them**
- Admin routes are protected by HTTP Basic Authentication
- Uploaded resume files are saved temporarily and **deleted immediately** after the Drive upload completes
- The token auto-refreshes using the stored `refresh_token` — no manual renewal needed under normal operation
