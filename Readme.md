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

## Build and Run Locally with Docker

The `build_run.ps1` script automates building and running the application in a Docker container locally. This is useful for testing the containerized application before deployment.

### Prerequisites for Local Docker Build

- Docker installed and running
- `.env` file created with required environment variables
- `token.json` and `client_secrets1.json` files in the project root (see [Local Setup](#local-setup) section)
- PowerShell Core (pwsh) or Windows PowerShell

### Running the Build Script

#### Basic Usage

```powershell
.\build_run.ps1
```

This will:
- Build a Docker image named `sortyx-resume-ats:local`
- Remove any existing container with the same name
- Run the container with port mapping (localhost:8000 → container:8000)
- Mount `.env`, `token.json`, and `client_secrets1.json` files into the container

#### Using Custom Parameters

```powershell
# Custom image name and port
.\build_run.ps1 -ImageName "sortyx-resume-ats:dev" -HostPort 9000 -ContainerPort 8000

# Rebuild without Docker cache (forces fresh dependencies)
.\build_run.ps1 -NoCache

# All parameters together
.\build_run.ps1 -ImageName "my-custom-image:v1" `
  -ContainerName "my-custom-container" `
  -HostPort 9000 `
  -ContainerPort 8000 `
  -NoCache
```

### Parameters

| Parameter | Default | Description |
|:----------|:--------|:------------|
| `-ImageName` | `sortyx-resume-ats:local` | Docker image name and tag |
| `-ContainerName` | `sortyx-resume-ats-local` | Docker container name |
| `-HostPort` | `8000` | Port on localhost to bind to |
| `-ContainerPort` | `8000` | Port inside the container |
| `-NoCache` | (switch) | Rebuild image without Docker layer cache |

### After Starting the Container

Once the container starts successfully, you'll see:

```
Container started successfully.
Service URL:  http://localhost:8000
Health check: http://localhost:8000/health
Docs:         http://localhost:8000/docs
```

**Test the service:**

```bash
# Health check
curl http://localhost:8000/health

# View API docs
open http://localhost:8000/docs

# Access the application form
open http://localhost:8000

# Access admin dashboard (username: sortyx_admin, password: from .env)
open http://localhost:8000/admin
```

**Useful Docker commands:**

```bash
# View container logs in real-time
docker logs -f sortyx-resume-ats-local

# Stop the container
docker stop sortyx-resume-ats-local

# Remove the container
docker rm -f sortyx-resume-ats-local

# List running containers
docker ps

# Inspect the image
docker images | grep sortyx-resume-ats
```

---

## Compile, Build and Deploy to GCP

The `build_deploy_gcp.ps1` script automates the complete CI/CD pipeline for deploying to Google Cloud Run:
1. Validates Python code syntax
2. Creates/ensures Artifact Registry repository
3. Manages secrets in Secret Manager
4. Builds and pushes Docker image
5. Deploys to Cloud Run with environment variables and secret mounts

### Prerequisites for GCP Deployment

- **Google Cloud CLI** (`gcloud`) installed and authenticated: `gcloud auth login`
- **Docker** installed and running
- **Python** installed (for code compilation check)
- **GCP Project** with the following APIs enabled:
  - Cloud Run API
  - Artifact Registry API
  - Secret Manager API
  - Cloud Logging API
- **Required files:**
  - `.env` file with configuration
  - `token.json` (OAuth token from `generate_token.py`)
  - `client_secrets1.json` (OAuth client credentials)

### Running the Deployment Script

#### Minimal Example (with prompts for missing required parameters)

```powershell
# Set your GCP project ID first (or pass as parameter)
$ProjectId = "your-gcp-project-id"

.\build_deploy_gcp.ps1 -ProjectId <Your-Project-Id>  -ReleaseTag <Release-Tag>
```

```

#### Using Environment Variables

You can pre-set values as environment variables instead of passing them as parameters:

```powershell
$env:SPREADSHEET_ID = "<your-spreadsheet-id>"
$env:GOOGLE_DRIVE_FOLDER_ID = "<your-drive-folder-id>"
$env:ADMIN_USERNAME = "<admin-username>"
$env:ADMIN_PASSWORD = "<your-secure-password>"
$env:TOKEN_SECRET_NAME = "sortyx-resume-ats-token-json"
$env:CLIENT_SECRETS_SECRET_NAME = "sortyx-resume-ats-client-secrets1-json"

# Now you only need to pass the required project ID
.\build_deploy_gcp.ps1 -ProjectId "<your-gcp-project-id>"
```

### Parameters

| Parameter | Required | Default | Description |
|:----------|:---------|:--------|:------------|
| `-ProjectId` | ✅ Yes | — | GCP Project ID |
| `-Region` | No | `us-central1` | GCP region for Cloud Run and Artifact Registry |
| `-ServiceName` | No | `sortyx-resume-ats` | Cloud Run service name |
| `-RepositoryName` | No | `sortyx-resume-ats` | Artifact Registry repository name |
| `-ImageName` | No | `sortyx-resume-ats` | Docker image name (without registry/tag) |
| `-Memory` | No | `2Gi` | Memory allocation per instance |
| `-Cpu` | No | `2` | CPU allocation per instance |
| `-Timeout` | No | `300s` | Request timeout |
| `-MinInstances` | No | `0` | Minimum instances (auto-scaling) |
| `-MaxInstances` | No | `5` | Maximum instances (auto-scaling) |
| `-SpreadsheetId` | ✅ Yes* | — | Google Sheet ID (*from .env if not passed) |
| `-GoogleDriveFolderId` | ✅ Yes* | — | Google Drive folder ID (*from .env if not passed) |
| `-AdminUsername` | ✅ Yes* | — | Admin login username (*from .env if not passed) |
| `-AdminPassword` | ✅ Yes* | — | Admin login password (*from .env if not passed) |
| `-DatabaseUrl` | No | — | Optional database connection string |
| `-TokenFile` | No | `token.json` | Path to OAuth token file |
| `-ClientSecretsFile` | No | `client_secrets1.json` | Path to OAuth client secrets file |
| `-TokenSecretName` | No | `sortyx-resume-ats-token-json` | GCP Secret Manager name for token |
| `-ClientSecretsSecretName` | No | `sortyx-resume-ats-client-secrets1-json` | GCP Secret Manager name for client secrets |
| `-ReleaseTag` | No | Auto-generated | Docker image release tag (defaults to git commit hash or timestamp) |

### Deployment Workflow

The script performs the following steps:

1. **Validation**
   - Checks for required commands (`gcloud`, `docker`, `python`)
   - Verifies required project files exist
   - Validates all required parameters are provided

2. **Python Compilation**
   - Runs `python -m compileall app` to catch syntax errors before deployment

3. **GCP Setup**
   - Sets active GCP project
   - Enables required APIs (Cloud Run, Artifact Registry, Secret Manager)
   - Resolves project number and service account details

4. **Artifact Registry**
   - Creates repository if it doesn't exist
   - Grants IAM permissions for image push and pull

5. **Secret Manager**
   - Creates secrets for `token.json` and `client_secrets1.json`
   - Uploads current versions of these files
   - Grants runtime service account access to secrets

6. **Docker Build**
   - Builds multi-platform image (`linux/amd64`)
   - Tags with both release version and `latest`

7. **Docker Push**
   - Configures Docker authentication for your Artifact Registry
   - Pushes release and latest images

8. **Cloud Run Deployment**
   - Deploys service with environment variables
   - Mounts secrets from Secret Manager
   - Configures auto-scaling, memory, CPU, and timeouts
   - Sets up service account and public access

### Example Complete Deployment Scenario

```powershell
# Setup (run once)
gcloud auth login
gcloud config set project "my-gcp-project"

# Get your IDs
# Google Drive folder ID: https://drive.google.com/drive/folders/<your-folder-id>...
# Google Sheet ID: https://docs.google.com/spreadsheets/d/<your-sheet-id>.../

# Create .env file with these IDs and credentials

# Copy token.json from local setup
# Copy client_secrets1.json from your GCP service account

# Deploy with explicit parameters
.\build_deploy_gcp.ps1 `
  -ProjectId "<your-gcp-project-id>" `
  -Region "us-central1" `
  -SpreadsheetId "<your-spreadsheet-id>" `
  -GoogleDriveFolderId "<your-drive-folder-id>" `
  -AdminUsername "<admin-username>" `
  -AdminPassword "<your-secure-password>" `
  -ReleaseTag "v1.0.0"
```

### After Deployment

Upon successful deployment, you'll see:

```
Deployment complete
Service URL:  https://sortyx-resume-ats-xxxxxxxx-uc.a.run.app
Health check: https://sortyx-resume-ats-xxxxxxxx-uc.a.run.app/health
Admin page:   https://sortyx-resume-ats-xxxxxxxx-uc.a.run.app/admin
Docs:         https://sortyx-resume-ats-xxxxxxxx-uc.a.run.app/docs

Next steps:
1. Test the health endpoint and confirm the secrets are mounted.
2. Submit a sample application to verify /apply works in Cloud Run.
3. Use gcloud run logs tail sortyx-resume-ats --region us-central1 for troubleshooting.
```

**Test the deployment:**

```bash
# Health check
curl https://sortyx-resume-ats-xxxxxxxx-uc.a.run.app/health

# View logs
gcloud run logs read sortyx-resume-ats --region us-central1 --limit 50

# Tail logs in real-time
gcloud run logs tail sortyx-resume-ats --region us-central1

# View service details
gcloud run services describe sortyx-resume-ats --region us-central1

# Update service (without redeploying)
gcloud run services update sortyx-resume-ats --region us-central1 --max-instances 10
```

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
