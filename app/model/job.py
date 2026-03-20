from sqlalchemy import Column, Integer, String, Text
from app.database.session import Base

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, unique=True, index=True) # e.g., "Python Developer"
    description = Column(Text) # The raw JD text for Llama 3
    min_score = Column(Integer, default=70) # Threshold for "Shortlisted"