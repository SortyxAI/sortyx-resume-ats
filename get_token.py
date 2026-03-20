import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# The permissions we need
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def main():
    creds = None
    # Check if we already have a token
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no token, log in through the browser
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secrets1.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the token for next time
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    print("✅ SUCCESS! token.json created. You are now authenticated as YOURSELF.")

if __name__ == '__main__':
    main()