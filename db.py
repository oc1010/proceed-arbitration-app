import streamlit as st
from google.cloud import firestore
from google.cloud import storage
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 1. CONNECT TO GOOGLE CLOUD ---
@st.cache_resource
def get_db():
    try:
        # Tries to connect to the "proceed" database you created
        return firestore.Client.from_service_account_info(
            st.secrets["gcp_service_account"], 
            database="proceed"
        )
    except Exception as e:
        # Fallback to default if "proceed" database isn't found
        try:
            return firestore.Client.from_service_account_info(st.secrets["gcp_service_account"])
        except Exception as e2:
            st.error(f"DB Connection Error: {e2}")
            return None

@st.cache_resource
def get_storage_bucket():
    try:
        storage_client = storage.Client.from_service_account_info(st.secrets["gcp_service_account"])
        bucket_name = f"{st.secrets['gcp_service_account']['project_id']}-files"
        try:
            return storage_client.get_bucket(bucket_name)
        except:
            return storage_client.create_bucket(bucket_name)
    except Exception as e:
        return None

db = get_db()
bucket = get_storage_bucket()

# --- 2. EMAIL HELPER (WITH DEBUGGING) ---
def send_email_via_smtp(to_list, subject, body):
    """Sends a real email and reports errors to the UI."""
    # Robust credential fetching (checks top-level AND nested)
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    
    if not smtp_user:
        # Try finding it inside the gcp block just in case
        gcp_sec = st.secrets.get("gcp_service_account", {})
        smtp_user = gcp_sec.get("ST_MAIL_USER")
        smtp_pass = gcp_sec.get("ST_MAIL_PASSWORD")

    if not smtp_user or not smtp_pass:
        st.warning("⚠️ Email not sent: ST_MAIL_USER or ST_MAIL_PASSWORD missing in secrets.")
        return False

    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            
            for recipient in to_list:
                if not recipient: continue
                msg = MIMEMultipart()
                msg['From'] = smtp_user
                msg['To'] = recipient
                msg['Subject'] = f"[PROCEED] {subject}"
                msg.attach(MIMEText(body, 'plain'))
                server.send_message(msg)
        return True
    except smtplib.SMTPAuthenticationError:
        st.error("❌ Email Failed: Authentication Error. Check your App Password.")
        return False
    except Exception as e:
        st.error(f"❌ Email Failed: {e}")
        return False

# --- 3. LCIA MASTER FUNCTIONS ---
def create_new_case(case_name, claimant_email, respondent_email, arbitrator_email, access_pin="1234"):
    """Creates a new case and notifies parties. Returns (ID, Email_Success_Bool)."""
    case_id = f"LCIA-{int(datetime.now().timestamp())}"
    
    new_case_data = {
        "meta": {
            "case_id": case_id,
            "case_name": case_name,
            "created_at": datetime.now(),
            "status": "Phase 1: Initiation",
            "access_pin": access_pin,
            "parties": {
                "claimant": claimant_email, 
                "respondent": respondent_email,
                "arbitrator": arbitrator_email
            }
        },
        "phase1": [], 
        "phase2": [],
        "phase1_released": False,
        "phase2_released": False,
        "responses": {},
        "complex_data": {
            "timeline": [], "delays": [], "notifications": [],
            "doc_prod": {"claimant": [], "respondent": []}, 
            "costs": {"claimant_log": [], "respondent_log": [], "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, "app_tagging": []}
        }
    }
    
    email_success = False
    if db:
        db.collection("arbitrations").document(case_id).set(new_case_data)
        
        # SEND WELCOME EMAIL
        recipients = [claimant_email, respondent_email, arbitrator_email]
        subject = f"Notice of Arbitration: {case_name}"
        body = f"""
        Strictly Confidential
        
        The LCIA has registered a new arbitration matter: {case_name}.
        
        ACCESS CREDENTIALS:
        -------------------
        Case ID: {case_id}
        Access PIN: {access_pin}
        
        Please log in at: https://proceedai.streamlit.app/
        
        Regards,
        LCIA Registrar
        """
        email_success = send_email_via_smtp(recipients, subject, body)
        
    return case_id, email_success

def get_all_cases_metadata():
    """Fetches a list of all cases for the LCIA Dashboard."""
    if not db: return []
    try:
        docs = db.collection("arbitrations").stream()
        cases_list = []
        for doc in docs:
            d = doc.to_dict()
            if 'meta' in d:
                cases_list.append(d['meta'])
        return cases_list
    except Exception as e:
        st.error(f"Error fetching case list: {e}")
        return []

# --- 4. PARTY ACCESS FUNCTIONS ---
def get_active_case_id():
    return st.session_state.get('active_case_id')

def verify_case_access(case_id, pin_attempt):
    if not db: return False, None
    doc = db.collection("arbitrations").document(case_id).get()
    if doc.exists:
        data = doc.to_dict()
        stored_pin = data['meta'].get('access_pin', '')
        if stored_pin == pin_attempt:
            return True, data['meta']
    return False, None

# --- 5. STANDARD DATA LOADERS ---
def load_full_config():
    cid = get_active_case_id()
    if not cid or not db: return {}
    doc = db.collection("arbitrations").document(cid).get()
    return doc.to_dict() if doc.exists else {}

def load_structure(phase="phase2"):
    data = load_full_config()
    return data.get(phase, [])

def save_structure(new_questions, phase="phase2"):
    cid = get_active_case_id()
    if cid and db:
        db.collection("arbitrations").document(cid).update({phase: new_questions})

def get_release_status():
    data = load_full_config()
    return {
        "phase1": data.get("phase1_released", False),
        "phase2": data.get("phase2_released", False)
    }

def set_release_status(phase, status=True):
    cid = get_active_case_id()
    if cid and db:
        db.collection("arbitrations").document(cid).update({f"{phase}_released": status})

def load_responses(phase="phase2"):
    data = load_full_config()
    return data.get("responses", {})

def save_responses(all_resp, phase="phase2"):
    cid = get_active_case_id()
    if cid and db:
        db.collection("arbitrations").document(cid).update({"responses": all_resp})

def load_complex_data():
    data = load_full_config()
    return data.get("complex_data", {})

def save_complex_data(key, sub_data):
    cid = get_active_case_id()
    if cid and db:
        db.collection("arbitrations").document(cid).update({f"complex_data.{key}": sub_data})

def upload_file_to_cloud(uploaded_file):
    if not bucket or not uploaded_file: return None
    try:
        blob_name = f"{get_active_case_id()}/{uploaded_file.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file)
        return blob.name 
    except Exception as e:
        return None

def send_email_notification(to_emails, subject, body):
    cid = get_active_case_id()
    if cid and db:
        try:
            new_note = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "to_roles": ["Recipients"], "subject": subject, "body": body}
            db.collection("arbitrations").document(cid).update({"complex_data.notifications": firestore.ArrayUnion([new_note])})
            send_email_via_smtp(to_emails, subject, body)
        except: pass
