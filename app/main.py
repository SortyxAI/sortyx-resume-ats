import os
import secrets
from fastapi import FastAPI, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel
from dotenv import load_dotenv

# Internal Imports
from app.api import upload
from app.database.base import Base
from app.database.session import engine, get_db
from app.model.candidate import Candidate
from app.model.job import Job

# Load Environment Variables
load_dotenv()

# 1. Initialize DB Tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Resume.AI - SortyX Ventures")
security = HTTPBasic()

# 2. Setup Static Files & Templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# 3. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Pydantic Schema for Job Creation
class JobCreate(BaseModel):
    title: str
    description: str
    min_score: int

# --- 🛡️ SECURITY HELPER ---
def get_current_admin(credentials: HTTPBasicCredentials = Depends(security)):
    """Triggers a browser login popup for Admin routes."""
    correct_username = secrets.compare_digest(credentials.username, os.getenv("ADMIN_USERNAME", "admin"))
    correct_password = secrets.compare_digest(credentials.password, os.getenv("ADMIN_PASSWORD", "sortyx123"))
    
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

# --- 🔗 PUBLIC ROUTES (For Candidates) ---

@app.get("/", response_class=HTMLResponse)
async def serve_home(request: Request):
    """The Public Application Form Link."""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/get-active-roles")
async def get_roles(db: Session = Depends(get_db)):
    """Fetches job titles for the dropdown on the frontend."""
    roles = db.query(Job.title).all()
    return [r[0] for r in roles]

# Include the background upload router (Candidate Uploads)
app.include_router(upload.router)

# --- 🔐 PROTECTED ADMIN ROUTES (For SortyX Team) ---

@app.get("/admin", response_class=HTMLResponse)
async def get_admin_page(
    request: Request, 
    username: str = Depends(get_current_admin)
):
    """The JD Management Page."""
    return templates.TemplateResponse("admin_jd.html", {"request": request})

@app.get("/admin/results", response_class=HTMLResponse)
async def view_results(
    request: Request, 
    db: Session = Depends(get_db),
    username: str = Depends(get_current_admin)
):
    """The Candidate Scoring Dashboard."""
    candidates = db.query(Candidate).all()
    jobs = {j.title: j.min_score for j in db.query(Job).all()}
    
    return templates.TemplateResponse("admin_results.html", {
        "request": request, 
        "candidates": candidates,
        "job_thresholds": jobs
    })

@app.post("/admin/create-job")
async def create_or_update_job(
    job_in: JobCreate, 
    db: Session = Depends(get_db),
    username: str = Depends(get_current_admin)
):
    """Logic to either add a new role or update an existing JD."""
    try:
        existing_job = db.query(Job).filter(Job.title == job_in.title).first()
        
        if existing_job:
            existing_job.description = job_in.description
            existing_job.min_score = job_in.min_score
            action = "updated"
        else:
            new_job = Job(**job_in.dict())
            db.add(new_job)
            action = "created"
            
        db.commit()
        return {"status": "success", "action": action}
    except Exception as e:
        db.rollback()
        print(f"❌ DB ERROR: {e}")
        raise HTTPException(status_code=500, detail="Database operation failed")