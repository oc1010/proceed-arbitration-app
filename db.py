import streamlit as st
from google.cloud import firestore
from google.cloud import storage
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 1. CONNECT TO GOOGLE CLOUD ---
# We use the secrets you pasted into Streamlit Dashboard
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
        # Create a client
        storage_client = storage.Client.from_service_account_info(st.secrets["gcp_service_account"])
        # You need to create a bucket named 'proceed-files' in Google Cloud Console or change this name
        bucket_name = f"{st.secrets['gcp_service_account']['project_id']}-files" 
        try:
            return storage_client.get_bucket(bucket_name)
        except:
            # Auto-create if not exists
            return storage_client.create_bucket(bucket_name)
    except Exception as e:
        return None

db = get_db()
bucket = get_storage_bucket()

# --- 2. CASE MANAGEMENT (THE NEW LOGIC) ---
def create_new_case(case_name, claimant_email, respondent_email):
    case_id = f"LCIA-{int(datetime.now().timestamp())}"
    
    # Defaults from your original code
    from pages._defaults import DEFAULTS_PHASE_1, DEFAULTS_PHASE_2 # We will handle this in a sec
    
    new_case_data = {
        "meta": {
            "case_name": case_name,
            "created_at": datetime.now(),
            "status": "Phase 1: Initiation",
            "parties": {"claimant": claimant_email, "respondent": respondent_email}
        },
        "phase1": [], # Will be filled with defaults on load if empty
        "phase2": [],
        "phase1_released": False,
        "phase2_released": False,
        "responses": {"claimant": {}, "respondent": {}},
        "complex_data": {
            "timeline": [], "delays": [], "notifications": [],
            "doc_prod": {"claimant": [], "respondent": []}, 
            "costs": {"claimant_log": [], "respondent_log": [], "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, "app_tagging": []}
        }
    }
    db.collection("arbitrations").document(case_id).set(new_case_data)
    return case_id

def get_active_case_id():
    # Helper to get the ID from session state
    return st.session_state.get('active_case_id')

# --- 3. ADAPTER FUNCTIONS (KEEPING YOUR OLD NAMES) ---

def load_full_config():
    """Reads the entire case object."""
    cid = get_active_case_id()
    if not cid: return {}
    doc = db.collection("arbitrations").document(cid).get()
    return doc.to_dict() if doc.exists else {}

def load_structure(phase="phase2"):
    data = load_full_config()
    # Return saved structure OR empty list (pages will handle defaults)
    return data.get(phase, [])

def save_structure(new_questions, phase="phase2"):
    cid = get_active_case_id()
    if cid:
        db.collection("arbitrations").document(cid).update({phase: new_questions})

def get_release_status():
    data = load_full_config()
    return {
        "phase1": data.get("phase1_released", False),
        "phase2": data.get("phase2_released", False)
    }

def set_release_status(phase, status=True):
    cid = get_active_case_id()
    if cid:
        db.collection("arbitrations").document(cid).update({f"{phase}_released": status})

def load_responses(phase="phase2"):
    data = load_full_config()
    # Your code expects {"claimant": {}, "respondent": {}}
    responses = data.get("responses", {})
    # If the database stores all responses in one big dict, we return that
    # Or if you separated them by phase. For simplicity, let's return the whole response object
    # Your original code separated them. Let's stick to a unified 'responses' object for now.
    return responses

def save_responses(all_resp, phase="phase2"):
    cid = get_active_case_id()
    if cid:
        # We update the whole response object
        db.collection("arbitrations").document(cid).update({"responses": all_resp})

def load_complex_data():
    data = load_full_config()
    return data.get("complex_data", {})

def save_complex_data(key, sub_data):
    # key is 'timeline', 'costs', etc.
    cid = get_active_case_id()
    if cid:
        # Firestore allows updating nested fields using dot notation
        db.collection("arbitrations").document(cid).update({f"complex_data.{key}": sub_data})

# --- 4. NEW FILE UPLOAD FUNCTION ---
def upload_file_to_cloud(uploaded_file):
    """Uploads a file to Google Cloud Storage and returns the public URL."""
    if not bucket or not uploaded_file: return None
    try:
        blob_name = f"{get_active_case_id()}/{uploaded_file.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file)
        return blob.public_url # or blob.name if you want to keep it private
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# --- 5. NOTIFICATIONS (UNCHANGED LOGIC) ---
def send_email_notification(to_emails, subject, body):
    # Log to DB
    cid = get_active_case_id()
    if cid:
        note = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to_roles": ["Recipients"], "subject": subject, "body": body
        }
        # Atomic array update
        db.collection("arbitrations").document(cid).update({
            "complex_data.notifications": firestore.ArrayUnion([note])
        })

    # Send Real Email (SMTP) - Keep your existing logic here
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    if smtp_user and smtp_pass:
        # ... (Your existing SMTP code goes here) ...
        pass
