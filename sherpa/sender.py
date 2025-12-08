import os.path
import base64
import sqlite3
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import requests
from config import DB_PATH, PHANTOMBUSTER_API_KEY, LINKEDIN_CONNECTION_AGENT_ID
from throttler import random_sleep, human_typing_delay

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: credentials.json not found. Please download it from Google Cloud Console.")
                return None
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def send_email(service, to_email, subject, body):
    try:
        message = MIMEText(body)
        message['to'] = to_email
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        message = {'raw': raw}
        
        sent_message = service.users().messages().send(userId="me", body=message).execute()
        print(f"Email sent to {to_email}. Message Id: {sent_message['id']}")
        return True
    except Exception as e:
        print(f"An error occurred sending email to {to_email}: {e}")
        return False

def send_whatsapp_nudge(driver, phone, message):
    """
    Sends a WhatsApp message using Selenium Web.
    Requires the user to be logged in to WhatsApp Web.
    """
    try:
        # Format phone number (remove non-digits, ensure country code if needed)
        # This is a simplified example.
        
        # Navigate to chat
        url = f"https://web.whatsapp.com/send?phone={phone}&text={message}"
        driver.get(url)
        
        # Wait for page load and send button
        time.sleep(15) # Wait for page to load
        
        # Press Enter to send (or find the send button)
        # This is fragile and depends on WhatsApp Web DOM
        action = webdriver.ActionChains(driver)
        action.send_keys(Keys.ENTER)
        action.perform()
        
        time.sleep(5)
        print(f"WhatsApp nudge sent to {phone}")
        return True
    except Exception as e:
        print(f"Error sending WhatsApp to {phone}: {e}")
        print(f"Error sending WhatsApp to {phone}: {e}")
        return False

def trigger_phantombuster_connection(linkedin_url, message):
    """
    Triggers the PhantomBuster LinkedIn Network Booster.
    """
    if LINKEDIN_CONNECTION_AGENT_ID == "YOUR_LINKEDIN_CONNECTION_AGENT_ID":
        print("Skipping LinkedIn: Agent ID not configured.")
        return

    url = "https://api.phantombuster.com/api/v2/agents/launch"
    headers = {
        "X-Phantombuster-Key": PHANTOMBUSTER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "id": LINKEDIN_CONNECTION_AGENT_ID,
        "argument": {
            "profileUrls": [linkedin_url],
            "message": message,
            "numberOfAddsPerLaunch": 1
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"LinkedIn connection queued for {linkedin_url}")
    except Exception as e:
        print(f"Error triggering LinkedIn Phantom: {e}")

def run_sender():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get Approved leads
    cursor.execute("SELECT * FROM leads WHERE status = 'Approved'")
    leads = cursor.fetchall()
    
    if not leads:
        print("No approved leads to process.")
        return

    # Initialize Gmail Service
    gmail_service = get_gmail_service()
    if not gmail_service:
        return

    # Initialize Selenium (only if there are leads)
    options = webdriver.ChromeOptions()
    options.add_argument("user-data-dir=selenium_data") # Keep session
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        print("Selenium driver initialized. Please scan QR code if needed.")
        time.sleep(5) # Give time to load
    except Exception as e:
        print(f"Failed to initialize Selenium: {e}")
        driver = None 

    for lead in leads:
        print(f"Processing outreach for {lead['email']}...")
        
        # 1. Send Email
        if lead['email'] and lead['draft_email_subject'] and lead['draft_email_body']:
            if send_email(gmail_service, lead['email'], lead['draft_email_subject'], lead['draft_email_body']):
                # Update status
                cursor.execute("UPDATE leads SET status = 'Contacted', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lead['id'],))
                conn.commit()
                
                # Throttling
                random_sleep(min_seconds=10, max_seconds=30) 
        else:
            print(f"Skipping Email for {lead['first_name']}: Missing email or draft.")
        
        # 2. LinkedIn
        if lead['linkedin_url'] and lead['draft_linkedin_note']:
            trigger_phantombuster_connection(lead['linkedin_url'], lead['draft_linkedin_note'])
        
        # 3. WhatsApp
        if driver and lead['phone'] and lead['draft_whatsapp_nudge']:
            send_whatsapp_nudge(driver, lead['phone'], lead['draft_whatsapp_nudge'])

    if driver:
        driver.quit()
    conn.close()

if __name__ == "__main__":
    run_sender()
