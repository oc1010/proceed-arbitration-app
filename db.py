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
        # Attempts to get or create a specific bucket for this project
        bucket_name = f"{st.secrets['gcp_service_account']['project_id']}-files" 
        try:
            return storage_client.get_bucket(bucket_name)
        except:
            return storage_client.create_bucket(bucket_name)
    except Exception as e:
        return None

db = get_db()
bucket = get_storage_bucket()

# --- 2. CASE MANAGEMENT (THE NEW LOGIC) ---
def create_new_case(case_name, claimant_email, respondent_email):
    # Generates a unique Case ID
    case_id = f"LCIA-{int(datetime.now().timestamp())}"
    
    # Initialize the full case structure (matches your original JSONBin structure)
    new_case_data = {
        "meta": {
            "case_name": case_name,
            "created_at": datetime.now(),
            "status": "Phase 1: Initiation",
            "parties": {"claimant": claimant_email, "respondent": respondent_email}
        },
        # These lists will store the Questions
        "phase1": [], 
        "phase2": [],
        "phase1_released": False,
        "phase2_released": False,
        # This dict stores the Answers
        "responses": {"claimant": {}, "respondent": {}},
        # This dict stores the "Complex Data" (Timeline, Costs, Docs)
        "complex_data": {
            "timeline": [], 
            "delays": [], 
            "notifications": [],
            "doc_prod": {"claimant": [], "respondent": []}, 
            "costs": {
                "claimant_log": [], 
                "respondent_log": [], 
                "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, 
                "app_tagging": []
            }
        }
    }
    
    if db:
        db.collection("arbitrations").document(case_id).set(new_case_data)
    return case_id

def get_active_case_id():
    # Helper to get the ID from session state
    return st.session_state.get('active_case_id')

# --- 3. ADAPTER FUNCTIONS (COMPATIBLE WITH YOUR EXISTING PAGES) ---

def load_full_config():
    """Reads the entire case object from Firestore."""
    cid = get_active_case_id()
    if not cid or not db: return {}
    doc = db.collection("arbitrations").document(cid).get()
    return doc.to_dict() if doc.exists else {}

def load_structure(phase="phase2"):
    """Loads the question list for the specific phase."""
    data = load_full_config()
    return data.get(phase, [])

def save_structure(new_questions, phase="phase2"):
    """Saves edited questions back to Cloud."""
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
    """Loads answers. Note: Your original code split them by phase, 
       but here we store all in one 'responses' dict for simplicity 
       unless we need strictly separate fields."""
    data = load_full_config()
    full_responses = data.get("responses", {})
    # Return the whole object to ensure compatibility with your existing logic
    # that expects keys like 'claimant' and 'respondent' inside.
    return full_responses

def save_responses(all_resp, phase="phase2"):
    """Updates the answers."""
    cid = get_active_case_id()
    if cid and db:
        # We update the 'responses' field directly
        db.collection("arbitrations").document(cid).update({"responses": all_resp})

def load_complex_data():
    """Loads timeline, costs, etc."""
    data = load_full_config()
    return data.get("complex_data", {})

def save_complex_data(key, sub_data):
    """Saves specific complex data (e.g. key='timeline')"""
    cid = get_active_case_id()
    if cid and db:
        # Update using dot notation for nested fields
        db.collection("arbitrations").document(cid).update({f"complex_data.{key}": sub_data})

# --- 4. NEW FILE UPLOAD FUNCTION ---
def upload_file_to_cloud(uploaded_file):
    """Uploads a file to Google Cloud Storage and returns the public URL."""
    if not bucket or not uploaded_file: return None
    try:
        # Organize files by Case ID
        blob_name = f"{get_active_case_id()}/{uploaded_file.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_file(uploaded_file)
        # For private buckets, you might need to generate a signed URL
        # For hackathon demo simplicity, we return the name so we know it exists
        return blob.name 
    except Exception as e:
        st.error(f"Upload failed: {e}")
        return None

# --- 5. NOTIFICATIONS (UPDATED FOR CLOUD) ---
def send_email_notification(to_emails, subject, body):
    """
    1. Logs notification to Firestore (App Inbox).
    2. Sends REAL professional email via SMTP.
    """
    cid = get_active_case_id()
    
    # A. LOG TO DATABASE (IN-APP)
    if cid and db:
        try:
            new_note = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "to_roles": ["Recipients"], 
                "subject": subject,
                "body": body
            }
            # Firestore ArrayUnion adds the element to the list
            db.collection("arbitrations").document(cid).update({
                "complex_data.notifications": firestore.ArrayUnion([new_note])
            })
        except Exception as e:
            print(f"DB Log Failed: {e}")

    # B. SEND REAL EMAIL (SMTP)
    # (This part remains exactly the same as your original code)
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

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
                    formatted_body = f"""
AUTOMATIC NOTIFICATION - PROCEED ARBITRATION PLATFORM
=====================================================

Subject: {subject}
Date: {datetime.now().strftime("%d %B %Y, %H:%M UTC")}

-----------------------------------------------------
MESSAGE:

{body}

-----------------------------------------------------
"""
                    msg.attach(MIMEText(formatted_body, 'plain'))
                    server.send_message(msg)
            
            st.toast(f"📧 Notification sent to {len(to_emails)} recipient(s).", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Email Failed: {e}")
    else:
        print("Email skipped: Credentials missing or no recipients.")

def reset_database():
    """Legacy function - not needed for Multi-Case setup but kept to prevent import errors."""
    pass
