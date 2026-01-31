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
        return firestore.Client.from_service_account_info(
            st.secrets["gcp_service_account"], 
            database="proceed"
        )
    except Exception:
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
    except Exception:
        return None

db = get_db()
bucket = get_storage_bucket()

# --- 2. EMAIL HELPER ---
def send_email_via_smtp(to_list, subject, body):
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    
    if not smtp_user:
        gcp_sec = st.secrets.get("gcp_service_account", {})
        smtp_user = gcp_sec.get("ST_MAIL_USER")
        smtp_pass = gcp_sec.get("ST_MAIL_PASSWORD")

    if not smtp_user or not smtp_pass:
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
    except Exception as e:
        print(f"Email error: {e}")
        return False

# --- 3. LCIA MASTER FUNCTIONS ---
def create_new_case(case_name, claimant_email, respondent_email, arbitrator_email, setup_pin="1234"):
    case_id = f"LCIA-{int(datetime.now().timestamp())}"
    
    new_case_data = {
        "meta": {
            "case_id": case_id,
            "case_name": case_name,
            "created_at": datetime.now(),
            "status": "Phase 1: Initiation",
            "setup_pin": setup_pin,  # Used only for activation
            "parties": {
                "claimant": claimant_email.strip().lower(), 
                "respondent": respondent_email.strip().lower(),
                "arbitrator": arbitrator_email.strip().lower() if arbitrator_email else ""
            },
            # STORES PRIVATE PASSWORDS (None initially)
            "credentials": {
                "claimant": None,
                "respondent": None,
                "arbitrator": None
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
        
        recipients = [claimant_email, respondent_email, arbitrator_email]
        subject = f"Notice of Arbitration: {case_name}"
        body = f"""
        Strictly Confidential
        
        The LCIA has registered a new arbitration matter: {case_name}.
        
        STEP 1: ACTIVATE YOUR ACCOUNT
        -----------------------------
        1. Go to https://proceedai.streamlit.app/
        2. Select the "Activate Account" tab.
        3. Enter Case ID: {case_id}
        4. Enter your Email and the Setup PIN: {setup_pin}
        5. Create your own private password.
        
        Regards,
        LCIA Registrar
        """
        email_success = send_email_via_smtp(recipients, subject, body)
        
    return case_id, email_success

def get_all_cases_metadata():
    if not db: return []
    try:
        docs = db.collection("arbitrations").stream()
        cases_list = []
        for doc in docs:
            d = doc.to_dict()
            if 'meta' in d:
                cases_list.append(d['meta'])
        return cases_list
    except Exception:
        return []

# --- 4. SECURE AUTHENTICATION FLOW ---
def get_active_case_id():
    return st.session_state.get('active_case_id')

def activate_user_account(case_id, email, input_setup_pin, new_password):
    """
    Registers a user by letting them set a password IF they have the Setup PIN.
    """
    if not db: return False, "DB Error"
    
    doc_ref = db.collection("arbitrations").document(case_id)
    doc = doc_ref.get()
    
    if not doc.exists: return False, "Case ID not found."
    
    data = doc.to_dict()
    meta = data.get('meta', {})
    
    # 1. Validate Setup PIN
    if meta.get('setup_pin') != input_setup_pin:
        return False, "Invalid Setup PIN."
        
    # 2. Identify Role by Email
    user_role = None
    input_email = email.strip().lower()
    for role, stored_email in meta.get('parties', {}).items():
        if stored_email == input_email:
            user_role = role
            break
            
    if not user_role:
        return False, "This email is not associated with this case."
        
    # 3. Check if already registered
    if meta.get('credentials', {}).get(user_role):
        return False, "Account already activated. Please go to Login."
        
    # 4. Save New Password
    # Note: In production, hash this password. For hackathon, storing plain is acceptable demo practice.
    db.collection("arbitrations").document(case_id).update({
        f"meta.credentials.{user_role}": new_password
    })
    
    return True, f"Account activated for {user_role.title()}!"

def login_user(case_id, email, password):
    """
    Logs in a user using their PRIVATE password.
    """
    if not db: return False, "DB Error", None, None
    
    doc = db.collection("arbitrations").document(case_id).get()
    if not doc.exists: return False, "Case ID not found.", None, None
    
    data = doc.to_dict()
    meta = data.get('meta', {})
    
    # 1. Identify Role
    user_role = None
    input_email = email.strip().lower()
    for role, stored_email in meta.get('parties', {}).items():
        if stored_email == input_email:
            user_role = role
            break
            
    if not user_role:
        return False, "Email not found in this case.", None, None
        
    # 2. Check Password
    stored_password = meta.get('credentials', {}).get(user_role)
    
    if not stored_password:
        return False, "Account not activated yet. Use the 'Activate Account' tab first.", None, None
        
    if stored_password != password:
        return False, "Incorrect Password.", None, None
        
    return True, "Success", user_role, meta

# --- 5. STANDARD LOADERS ---
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
    except Exception:
        return None

def send_email_notification(to_emails, subject, body):
    cid = get_active_case_id()
    if cid and db:
        try:
            new_note = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "to_roles": ["Recipients"], "subject": subject, "body": body}
            db.collection("arbitrations").document(cid).update({"complex_data.notifications": firestore.ArrayUnion([new_note])})
            send_email_via_smtp(to_emails, subject, body)
        except: pass

def reset_database(): pass
