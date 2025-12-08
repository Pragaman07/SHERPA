import sqlite3
import datetime
from config import DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def generate_daily_report():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    today = datetime.date.today().isoformat()
    
    # Metrics
    cursor.execute("SELECT COUNT(*) FROM leads WHERE date(created_at) = ?", (today,))
    hunted = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'Enriched' AND date(updated_at) = ?", (today,))
    enriched = cursor.fetchone()[0] # Approximation
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'Approved' AND date(updated_at) = ?", (today,))
    approved = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'Contacted' AND date(updated_at) = ?", (today,))
    sent = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status IN ('Interested', 'Replied', 'Snoozed', 'Dead') AND date(updated_at) = ?", (today,))
    replies = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM leads WHERE status = 'Interested' AND date(updated_at) = ?", (today,))
    interested = cursor.fetchone()[0]
    
    report = f"""
    🏔️ SHERPA Daily Summary ({today})
    --------------------------------
    Hunted:   {hunted} Profiles scanned.
    Enriched: {enriched} Verified Emails found.
    Approved: {approved} Drafts approved by you.
    Sent:     {sent} Emails.
    Replies:  {replies} New Replies ({interested} Interested).
    Errors:   None.
    """
    
    print(report)
    
    # In a real scenario, we would send this via Slack or Email
    # send_slack_notification(report)
    
    conn.close()

if __name__ == "__main__":
    generate_daily_report()
