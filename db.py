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
        return firestore.Client.from_service_account_info(st.secrets["gcp_service_account"])
    except Exception as e:
        st.error(f"DB Connection Error: {e}")
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

# --- 2. LCIA MASTER FUNCTIONS ---
def create_new_case(case_name, claimant_email, respondent_email, access_pin="1234"):
    """Creates a new case. Only called by LCIA Admin."""
    case_id = f"LCIA-{int(datetime.now().timestamp())}"
    
    new_case_data = {
        "meta": {
            "case_id": case_id,
            "case_name": case_name,
            "created_at": datetime.now(),
            "status": "Phase 1: Initiation",
            "access_pin": access_pin,
            "parties": {"claimant": claimant_email, "respondent": respondent_email}
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
    
    if db:
        db.collection("arbitrations").document(case_id).set(new_case_data)
    return case_id

def get_all_cases_metadata():
    """Fetches a lightweight list of all cases for the LCIA Dashboard."""
    if not db: return []
    try:
        # We only get the 'meta' field to save bandwidth
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

# --- 3. PARTY ACCESS FUNCTIONS ---
def get_active_case_id():
    return st.session_state.get('active_case_id')

def verify_case_access(case_id, pin_attempt):
    """Checks if Case ID exists and PIN matches."""
    if not db: return False, None
    doc = db.collection("arbitrations").document(case_id).get()
    if doc.exists:
        data = doc.to_dict()
        stored_pin = data['meta'].get('access_pin', '')
        if stored_pin == pin_attempt:
            return True, data['meta']
    return False, None

# --- 4. STANDARD DATA LOADERS ---
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

# --- 5. CLOUD STORAGE & EMAIL ---
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
        except: pass

# --- 6. LEGACY COMPATIBILITY (FIXES THE CRASH) ---
def reset_database():
    """Dummy function to prevent import errors from old code."""
    pass
