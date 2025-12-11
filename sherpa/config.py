import streamlit as st
import os

# Default Values
PHANTOMBUSTER_API_KEY = None
APOLLO_API_KEY = None
GEMINI_API_KEY = None
PHANTOMBUSTER_AGENT_ID = None
LINKEDIN_CONNECTION_AGENT_ID = None
DB_PATH = "leads.db"
DAILY_LEAD_LIMIT = 50
LINKEDIN_SEARCH_URL = "https://www.linkedin.com/search/results/people/?keywords=founder&origin=SWITCH_SEARCH_VERTICAL"

# 1. Try loading from local config (for local development)
try:
    from .config_local import *
except ImportError:
    pass

# 2. Override with Streamlit Secrets (for Cloud Deployment)
# Secrets are accessed via st.secrets dict
def load_secret(key, current_value):
    if key in st.secrets:
        return st.secrets[key]
    return current_value

PHANTOMBUSTER_API_KEY = load_secret("PHANTOMBUSTER_API_KEY", PHANTOMBUSTER_API_KEY)
APOLLO_API_KEY = load_secret("APOLLO_API_KEY", APOLLO_API_KEY)
GEMINI_API_KEY = load_secret("GEMINI_API_KEY", GEMINI_API_KEY)
PHANTOMBUSTER_AGENT_ID = load_secret("PHANTOMBUSTER_AGENT_ID", PHANTOMBUSTER_AGENT_ID)
LINKEDIN_CONNECTION_AGENT_ID = load_secret("LINKEDIN_CONNECTION_AGENT_ID", LINKEDIN_CONNECTION_AGENT_ID)
