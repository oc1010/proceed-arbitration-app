import streamlit as st
import requests
import smtplib
from email.mime.text import MIMEText
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

# --- 0. CENTRAL NOTIFICATION HANDLER ---
def send_notification(to_roles, subject, body, to_emails=None):
    """
    1. Sends REAL email via SMTP.
    2. Logs notification to 'notifications' bin for the in-app tab.
    """
    # A. LOG TO DATABASE (IN-APP)
    try:
        # Load existing notifications
        full_data = load_complex_data()
        if "notifications" not in full_data: full_data["notifications"] = []
        
        # Add new entry
        new_note = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to_roles": to_roles, # list like ['claimant', 'respondent']
            "subject": subject,
            "body": body
        }
        full_data["notifications"].append(new_note)
        
        # Save back
        requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full_data, headers=HEADERS)
        load_complex_data.clear() # Clear cache to show immediately
    except Exception as e:
        print(f"DB Log Failed: {e}")

    # B. SEND REAL EMAIL
    # If explicit emails aren't provided, try to fetch from responses
    if not to_emails:
        to_emails = []
        p2 = load_responses("phase2")
        if 'claimant' in to_roles:
            c_mail = p2.get('claimant', {}).get('contact_email')
            if c_mail: to_emails.append(c_mail)
        if 'respondent' in to_roles:
            r_mail = p2.get('respondent', {}).get('contact_email')
            if r_mail: to_emails.append(r_mail)

    st.toast(f"🔔 In-App Notification Sent: {subject}")

    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

    if smtp_user and smtp_pass and to_emails:
        try:
            msg = MIMEText(body)
            msg['Subject'] = f"[PROCEED] {subject}"
            msg['From'] = smtp_user
            msg['To'] = ", ".join(to_emails)

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            
            st.toast(f"📧 Email Sent Successfully to {len(to_emails)} recipients.", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Email Failed: {e}") # Show this error to user for debugging
    else:
        print("Email skipped: Credentials missing or no recipients.")

# --- 1. CONFIGURATION ---
@st.cache_data(ttl=60)
def load_full_config():
    url = f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json().get('record', {})
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

# --- 2. RESPONSES ---
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

# --- 3. COMPLEX DATA ---
@st.cache_data(ttl=2)
def load_complex_data():
    url = f"https://api.jsonbin.io/v3/b/{BIN_TIME}/latest"
    try:
        resp = requests.get(url, headers=HEADERS)
        if resp.status_code == 200:
            return resp.json().get('record', {})
    except: pass
    return {}

def save_complex_data(key, sub_data):
    full = load_complex_data()
    full[key] = sub_data
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_TIME}", json=full, headers=HEADERS)
    load_complex_data.clear()

# --- 4. RESET ---
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
