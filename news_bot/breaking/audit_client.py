import os.path
import pickle # For storing/loading OAuth tokens
import base64

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from ..core import config
from datetime import datetime

def convert_date_str_to_datetime(date_str: str) -> datetime:
    """
    Converts a date string to a datetime object.
    - Input format: Mon, 08 Sep 2025 10:00:00
    - Output format: 2025-09-08
    """
    date_obj = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S")
    return date_obj.strftime("%Y-%m-%d")


def _get_credentials():
    """
    Gets valid user credentials from storage or initiates OAuth2 flow.
    The file token.pickle stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first time.
    """
    creds = None
    if os.path.exists(config.OAUTH_TOKEN_PICKLE_FILE_GMAIL):
        with open(config.OAUTH_TOKEN_PICKLE_FILE_GMAIL, 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing OAuth token...")
                creds.refresh(Request())
            except Exception as e_refresh:
                print(f"Error refreshing token: {e_refresh}. Need to re-authorize.")
                creds = None # Force re-authorization
        if not creds: # creds might be None if refresh failed or no token.pickle
            if not os.path.exists(config.OAUTH_CREDENTIALS_FILE):
                print(f"Error: OAuth credentials.json not found at {config.OAUTH_CREDENTIALS_FILE}")
                print("Please download it from Google Cloud Console and place it in the project root.")
                return None
            try:
                print("Initiating OAuth flow for Google Docs... Please follow browser instructions.")
                flow = InstalledAppFlow.from_client_secrets_file(
                    config.OAUTH_CREDENTIALS_FILE, config.GMAIL_SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e_flow:
                print(f"Error during OAuth flow: {e_flow}")
                return None
        
        # Save the credentials for the next run
        if creds:
            try:
                with open(config.OAUTH_TOKEN_PICKLE_FILE_GMAIL, 'wb') as token:
                    pickle.dump(creds, token)
                print(f"OAuth token saved to {config.OAUTH_TOKEN_PICKLE_FILE_GMAIL}")
            except Exception as e_save_token:
                print(f"Error saving OAuth token: {e_save_token}")
        else:
            print("Failed to obtain OAuth credentials.")
            return None # Explicitly return None if creds are still None
            
    return creds


class GmailApi:
    def __init__(self):
        # alternatively, we could pass credentials to constructor
        # to decouple the code.
        creds = _get_credentials()
        self.service = build("gmail", "v1", credentials=creds)

    def find_emails(self, max_results: int = 500):
        """
        Outputs a list of emails in the Primary inbox.
        - Output format: [{message_id, subject, from, date, encoded_message}, ...]
        """
        print("\n=============== Find Emails: start ===============")
        payload_list = [] 
        # Sending HTTP request to the Gmail API        
        results = (
            self.service.users().messages().list(
                userId="me", 
                labelIds=["INBOX"],
                q="in:inbox -category:{social promotions updates forums}"   # Default to Primary inbox when no explicit query/sender provided
            ).execute()
        )
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return

        print(f"Messages:")
        for message in messages:
            response_msg = (
                self.service.users().messages().get(userId="me", id=message["id"]).execute()
            )
            encoded_message = response_msg["payload"]["parts"][0]["body"]["data"]
            encoded_message = encoded_message.replace("-", "+").replace("_", "/")
            decoded_message = base64.b64decode(encoded_message).decode("utf-8")
            print(f"Decoded message: {decoded_message}")
            
            date_str = response_msg["payload"]["headers"][1]["value"].split(";")[1].strip()
            # Get rid of the timezone
            date_str = date_str.split("-")[0].strip()
            date_str = convert_date_str_to_datetime(date_str)
            
            msg = {
                "message_id": response_msg["id"],
                "subject": response_msg["snippet"],
                "from_": response_msg["payload"]["headers"][0]["value"],
                "date": date_str,
                "decoded_message": decoded_message
            }
            print(f"Message: {msg}")
            payload_list.append(msg)

        print(f"Retrieved {len(payload_list)} messages")
        print("=============== Find Emails: end ===============")
        return payload_list
