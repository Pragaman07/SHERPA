import os.path
import base64
import sqlite3
import json
import google.generativeai as genai
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from config import DB_PATH, GEMINI_API_KEY

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly', 'https://www.googleapis.com/auth/gmail.modify']

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def classify_reply(email_body):
    """
    Uses Gemini to classify the reply.
    """
    model = genai.GenerativeModel('gemini-2.0-flash')
    prompt = f"""
    You are a sales assistant. Classify the following email reply from a prospect.
    Categories:
    - INTERESTED: They want to know more, meet, or chat.
    - LATER: They are busy or asked to contact later.
    - STOP: They are not interested, asked to unsubscribe, or stop contacting.
    - OTHER: Auto-reply, out of office, or unclear.
    
    Email Body:
    {email_body}
    
    Output only the category name.
    """
    try:
        response = model.generate_content(prompt)
        return response.text.strip().upper()
    except Exception as e:
        print(f"Error classifying reply: {e}")
        return "OTHER"

def process_replies():
    service = get_gmail_service()
    if not service:
        return

    # List unread messages
    results = service.users().messages().list(userId='me', q='is:unread').execute()
    messages = results.get('messages', [])

    if not messages:
        print("No new messages.")
        return

    conn = get_db_connection()
    cursor = conn.cursor()

    for message in messages:
        msg = service.users().messages().get(userId='me', id=message['id']).execute()
        
        # Extract headers
        headers = msg['payload']['headers']
        sender = next((h['value'] for h in headers if h['name'] == 'From'), None)
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), None)
        
        # Extract email address from sender "Name <email@example.com>"
        email_address = sender.split('<')[-1].replace('>', '') if sender else None
        
        # Check if this email is in our leads db
        cursor.execute("SELECT * FROM leads WHERE email = ?", (email_address,))
        lead = cursor.fetchone()
        
        if lead:
            print(f"Reply received from lead: {email_address}")
            
            # Get body (simplified)
            if 'parts' in msg['payload']:
                parts = msg['payload']['parts']
                data = parts[0]['body']['data']
            else:
                data = msg['payload']['body']['data']
            
            body = base64.urlsafe_b64decode(data).decode('utf-8')
            
            # Classify
            category = classify_reply(body)
            print(f"Classification: {category}")
            
            # Update DB
            new_status = "Replied"
            if category == "INTERESTED":
                new_status = "Interested"
            elif category == "STOP":
                new_status = "Dead"
            elif category == "LATER":
                new_status = "Snoozed"
            
            cursor.execute("UPDATE leads SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_status, lead['id']))
            conn.commit()
            
            # Stop Switch: If replied, we generally stop automated follow-ups (handled by status check in sender)
            print(f"Updated status for {email_address} to {new_status}")
            
            # Mark as read
            service.users().messages().modify(userId='me', id=message['id'], body={'removeLabelIds': ['UNREAD']}).execute()

    conn.close()

if __name__ == "__main__":
    process_replies()
