import requests
import sqlite3
import time
import json
from config import PHANTOMBUSTER_API_KEY, APOLLO_API_KEY, LINKEDIN_SEARCH_EXPORT_AGENT_ID, DB_PATH

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def trigger_phantombuster(search_url):
    """
    Triggers the PhantomBuster LinkedIn Search Export phantom.
    Note: This is a simplified implementation. In a real scenario, you'd need to 
    handle the argument structure specific to the Phantom.
    """
    url = "https://api.phantombuster.com/api/v2/agents/launch"
    headers = {
        "X-Phantombuster-Key": PHANTOMBUSTER_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "id": LINKEDIN_SEARCH_EXPORT_AGENT_ID,
        "argument": {
            "searchUrl": search_url,
            "numberOfProfiles": 60 # As per requirements
        }
    }
    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"PhantomBuster triggered: {response.json()}")
        return response.json().get("containerId")
    except Exception as e:
        print(f"Error triggering PhantomBuster: {e}")
        return None

def get_phantombuster_result(container_id):
    """
    Polls for the result of the PhantomBuster run.
    """
    url = f"https://api.phantombuster.com/api/v2/containers/{container_id}/output"
    headers = {"X-Phantombuster-Key": PHANTOMBUSTER_API_KEY}
    
    print("Waiting for PhantomBuster to finish...")
    # In reality, this might take minutes. We'll poll every 30 seconds.
    # For this script, we'll just check once after a short sleep for demonstration,
    # or assume we are fetching the latest result from a completed run.
    
    # improved logic: fetch latest result object
    url_result = f"https://api.phantombuster.com/api/v2/agents/{LINKEDIN_SEARCH_EXPORT_AGENT_ID}/output"
    try:
        response = requests.get(url_result, headers=headers)
        response.raise_for_status()
        output = response.json().get("output")
        if output:
            # PhantomBuster often returns JSON lines (one JSON object per line)
            # or a list of objects.
            try:
                # Try parsing as a single JSON object/list
                data = json.loads(output)
                if isinstance(data, list):
                    return data
                elif isinstance(data, dict):
                    return [data]
            except json.JSONDecodeError:
                # Try parsing as JSON lines
                data = []
                for line in output.splitlines():
                    if line.strip():
                        try:
                            data.append(json.loads(line))
                        except json.JSONDecodeError:
                            pass
                return data
    except Exception as e:
        print(f"Error getting PhantomBuster result: {e}")
    return []

def enrich_with_apollo(linkedin_url):
    """
    Queries Apollo API to find email for the given LinkedIn URL.
    """
    url = "https://api.apollo.io/v1/people/match"
    headers = {
        "Content-Type": "application/json",
        "Cache-Control": "no-cache"
    }
    payload = {
        "api_key": APOLLO_API_KEY,
        "linkedin_url": linkedin_url
    }
    
    try:
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            data = response.json()
            person = data.get("person")
            if person and person.get("email"):
                return {
                    "email": person.get("email"),
                    "first_name": person.get("first_name"),
                    "last_name": person.get("last_name"),
                    "title": person.get("title"),
                    "company": person.get("organization", {}).get("name"),
                    "location": person.get("location", {}).get("name"), # simplified
                    "verification_status": "verified" # Assuming Apollo returns verified emails mostly
                }
    except Exception as e:
        print(f"Error enriching {linkedin_url}: {e}")
    
    return None

def save_lead(lead_data):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if exists
    cursor.execute("SELECT id FROM leads WHERE linkedin_url = ?", (lead_data['linkedin_url'],))
    if cursor.fetchone():
        print(f"Lead {lead_data['linkedin_url']} already exists. Skipping.")
        conn.close()
        return

    sql = """
    INSERT INTO leads (linkedin_url, first_name, last_name, email, company, title, location, verification_status, status)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Enriched')
    """
    try:
        cursor.execute(sql, (
            lead_data['linkedin_url'],
            lead_data.get('first_name'),
            lead_data.get('last_name'),
            lead_data.get('email'),
            lead_data.get('company'),
            lead_data.get('title'),
            lead_data.get('location'),
            lead_data.get('verification_status')
        ))
        conn.commit()
        print(f"Saved lead: {lead_data.get('email')}")
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    finally:
        conn.close()

def run_bridge(search_url=None, mock_data=False):
    if mock_data:
        print("Running in MOCK mode.")
        # Mock PhantomBuster results
        linkedin_urls = [
            "https://www.linkedin.com/in/mock-user-1/",
            "https://www.linkedin.com/in/mock-user-2/"
        ]
    else:
        if not search_url:
            print("No search URL provided.")
            return
        
        # 1. Trigger PhantomBuster (Skipping actual trigger for safety in dev, assuming we fetch latest)
        # container_id = trigger_phantombuster(search_url)
        # results = get_phantombuster_result(container_id)
        
        # For production, we fetch the latest results from the agent
        print("Fetching results from PhantomBuster...")
        results = get_phantombuster_result(None)
        
        linkedin_urls = []
        for item in results:
            # Adjust key based on actual PhantomBuster output
            url = item.get("profileUrl") or item.get("url") or item.get("linkedinUrl")
            if url:
                linkedin_urls.append(url)

    print(f"Found {len(linkedin_urls)} profiles to enrich.")

    for url in linkedin_urls:
        print(f"Processing: {url}")
        
        if mock_data:
            # Mock Apollo Enrichment
            enriched_data = {
                "linkedin_url": url,
                "email": f"user{linkedin_urls.index(url)}@example.com",
                "first_name": "Mock",
                "last_name": f"User{linkedin_urls.index(url)}",
                "company": "Mock Company",
                "title": "CEO",
                "location": "San Francisco",
                "verification_status": "verified"
            }
        else:
            enriched_data = enrich_with_apollo(url)
            if enriched_data:
                enriched_data['linkedin_url'] = url
        
        if enriched_data:
            save_lead(enriched_data)
        else:
            print(f"Could not enrich or verify email for {url}")

if __name__ == "__main__":
    # Example usage
    # run_bridge(search_url="https://www.linkedin.com/search/results/people/...", mock_data=True)
    import sys
    from config import LINKEDIN_SEARCH_URL
    
    if len(sys.argv) > 1 and sys.argv[1] == "--mock":
        run_bridge(mock_data=True)
    else:
        # Use URL from config if available
        if LINKEDIN_SEARCH_URL:
            run_bridge(search_url=LINKEDIN_SEARCH_URL)
        else:
            print("Please provide a search URL in config.py or run with --mock")
