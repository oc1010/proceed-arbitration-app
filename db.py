import streamlit as st
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- CONFIG ---
API_KEY = st.secrets.get("X_MASTER_KEY", "")
BIN_STRUCT = st.secrets.get("BIN_ID_STRUCT", "")
BIN_RESP = st.secrets.get("BIN_ID_RESP", "")
BIN_TIME = st.secrets.get("BIN_ID_TIME", "")

HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": API_KEY
}

# --- NOTIFICATION HANDLER ---
def send_email_notification(to_emails, subject, body):
    """
    1. Logs notification to 'notifications' bin for the in-app tab.
    2. Sends REAL professional email via SMTP.
    """
    # A. LOG TO DATABASE (IN-APP)
    try:
        # Load existing notifications
        full_data = load_complex_data()
        if "notifications" not in full_data: full_data["notifications"] = []
        
        # Determine roles based on context (simplified for logging)
        # We log it generally so it appears in the system
        new_note = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to_roles": ["Recipients"], # Generic label since we only have emails here
            "subject": subject,
            "body": body
        }
        full_data["notifications"].append(new_note)
        
        # Save back
        requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full_data, headers=HEADERS)
        load_complex_data.clear() # Clear cache
    except Exception as e:
        print(f"DB Log Failed: {e}")

    # B. SEND REAL EMAIL (Professional)
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

    # Professional Template Construction
    # We use a loop to send individually to ensure privacy and delivery of duplicates
    if smtp_user and smtp_pass and to_emails:
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                
                for recipient in to_emails:
                    if not recipient: continue
                    
                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = recipient
                    msg['Subject'] = f"[PROCEED] {subject}"
                    
                    # Professional Body
                    formatted_body = f"""
AUTOMATIC NOTIFICATION - PROCEED ARBITRATION PLATFORM
=====================================================

Subject: {subject}
Date: {datetime.now().strftime("%d %B %Y, %H:%M UTC")}

-----------------------------------------------------
MESSAGE:

{body}

-----------------------------------------------------

PLEASE DO NOT REPLY DIRECTLY TO THIS EMAIL.
This is an automated message. For any queries, please reach out to the Arbitrator directly or log in to the PROCEED platform.
"""
                    msg.attach(MIMEText(formatted_body, 'plain'))
                    server.send_message(msg)
            
            st.toast(f"📧 Notification sent to {len(to_emails)} recipient(s).", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Email Failed: {e}")
    else:
        print("Email skipped: Credentials missing or no recipients.")

# --- DATABASE FUNCTIONS ---
@st.cache_data(ttl=60)
def load_full_config():
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200: return resp.json().get('record', {})
    except: pass
    return {}

def load_structure(phase="phase2"):
    data = load_full_config()
    return data.get(phase, [])

def save_structure(new_questions, phase="phase2"):
    current = load_full_config()
    current[phase] = new_questions
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json=current, headers=HEADERS)
    load_full_config.clear()

@st.cache_data(ttl=2)
def load_responses(phase="phase2"):
    url = f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            data = resp.json().get('record')
            return data.get(phase, {"claimant": {}, "respondent": {}}) if data else {}
    except: pass
    return {"claimant": {}, "respondent": {}}

def save_responses(new_phase_data, phase="phase2"):
    try:
        resp = requests.get(f"https://api.jsonbin.io/v3/b/{BIN_RESP}/latest", headers=HEADERS)
        current = resp.json().get('record', {})
    except: current = {}
    current[phase] = new_phase_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json=current, headers=HEADERS)
    load_responses.clear()

@st.cache_data(ttl=2)
def load_complex_data():
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200: return resp.json().get('record', {})
    except: pass
    return {}

def save_complex_data(key, sub_data):
    full = load_complex_data()
    full[key] = sub_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full, headers=HEADERS)
    load_complex_data.clear()

def reset_database():
    empty_complex = {
        "timeline": [], "delays": [], "notifications": [],
        "doc_prod": {"claimant": [], "respondent": []}, 
        "costs": {"claimant_log": [], "respondent_log": [], "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, "app_tagging": []}
    }
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=empty_complex, headers=HEADERS)
    load_full_config.clear(); load_responses.clear(); load_complex_data.clear()
    return True
