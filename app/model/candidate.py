from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.sql import func
from app.database.base import Base

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    college = Column(String)
    role = Column(String)
    email = Column(String)
    yop = Column(Integer)
    resume_path = Column(String)
    ats_score = Column(Float)
    analysis = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())