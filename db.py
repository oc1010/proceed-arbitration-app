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

# --- CENTRAL NOTIFICATION HANDLER ---
def send_notification(to_roles, subject, body, to_emails=None):
    """
    Sends a professional email and logs the notification in the app.
    """
    # 1. LOG TO DATABASE (IN-APP)
    try:
        full_data = load_complex_data()
        if "notifications" not in full_data: full_data["notifications"] = []
        
        new_note = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to_roles": to_roles, 
            "subject": subject,
            "body": body
        }
        full_data["notifications"].append(new_note)
        requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full_data, headers=HEADERS)
        load_complex_data.clear()
    except Exception as e:
        print(f"DB Log Failed: {e}")

    # 2. RESOLVE EMAILS
    if not to_emails:
        to_emails = []
        p2 = load_responses("phase2")
        # Check roles and fetch emails
        if 'claimant' in to_roles:
            val = p2.get('claimant', {}).get('contact_email')
            if val: to_emails.append(val)
        if 'respondent' in to_roles:
            val = p2.get('respondent', {}).get('contact_email')
            if val: to_emails.append(val)
        
        # Remove duplicates to avoid spamming the same inbox multiple times
        to_emails = list(set(to_emails))

    # 3. CONSTRUCT PROFESSIONAL EMAIL
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

    # Professional Template
    full_body = f"""
    [AUTOMATIC NOTIFICATION - PROCEED ARBITRATION PLATFORM]
    
    Subject: {subject}
    
    -------------------------------------------------------
    {body}
    -------------------------------------------------------
    
    PLEASE DO NOT REPLY DIRECTLY TO THIS EMAIL.
    For any queries, please reach out to the Arbitrator directly or log in to the PROCEED platform.
    """

    if smtp_user and smtp_pass and to_emails:
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                
                # Send individually to ensure delivery even if emails are identical or Bcc issues arise
                for recipient in to_emails:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = recipient
                    msg['Subject'] = f"[PROCEED] {subject}"
                    msg.attach(MIMEText(full_body, 'plain'))
                    server.send_message(msg)
            
            st.toast(f"📧 Notification sent to {len(to_emails)} recipient(s).", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Email Error: {e}")
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
        "timeline": [], 
        "delays": [],
        "notifications": [],
        "doc_prod": {"claimant": [], "respondent": []}, 
        "costs": {"claimant_log": [], "respondent_log": [], "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, "app_tagging": []}
    }
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_RESP}", json={"initial_setup": True}, headers=HEADERS)
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=empty_complex, headers=HEADERS)
    load_full_config.clear()
    load_responses.clear()
    load_complex_data.clear()
    return True
