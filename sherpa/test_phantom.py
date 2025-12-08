import requests
from config import PHANTOMBUSTER_API_KEY, LINKEDIN_SEARCH_EXPORT_AGENT_ID

def test_api():
    print(f"Testing API Key: {PHANTOMBUSTER_API_KEY[:5]}...")
    
    # 1. Check if we can list agents
    url = "https://api.phantombuster.com/api/v2/agents"
    headers = {"X-Phantombuster-Key": PHANTOMBUSTER_API_KEY}
    
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            agents = response.json()
            print("API Key is VALID.")
            print(f"Found {len(agents)} agents.")
            
            found = False
            for agent in agents:
                print(f"- {agent.get('name')} (ID: {agent.get('id')})")
                if str(agent.get('id')) == str(LINKEDIN_SEARCH_EXPORT_AGENT_ID):
                    found = True
            
            if found:
                print(f"\nAgent ID {LINKEDIN_SEARCH_EXPORT_AGENT_ID} FOUND in list.")
            else:
                print(f"\nAgent ID {LINKEDIN_SEARCH_EXPORT_AGENT_ID} NOT FOUND in list.")
                
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    test_api()
