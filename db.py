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

# --- 0. HELPER: REAL EMAIL SENDER ---
def send_email_notification(to_emails, subject, body):
    """
    Sends a REAL email if ST_MAIL_USER and ST_MAIL_PASSWORD are in secrets.
    Otherwise, simulates it in the app.
    """
    # 1. App Notification
    st.toast(f"📧 Notification: {subject}", icon="📨")
    
    # 2. Real Email Logic
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    
    if smtp_user and smtp_pass and to_emails:
        try:
            msg = MIMEText(body)
            msg['Subject'] = f"[PROCEED] {subject}"
            msg['From'] = smtp_user
            msg['To'] = ", ".join(to_emails)

            # Example for Outlook/Office365. Change server for Gmail (smtp.gmail.com)
            with smtplib.SMTP('smtp.office365.com', 587) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
            print("Email sent successfully.")
        except Exception as e:
            print(f"Email failed: {e}")
    else:
        print("Email simulation: No SMTP credentials found in secrets.")

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

def get_release_status():
    data = load_full_config()
    return {
        "phase1": data.get("phase1_released", False),
        "phase2": data.get("phase2_released", False),
        "phase3": data.get("phase3_released", False),
        "phase4": data.get("phase4_released", True),
        "phase5": data.get("phase5_released", True)
    }

def save_structure(new_questions, phase="phase2"):
    current = load_full_config()
    current[phase] = new_questions
    requests.put(f"https://api.jsonbin.io/v3/b/{BIN_STRUCT}", json=current, headers=HEADERS)
    load_full_config.clear()

def set_release_status(phase, status=True):
    current = load_full_config()
    current[f"{phase}_released"] = status
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

# --- 3. COMPLEX DATA (Timeline, Docs, Costs) ---
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
