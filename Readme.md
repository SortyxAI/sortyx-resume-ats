# Sortyx Intelligence: AI Resume and ATS Automation System

## Overview
Sortyx Intelligence is an enterprise-grade recruitment automation platform developed for Sortyx Ventures Private Limited. The system optimizes the initial candidate screening process by utilizing Artificial Intelligence to parse resumes, calculate Applicant Tracking System (ATS) scores against specific Job Descriptions (JDs), and automate the storage of high-potential candidates.

The platform ensures that only qualified applicants are moved forward in the recruitment funnel, reducing manual overhead and increasing the quality of hire.

---

## Core Features
* **Automated ATS Scoring:** Evaluates resumes based on keyword density, skills alignment, and experience relevance.
* **Intelligent Shortlisting:** Automatically identifies candidates meeting a predefined threshold for specific roles.
* **Cloud Repository Integration:** Securely uploads shortlisted resumes to a centralized Google Drive storage system.
* **Admin Intelligence Dashboard:** Provides real-time visibility into applicant data, scores, and application timelines.
* **Dynamic JD Management:** Allows administrators to update job requirements and scoring thresholds on the fly.
* **Relational Data Management:** Persists comprehensive applicant history using a PostgreSQL infrastructure via Supabase.

---

## Technical Stack
| Component | Technology |
| :--- | :--- |
| **Backend Framework** | FastAPI (Python 3.10+) |
| **Database** | PostgreSQL (Supabase) |
| **ORM** | SQLAlchemy |
| **File Storage** | Google Drive API v3 |
| **Frontend** | HTML5, Tailwind CSS, Jinja2 |
| **Server/Hosting** | Render / Docker |

---

## Project Structure
```text
sortyx-resume-ats/
├── app/
│   ├── api/            # Route controllers for upload and admin
│   ├── database/       # Database connection and session management
│   ├── models/         # SQLAlchemy schema definitions
│   ├── services/       # Drive API and ATS analysis logic
│   └── main.py         # Application entry point
├── static/             # CSS, images, and client-side JavaScript
├── templates/          # Jinja2 HTML dashboard templates
├── uploads/            # Temporary storage for processing
├── .env                # Environment secrets configuration
├── Dockerfile          # Containerization instructions
└── requirements.txt    # Project dependencies
# Installation and Deployment
1. Repository SetupClone the project repository to your local environment:
git clone https://github.com/sortyx-ventures/resume-ats-automation.git
cd sortyx-resume-ats
2. Environment Configuration
Create a virtual environment and install the required dependencies:
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
3. Configuration Variables
Create a .env file in the root directory. This file must contain the following variables for the system to function:
4. Database Configuration
DATABASE_URL= contact developer [private]
Google Drive Integration
DRIVE_FOLDER_ID= contact developer [private]
GOOGLE_APPLICATION_CREDENTIALS= contact developer [private]
5. Database Initialization
Run the following command to synchronize the database schema with your Supabase instance:
python -c "from app.database.session import engine; from app.models.candidate import Base; Base.metadata.create_all(bind=engine)"
6. Execution
To start the development server locally:
uvicorn app.main:app --reload
The application will be accessible at http://localhost:8000.
# Security and Data PrivacyAuthentication:
Google Drive interactions are managed through OAuth 2.0 service accounts.
Encrypted Secrets: Production credentials are managed via environment variables and are never stored in the codebase.
Data Integrity: Foreign key constraints and transaction management ensure consistent applicant records.
# Contact and Support
For internal technical support or feature requests, contact the development team at Sortyx Ventures Private Limited.
Copyright 2026 Sortyx Ventures Private Limited. All Rights Reserved.
