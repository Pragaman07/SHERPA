import streamlit as st
import sqlite3
import pandas as pd
from config import DB_PATH

st.set_page_config(page_title="SHERPA Dashboard", layout="wide")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def load_pending_drafts():
    conn = get_db_connection()
    drafts = pd.read_sql_query("SELECT * FROM leads WHERE status = 'Pending_Approval'", conn)
    conn.close()
    return drafts

def approve_draft(lead_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = 'Approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()

def reject_draft(lead_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE leads SET status = 'Rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (lead_id,))
    conn.commit()
    conn.close()

def update_draft(lead_id, subject, body, li_note, wa_nudge):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE leads 
        SET draft_email_subject = ?, 
            draft_email_body = ?, 
            draft_linkedin_note = ?, 
            draft_whatsapp_nudge = ?,
            updated_at = CURRENT_TIMESTAMP 
        WHERE id = ?
    """, (subject, body, li_note, wa_nudge, lead_id))
    conn.commit()
    conn.close()

def add_manual_lead(first_name, last_name, email, phone, linkedin_url, company, title, location):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO leads (first_name, last_name, email, phone, linkedin_url, company, title, location, status, verification_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Enriched', 'Manual')
        """, (first_name, last_name, email, phone, linkedin_url, company, title, location))
        conn.commit()
        st.success(f"Lead {first_name} {last_name} added successfully! Run 'drafter.py' to generate content.")
    except sqlite3.IntegrityError:
        st.error("Error: A lead with this LinkedIn URL already exists.")
    except Exception as e:
        st.error(f"Database error: {e}")
from sender import run_sender
from drafter import run_drafter

# Sidebar Navigation
st.sidebar.title("🏔️ SHERPA")
page = st.sidebar.radio("Navigate", ["Approval Dashboard", "Lead Tracker", "Add Manual Lead", "Upload Leads", "AI Discovery"])

st.sidebar.markdown("---")

if st.sidebar.button("✨ Generate Drafts"):
    with st.spinner("Generating drafts with Gemini..."):
        try:
            run_drafter()
            st.sidebar.success("Drafts generated!")
            time.sleep(1) # Brief pause
            st.rerun() # Refresh to show new drafts
        except Exception as e:
            st.sidebar.error(f"Error generating drafts: {e}")

if st.sidebar.button("🚀 Send Approved Messages"):
    with st.spinner("Sending messages... Check the terminal for WhatsApp QR code if needed."):
        try:
            run_sender()
            st.sidebar.success("Outreach cycle completed!")
        except Exception as e:
            st.sidebar.error(f"Error during outreach: {e}")

if page == "Add Manual Lead":
    st.title("📝 Add Manual Lead")
    st.markdown("Enter prospect details below. The AI will pick this up for drafting.")
    
    with st.form("manual_lead_form"):
        col1, col2 = st.columns(2)
        with col1:
            first_name = st.text_input("First Name")
            email = st.text_input("Email")
            phone = st.text_input("Phone Number (with country code, e.g., +1...)")
            company = st.text_input("Company")
            linkedin_url = st.text_input("LinkedIn URL")
        with col2:
            last_name = st.text_input("Last Name")
            title = st.text_input("Title")
            location = st.text_input("Location")
        
        submitted = st.form_submit_button("Add Lead")
        
        if submitted:
            if first_name and (email or phone or linkedin_url):
                add_manual_lead(first_name, last_name, email, phone, linkedin_url, company, title, location)
            else:
                st.warning("Please fill in Name AND at least one contact method (Email, Phone, or LinkedIn).")

elif page == "Lead Tracker":
    st.title("📊 Lead Tracker")
    
    conn = get_db_connection()
    # Fetch all leads
    df = pd.read_sql_query("SELECT * FROM leads ORDER BY updated_at DESC", conn)
    conn.close()
    
    # Filters
    status_filter = st.multiselect("Filter by Status", options=df['status'].unique(), default=df['status'].unique())
    
    if not df.empty:
        filtered_df = df[df['status'].isin(status_filter)]
        st.dataframe(filtered_df[['first_name', 'last_name', 'company', 'title', 'status', 'email', 'phone', 'updated_at']], use_container_width=True)
        
        st.markdown("### Detailed View")
        selected_lead_id = st.selectbox("Select Lead to View Details", options=filtered_df['id'], format_func=lambda x: f"{filtered_df[filtered_df['id'] == x]['first_name'].values[0]} {filtered_df[filtered_df['id'] == x]['last_name'].values[0]}")
        
        if selected_lead_id:
            lead = filtered_df[filtered_df['id'] == selected_lead_id].iloc[0]
            st.write(f"**Name:** {lead['first_name']} {lead['last_name']}")
            st.write(f"**Company:** {lead['company']}")
            st.write(f"**Status:** {lead['status']}")
            st.write(f"**Email:** {lead['email']}")
            st.write(f"**Phone:** {lead['phone']}")
            st.text_area("Draft Email", value=lead['draft_email_body'] if lead['draft_email_body'] else "N/A", height=150, disabled=True)
            st.text_area("WhatsApp Nudge", value=lead['draft_whatsapp_nudge'] if lead['draft_whatsapp_nudge'] else "N/A", height=50, disabled=True)

elif page == "Upload Leads":
    st.title("📂 Upload Leads")
    st.markdown("Upload a CSV or Excel file with columns: `Name`, `Email`, `LinkedIn`, `Company`, `Title`, `Location`, `Phone`.")
    
    uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx'])
    
    if uploaded_file is not None:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.write("Preview:")
            st.dataframe(df.head())
            
            if st.button("Import Leads"):
                conn = get_db_connection()
                cursor = conn.cursor()
                success_count = 0
                error_count = 0
                
                progress_bar = st.progress(0)
                
                for index, row in df.iterrows():
                    # Smart Column Mapping
                    # Normalize column names to lowercase for matching
                    row_keys = {k.lower(): k for k in df.columns}
                    
                    def get_val(key_list):
                        for k in key_list:
                            if k in row_keys:
                                return row[row_keys[k]]
                        return ""

                    # Extract fields
                    first_name = ""
                    last_name = ""
                    
                    full_name = get_val(['name', 'full name', 'fullname'])
                    if full_name:
                        parts = str(full_name).split(' ', 1)
                        first_name = parts[0]
                        last_name = parts[1] if len(parts) > 1 else ""
                    else:
                        first_name = get_val(['first name', 'firstname', 'first_name'])
                        last_name = get_val(['last name', 'lastname', 'last_name'])
                        
                    email = get_val(['email', 'email address'])
                    linkedin = get_val(['linkedin', 'linkedin url', 'linkedin_url', 'profile'])
                    company = get_val(['company', 'company name'])
                    title = get_val(['title', 'job title', 'role'])
                    location = get_val(['location', 'city', 'country'])
                    phone = get_val(['phone', 'phone number', 'mobile'])

                    if first_name and (email or phone or linkedin):
                        try:
                            cursor.execute("""
                                INSERT INTO leads (first_name, last_name, email, phone, linkedin_url, company, title, location, status, verification_status)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Enriched', 'Manual')
                            """, (first_name, last_name, email, phone, linkedin, company, title, location))
                            success_count += 1
                        except sqlite3.IntegrityError:
                            error_count += 1 # Duplicate
                        except Exception as e:
                            st.error(f"Error importing row {index}: {e}")
                    else:
                        # Optional: Log skipped rows
                        pass
                    
                    progress_bar.progress((index + 1) / len(df))
                
                conn.commit()
                conn.close()
                st.success(f"Imported {success_count} leads successfully! ({error_count} duplicates skipped)")
                
        except Exception as e:
            st.error(f"Error processing file: {e}")

elif page == "AI Discovery":
    st.title("🧠 AI Lead Discovery")
    st.markdown("Ask Gemini to find leads for you. Example: *'Find 10 D2C skincare brands in India'*")
    
    prompt = st.text_area("Enter your request:", height=100)
    
    if st.button("🔍 Find Leads"):
        if not prompt:
            st.warning("Please enter a prompt.")
        else:
            with st.spinner("Consulting Gemini... (This may take a moment)"):
                try:
                    import google.generativeai as genai
                    import json
                    from config import GEMINI_API_KEY
                    
                    genai.configure(api_key=GEMINI_API_KEY)
                    model = genai.GenerativeModel('gemini-flash-latest')
                    
                    ai_query = f"""
                    You are a lead generation expert.
                    User Request: "{prompt}"
                    
                    Task: Generate a list of companies/leads that match this request.
                    Return ONLY a JSON array of objects. No markdown, no text.
                    
                    Fields required per object:
                    - first_name (Make up a plausible founder/CEO name if specific person not requested, or use "Founder")
                    - last_name
                    - company
                    - title (e.g. Founder, CEO)
                    - email (Make up a plausible pattern like info@domain.com or founder@domain.com if actual not known, mark as 'Unverified')
                    - phone (Use "N/A" if unknown)
                    - linkedin_url (Use company LinkedIn or "N/A")
                    - location
                    
                    JSON Structure:
                    [
                        {{
                            "first_name": "...",
                            "last_name": "...",
                            "company": "...",
                            "title": "...",
                            "email": "...",
                            "phone": "...",
                            "linkedin_url": "...",
                            "location": "..."
                        }}
                    ]
                    """
                    
                    response = model.generate_content(ai_query)
                    content = response.text.replace('```json', '').replace('```', '').strip()
                    leads_data = json.loads(content)
                    
                    if leads_data:
                        st.session_state['ai_leads'] = leads_data
                        st.success(f"Found {len(leads_data)} potential leads!")
                    else:
                        st.warning("AI returned no data.")
                        
                except Exception as e:
                    st.error(f"Error fetching leads: {e}")

    if 'ai_leads' in st.session_state:
        df_ai = pd.DataFrame(st.session_state['ai_leads'])
        st.dataframe(df_ai)
        
        if st.button("📥 Add All to Database"):
            conn = get_db_connection()
            cursor = conn.cursor()
            added = 0
            skipped = 0
            
            for lead in st.session_state['ai_leads']:
                try:
                    cursor.execute("""
                        INSERT INTO leads (first_name, last_name, email, phone, linkedin_url, company, title, location, status, verification_status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Enriched', 'AI_Generated')
                    """, (
                        lead.get('first_name', 'Founder'), 
                        lead.get('last_name', ''), 
                        lead.get('email', ''), 
                        lead.get('phone', ''), 
                        lead.get('linkedin_url', ''), 
                        lead.get('company', ''), 
                        lead.get('title', 'Founder'), 
                        lead.get('location', '')
                    ))
                    added += 1
                except sqlite3.IntegrityError:
                    skipped += 1
                except Exception as e:
                    st.error(f"Error adding {lead.get('company')}: {e}")
            
            conn.commit()
            conn.close()
            st.success(f"Added {added} leads to database! ({skipped} duplicates skipped)")
            del st.session_state['ai_leads'] # Clear after adding

elif page == "Approval Dashboard":
    st.title("✅ Approval Dashboard")

    drafts = load_pending_drafts()

    if drafts.empty:
        st.info("No drafts pending approval. Great job!")
    else:
        st.write(f"Found {len(drafts)} drafts pending review.")
        
        for index, row in drafts.iterrows():
            with st.expander(f"{row['first_name']} {row['last_name']} - {row['company']}", expanded=True):
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    st.subheader("Prospect Info")
                    st.write(f"**Title:** {row['title']}")
                    st.write(f"**Location:** {row['location']}")
                    st.write(f"**LinkedIn:** [{row['linkedin_url']}]({row['linkedin_url']})")
                    st.write(f"**Email:** {row['email']}")
                
                with col2:
                    st.subheader("Draft Content")
                    
                    with st.form(key=f"form_{row['id']}"):
                        subject = st.text_input("Email Subject", value=row['draft_email_subject'])
                        body = st.text_area("Email Body", value=row['draft_email_body'], height=200)
                        li_note = st.text_area("LinkedIn Note", value=row['draft_linkedin_note'], height=100)
                        wa_nudge = st.text_input("WhatsApp Nudge", value=row['draft_whatsapp_nudge'])
                        
                        c1, c2, c3 = st.columns(3)
                        with c1:
                            if st.form_submit_button("✅ Approve"):
                                update_draft(row['id'], subject, body, li_note, wa_nudge)
                                approve_draft(row['id'])
                                st.rerun()
                        with c2:
                            if st.form_submit_button("💾 Save Edits"):
                                update_draft(row['id'], subject, body, li_note, wa_nudge)
                                st.success("Draft updated.")
                        with c3:
                            if st.form_submit_button("❌ Reject"):
                                reject_draft(row['id'])
                                st.rerun()
