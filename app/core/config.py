import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "Resume.AI"
    DATABASE_URL: str = os.getenv("DATABASE_URL")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY")
    GOOGLE_DRIVE_FOLDER_ID: str = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    UPLOAD_DIR: str = "uploads"

settings = Settings()