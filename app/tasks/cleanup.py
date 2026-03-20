from datetime import datetime, timedelta
from app.database.session import SessionLocal
from app.model.candidate import Candidate
import os

def run_cleanup():
    db = SessionLocal()
    threshold = datetime.now() - timedelta(days=14)
    expired = db.query(Candidate).filter(Candidate.created_at < threshold).all()
    
    for c in expired:
        if os.path.exists(c.resume_path):
            os.remove(c.resume_path)
        db.delete(c)
    
    db.commit()
    db.close()