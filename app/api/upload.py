import os
import uuid
import shutil
from fastapi import APIRouter, UploadFile, File, Form, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session

# Internal Imports
from app.database.session import get_db, SessionLocal
from app.model.candidate import Candidate
from app.services.parser import parse_resume
from app.services.evaluator import evaluate_resume
from app.core.google_drive import upload_to_drive
from app.core.config import settings

router = APIRouter()

@router.post("/apply")
async def apply(
    background_tasks: BackgroundTasks,
    name: str = Form(None),
    first_name: str = Form(None),
    last_name: str = Form(None),
    college: str = Form(...),
    role: str = Form(...),
    email: str = Form(...),
    yop: int = Form(...),
    phone: str = Form(...),
    file: UploadFile = File(...),
    notes: str = Form(None),
    db: Session = Depends(get_db)
):
    # 0. Handle name construction if not provided directly
    if not name and (first_name or last_name):
        name = f"{(first_name or '').strip()} {(last_name or '').strip()}".strip()
    
    if not name:
        name = "Unknown Candidate"

    # 1. Check folder and extension
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in ['.pdf', '.docx']:
        raise HTTPException(status_code=400, detail="Use PDF or DOCX only.")

    # 2. Secure File Saving
    unique_name = f"{uuid.uuid4()}{file_ext}"
    file_path = os.path.abspath(os.path.join(settings.UPLOAD_DIR, unique_name))

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    except Exception as e:
        print(f"❌ File Save Error: {e}")
        raise HTTPException(status_code=500, detail="Could not save file locally.")

    # 3. Create Database Entry
    new_candidate = Candidate(
        name=name, college=college, role=role, email=email, 
        phone=phone, yop=yop, resume_path=file_path, ats_score=0.0, 
        analysis={}, notes=notes
    )
    db.add(new_candidate)
    db.commit()
    db.refresh(new_candidate)

    # 4. Trigger Background Processing
    background_tasks.add_task(run_complete_pipeline, new_candidate.id, file_path, role)

    return {"message": "Application received! AI is analyzing now.", "id": new_candidate.id}

async def run_complete_pipeline(candidate_id: int, file_path: str, role: str):
    """Handles Parsing -> AI Scoring -> Drive Upload in the background."""
    # We use a fresh DB session for the background thread
    db = SessionLocal()
    try:
        print(f"🚀 Processing Candidate {candidate_id}...")

        # A. Parse
        text = parse_resume(file_path)
        if not text:
            print("❌ Parsing failed.")
            return

        # B. AI Score
        result = await evaluate_resume(text, role)
        score = result.get("score", 0)

        # C. Update DB
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        if candidate:
            candidate.ats_score = score
            candidate.analysis = result
            db.commit()
            print(f"✅ DB Updated. Score: {score}")

            # D. Drive Upload (Critical Step)
            if score >= 50:  # Only upload if score is decent
                drive_name = f"{score}_{candidate.name}_Resume{os.path.splitext(file_path)[1]}"
                print(f"📤 Uploading {drive_name} to Google Drive...")
                try:
                    drive_id = upload_to_drive(file_path, drive_name)
                    if drive_id:
                        candidate.drive_id = drive_id
                        db.commit()
                        print(f"🏁 SUCCESS: File is in Google Drive. ID: {drive_id}")
                    else:
                        print("❌ Drive upload returned no ID.")
                except Exception as drive_err:
                    print(f"❌ DRIVE ERROR: {drive_err}")
            else:
                print(f"⏭️ Score {score} too low for Drive upload.")

    except Exception as e:
        print(f"❌ PIPELINE CRASH: {e}")
    finally:
        db.close()
        # Clean up local file after processing
        if os.path.exists(file_path):
            os.remove(file_path)
