"""
Run this script once to generate a fresh token.json with the correct OAuth scopes.
It will open a browser window — log in with the Google account that owns the Drive folder
and Google Sheet, then authorize the requested permissions.

Usage:
    python generate_token.py
"""

import json
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]

CLIENT_SECRETS_FILE = "client_secrets1.json"
TOKEN_OUTPUT_FILE = "token.json"


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)

    # Serialize to the same format google-auth uses
    token_data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
        "universe_domain": "googleapis.com",
        "account": "",
        "expiry": creds.expiry.isoformat() + "Z" if creds.expiry else None,
    }

    with open(TOKEN_OUTPUT_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    print(f"\n[OK] token.json written successfully!")
    print(f"   Scopes granted : {list(creds.scopes)}")
    print(f"   Expiry         : {creds.expiry}")
    print(f"   Refresh token  : {'present' if creds.refresh_token else 'MISSING'}")


if __name__ == "__main__":
    main()
