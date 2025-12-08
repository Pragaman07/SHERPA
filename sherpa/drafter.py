import google.generativeai as genai
import sqlite3
import json
from config import GEMINI_API_KEY, DB_PATH

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_drafts(lead):
    """
    Generates email, LinkedIn note, and WhatsApp nudge using Gemini.
    """
    model = genai.GenerativeModel('gemini-flash-latest')
    
    # Construct the prompt (The "Noboru Protocol")
    prompt = f"""
    You are Pragaman, a strategic sales architect at Noboru World.
    Your goal is to draft a hyper-personalized, peer-to-peer outreach sequence.
    
    Prospect Details:
    Name: {lead['first_name']} {lead['last_name']}
    Title: {lead['title']}
    Company: {lead['company']}
    Location: {lead['location']}
    LinkedIn URL: {lead['linkedin_url'] if lead['linkedin_url'] else "N/A"}
    Email: {lead['email'] if lead['email'] else "N/A"}
    Phone: {lead['phone'] if lead['phone'] else "N/A"}
    
    ### Noboru Protocol V2 Guidelines:
    1. **Inference First**: Based on their Title, infer their top 3 probable pain points.
    2. **Framework**: Use "Observation -> Problem -> Solution".
    3. **Tone**: Peer-to-peer, direct, low friction.
    4. **Missing Data**: 
       - If Email is "N/A", set "email_subject" and "email_body" to null.
       - If LinkedIn URL is "N/A", set "linkedin_note" to null.
       - If Phone is "N/A", set "whatsapp_nudge" to null.
    
    ### Deliverables (Only if data available):
    1. **Cold Email**: Subject (lowercase, 2-4 words) + Body (under 75 words).
    2. **LinkedIn Note**: Max 280 chars. Casual.
    3. **WhatsApp Nudge**: Extremely casual.
    
    Output JSON format:
    {{
        "email_subject": "...",
        "email_body": "...",
        "linkedin_note": "...",
        "whatsapp_nudge": "..."
    }}
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating draft for {lead['email']}: {e}")
        return None

def run_drafter():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch leads that need drafting (Status 'Enriched' or 'New')
    cursor.execute("SELECT * FROM leads WHERE status IN ('Enriched', 'New') AND draft_email_body IS NULL")
    leads = cursor.fetchall()
    
    print(f"Found {len(leads)} leads to draft.")
    
    for lead in leads:
        print(f"Drafting for {lead['first_name']} {lead['last_name']}...")
        drafts = generate_drafts(lead)
        
        if drafts:
            try:
                cursor.execute("""
                UPDATE leads 
                SET draft_email_subject = ?,
                    draft_email_body = ?,
                    draft_linkedin_note = ?,
                    draft_whatsapp_nudge = ?,
                    status = 'Pending_Approval',
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """, (
                    drafts.get('email_subject'),
                    drafts.get('email_body'),
                    drafts.get('linkedin_note'),
                    drafts.get('whatsapp_nudge'),
                    lead['id']
                ))
                conn.commit()
                print("Draft saved.")
            except sqlite3.Error as e:
                print(f"Database error: {e}")
        else:
            print("Skipping due to generation error.")
            
    conn.close()

if __name__ == "__main__":
    run_drafter()
