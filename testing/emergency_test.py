import os
from dotenv import load_dotenv
from app.core.google_drive import upload_to_drive

load_dotenv()

# 1. Create a dummy test file
test_file = "debug_test.txt"
with open(test_file, "w") as f:
    f.write("This is a manual test of the Google Drive integration.")

print(f"--- STARTING MANUAL UPLOAD TEST ---")
print(f"Target Folder ID from .env: {os.getenv('GOOGLE_DRIVE_FOLDER_ID')}")

try:
    # 2. Try the upload
    file_id = upload_to_drive(test_file, "DEBUG_SUCCESS.txt")
    print(f"✅ SUCCESS! File ID: {file_id}")
    print("Go check your Google Drive folder now.")
except Exception as e:
    print("❌ FAILED!")
    print(f"The error is: {e}")
finally:
    if os.path.exists(test_file):
        os.remove(test_file)