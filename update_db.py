import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    print("❌ DATABASE_URL not found!")
    exit(1)

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)

def update_schema():
    with engine.connect() as conn:
        print("🔍 Checking columns in 'candidates' table...")
        
        # Check if columns exist
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'candidates'
        """))
        existing_columns = [row[0] for row in result]
        print(f"Existing columns: {existing_columns}")
        
        columns_to_add = [
            ("phone", "VARCHAR"),
            ("notes", "VARCHAR"),
            ("drive_id", "VARCHAR")
        ]
        
        for col_name, col_type in columns_to_add:
            if col_name not in existing_columns:
                print(f"➕ Adding column '{col_name}'...")
                conn.execute(text(f"ALTER TABLE candidates ADD COLUMN {col_name} {col_type}"))
                conn.commit()
                print(f"✅ Column '{col_name}' added.")
            else:
                print(f"ℹ️ Column '{col_name}' already exists.")

if __name__ == "__main__":
    try:
        update_schema()
        print("🏁 Database schema update complete.")
    except Exception as e:
        print(f"❌ Error updating database: {e}")
