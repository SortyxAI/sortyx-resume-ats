import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8000"

async def test_full_pipeline():
    print("🧪 STARTING AUTOMATED SYSTEM TEST...")

    async with httpx.AsyncClient() as client:
        # 1. Test Admin Job Creation
        print("📝 Step 1: Creating 'Python Senior' Job...")
        job_data = {
            "title": "Python Senior",
            "description": "Must know FastAPI, PostgreSQL, and AI. 5 years experience.",
            "min_score": 80
        }
        res1 = await client.post(f"{BASE_URL}/admin/create-job", json=job_data)
        print(f"Status: {res1.status_code}")
        try:
            res1 = await client.post(f"{BASE_URL}/admin/create-job", json=job_data, timeout=30.0)
            res1.raise_for_status() # This catches 4xx and 5xx errors
            print(f"Status: {res1.status_code} - {res1.json()}")
        except httpx.ReadError:
            print("❌ SERVER CRASHED: The backend stopped responding mid-request.")
        except httpx.HTTPStatusError as e:
            print(f"❌ SERVER ERROR {e.response.status_code}: Check your FastAPI logs.")
        except Exception as e:
            print(f"❌ UNEXPECTED ERROR: {e}")

        # 2. Test Dropdown Sync
        print("🔄 Step 2: Checking Candidate Dropdown...")
        res2 = await client.get(f"{BASE_URL}/get-active-roles")
        if "Python Senior" in res2.json():
            print("✅ Dropdown Sync: SUCCESS")

        # 3. Test Candidate Submission (Mock File)
        print("📤 Step 3: Submitting Mock Application...")
        files = {'file': ('test_resume.pdf', b'fake pdf content', 'application/pdf')}
        data = {
            "name": "AI Test Bot",
            "email": "bot@sortyx.ai",
            "role": "Python Senior"
        }
        res3 = await client.post(f"{BASE_URL}/api/upload", data=data, files=files)
        print(f"Status: {res3.status_code} - {res3.json()}")

    print("\n🏁 TEST COMPLETE. Now check your /admin/results page!")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())