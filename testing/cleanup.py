import os
import time

# Path to your uploads folder
UPLOAD_DIR = os.path.join(os.getcwd(), "uploads")

# Delete files older than 24 hours (86,400 seconds)
CUTOFF = time.time() - 86400

def clean_uploads():
    count = 0
    for filename in os.listdir(UPLOAD_DIR):
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        # Only delete if it's a file and it's older than the cutoff
        if os.path.isfile(file_path) and os.path.getmtime(file_path) < CUTOFF:
            os.remove(file_path)
            count += 1
            
    print(f"Successfully cleared {count} old resumes from the server.")

if __name__ == "__main__":
    clean_uploads()