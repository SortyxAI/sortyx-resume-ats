"""
Enables Google Sheets API and Google Drive API for the project
using the existing OAuth token - no GCP Console login needed.
"""
import json
import urllib.request
import urllib.error

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

TOKEN_FILE = "token.json"
PROJECT = "resume-490804"
APIS = ["sheets.googleapis.com", "drive.googleapis.com"]

def main():
    with open(TOKEN_FILE) as f:
        t = json.load(f)

    creds = Credentials(
        token=t["token"],
        refresh_token=t["refresh_token"],
        token_uri=t["token_uri"],
        client_id=t["client_id"],
        client_secret=t["client_secret"],
        scopes=t["scopes"],
    )

    if creds.expired:
        creds.refresh(Request())
        print("[INFO] Token refreshed.")

    access_token = creds.token

    for api in APIS:
        url = f"https://serviceusage.googleapis.com/v1/projects/{PROJECT}/services/{api}:enable"
        req = urllib.request.Request(url, method="POST", data=b"{}")
        req.add_header("Authorization", "Bearer " + access_token)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req) as resp:
                body = json.loads(resp.read())
                print(f"[OK] {api} enabled. Operation: {body.get('name', 'done')}")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            print(f"[ERR] {api}: HTTP {e.code}")
            print("      " + body[:400])

if __name__ == "__main__":
    main()
