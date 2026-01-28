import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data

# --- PAGE SETUP ---
st.set_page_config(page_title="Document Production", layout="wide")

# --- AUTH & SESSION STATE ---
if 'doc_view_mode' not in st.session_state: st.session_state['doc_view_mode'] = 'list' 
if 'active_req_idx' not in st.session_state: st.session_state['active_req_idx'] = None
if 'active_party_list' not in st.session_state: st.session_state['active_party_list'] = 'claimant'
if 'active_form_type' not in st.session_state: st.session_state['active_form_type'] = None

role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
        st.switch_page("main.py")

# --- LOAD DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})

# --- CONSTANTS (From Requirements) ---
CATEGORIES = [
    "(a) General Contractual Documents",
    "(b) Technical & Project-Specific",
    "(c) Financial Documents",
    "(d) Company and Employee Data",
    "(e) Electronic Metadata",
    "(f) Other Documents"
]
URGENCY_LEVELS = ["(a) Low", "(b) Medium", "(c) High [Tribunal Priority]"]
YES_NO_OPTS = ["(a) Yes", "(b) No"]
DETERMINATION_OPTS = ["Allowed", "Allowed in Part", "Denied", "Reserved"]

# --- HELPER FUNCTIONS ---
def save_current_data():
    save_complex_data("doc_prod", doc_prod)

def navigate_to(mode, idx=None, form_type=None):
    st.session_state['doc_view_mode'] = mode
    if idx is not None: st.session_state['active_req_idx'] = idx
    if form_type is not None: st.session_state['active_form_type'] = form_type
    st.rerun()

def get_active_list():
    return doc_prod.get(st.session_state['active_party_list'], [])

def get_active_request():
    lst = get_active_list()
    idx = st.session_state['active_req_idx']
    if idx is not None and 0 <= idx < len(lst):
        return lst[idx]
    return {}

# --- VIEW 1: DASHBOARD (LIST VIEW) ---
if st.session_state['doc_view_mode'] == 'list':
    st.title("📂 Document Production Management")
    
    # 1. TABS for Parties
    tab_c, tab_r = st.tabs(["Claimant's Requests", "Respondent's Requests"])
    
    # Logic to set active list based on tab selection is tricky in Streamlit (tabs don't return value).
    # Instead, we render the content inside the tabs.
    
    def render_request_list(party_key):
        request_list = doc_prod[party_key]
        
        # New Request Button (Only for Owner)
        if role == party_key:
            if st.button(f"➕ New Request ({party_key.title()})", key=f"btn_new_{party_key}"):
                new_req = {
                    "req_no": f"Req-{len(request_list)+1}",
                    "category": CATEGORIES[0],
                    "date_req": str(date.today()),
                    "urgency": URGENCY_LEVELS[1],
                    "desc": "New Request...",
                    # Sub-objects
                    "objection": {}, 
                    "reply": {}, 
                    "determination": {}
                }
                doc_prod[party_key].append(new_req)
                save_current_data()
                st.rerun()

        if not request_list:
            st.info("No requests yet.")
            return

        # Header Row
        c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 3, 2])
        c1.markdown("**Req No.**")
        c2.markdown("**Category**")
        c3.markdown("**Urgency**")
        c4.markdown("**Status**")
        c5.markdown("**Action**")
        st.divider()

        for i, req in enumerate(request_list):
            c1, c2, c3, c4, c5 = st.columns([1, 2, 2, 3, 2])
            
            # Display Data
            c1.write(req.get('req_no', '-'))
            c2.caption(req.get('category', '').split(' ')[0] + "...") # Shorten
            
            # Urgency Styling
            urg = req.get('urgency', '')
            if "High" in urg: c3.error("High")
            elif "Medium" in urg: c3.warning("Medium")
            else: c3.success("Low")
            
            # Rich Status Info
            det = req.get('determination', {}).get('decision')
            obj = req.get('objection', {}).get('is_objected')
            
            if det:
                c4.info(f"⚖️ **{det}**") # Shows exact ruling
            elif obj == "(a) Yes":
                c4.warning("⚠️ Objected")
            else:
                c4.caption("⏳ Pending")

            if c5.button("Manage", key=f"mng_{party_key}_{i}"):
                st.session_state['active_party_list'] = party_key
                navigate_to('details', i)
            
            st.divider()

    with tab_c:
        render_request_list("claimant")
    with tab_r:
        render_request_list("respondent")


# --- VIEW 2: THE 4-STAGE HUB ---
elif st.session_state['doc_view_mode'] == 'details':
    req = get_active_request()
    idx = st.session_state['active_req_idx']
    
    st.button("⬅️ Back to List", on_click=lambda: navigate_to('list'))
    st.divider()
    
    st.subheader(f"Managing: {req.get('req_no', 'Unknown')}")
    st.caption(f"Category: {req.get('category')}")
    
    # 4 Cards Layout
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. REQUEST
    with col1:
        with st.container(border=True):
            st.markdown("### 1. Request")
            st.caption(f"Date: {req.get('date_req')}")
            if st.button("Edit Request", use_container_width=True):
                navigate_to('form', idx, 'request')

    # 2. OBJECTION (Response)
    with col2:
        with st.container(border=True):
            st.markdown("### 2. Objection")
            obj_status = req.get('objection', {}).get('is_objected', 'Pending')
            if "Yes" in obj_status: st.error("Objected")
            elif "No" in obj_status: st.success("No Objection")
            else: st.info("Pending")
            
            if st.button("File/View Objection", use_container_width=True):
                navigate_to('form', idx, 'objection')

    # 3. REPLY TO OBJECTION
    with col3:
        with st.container(border=True):
            st.markdown("### 3. Reply")
            rep_status = req.get('reply', {}).get('has_replied', 'Pending')
            if "Yes" in rep_status: st.warning("Reply Filed")
            else: st.caption("No Reply")
            
            if st.button("File/View Reply", use_container_width=True):
                navigate_to('form', idx, 'reply')

    # 4. TRIBUNAL DETERMINATION
    with col4:
        with st.container(border=True):
            st.markdown("### 4. Ruling")
            det = req.get('determination', {}).get('decision', 'Pending')
            st.info(f"Decision: {det}")
            
            if st.button("Issue Determination", use_container_width=True):
                navigate_to('form', idx, 'determination')


# --- VIEW 3: SPECIFIC FORMS ---
elif st.session_state['doc_view_mode'] == 'form':
    f_type = st.session_state['active_form_type']
    req = get_active_request()
    list_owner = st.session_state['active_party_list'] # 'claimant' or 'respondent'
    
    st.button("⬅️ Back to Request Hub", on_click=lambda: navigate_to('details'))
    st.divider()

    # --- FORM 1: REQUEST ---
    if f_type == 'request':
        st.subheader("📝 1. Request Details")
        is_owner = (role == list_owner)
        
        with st.form("frm_request"):
            # Fields from prompt
            new_no = st.text_input("Request Number", value=req.get('req_no', ''), disabled=not is_owner)
            new_cat = st.selectbox("Category of Documents", CATEGORIES, index=CATEGORIES.index(req.get('category')) if req.get('category') in CATEGORIES else 0, disabled=not is_owner)
            new_date = st.date_input("Date of Request", value=pd.to_datetime(req.get('date_req', date.today())), disabled=not is_owner)
            new_urg = st.selectbox("Urgency Marker", URGENCY_LEVELS, index=URGENCY_LEVELS.index(req.get('urgency')) if req.get('urgency') in URGENCY_LEVELS else 0, disabled=not is_owner)
            new_desc = st.text_area("Description / Notes", value=req.get('desc', ''), disabled=not is_owner)
            
            if is_owner:
                if st.form_submit_button("Submit Request"):
                    req.update({
                        'req_no': new_no, 'category': new_cat, 
                        'date_req': str(new_date), 'urgency': new_urg, 
                        'desc': new_desc
                    })
                    save_current_data()
                    st.success("Request Saved!")
            else:
                st.warning("Read-Only Mode")

    # --- FORM 2: OBJECTION ---
    elif f_type == 'objection':
        st.subheader("✋ 2. Objection (Respondent)")
        # If list is Claimant, Respondent objects. If list is Respondent, Claimant objects.
        is_opponent = (role != list_owner and role in ['claimant', 'respondent'])
        
        curr_obj = req.get('objection', {})
        
        with st.form("frm_objection"):
            is_obj = st.selectbox("Objection?", YES_NO_OPTS, index=YES_NO_OPTS.index(curr_obj.get('is_objected')) if curr_obj.get('is_objected') in YES_NO_OPTS else 1, disabled=not is_opponent)
            obj_date = st.date_input("Date of Objection", value=pd.to_datetime(curr_obj.get('date', date.today())), disabled=not is_opponent)
            comments = st.text_area("Reason for Objection", value=curr_obj.get('reason', ''), disabled=not is_opponent)
            
            if is_opponent:
                if st.form_submit_button("Submit Objection"):
                    req['objection'] = {
                        'is_objected': is_obj,
                        'date': str(obj_date),
                        'reason': comments
                    }
                    save_current_data()
                    st.success("Objection Saved!")
            else:
                st.warning("Read-Only: Only the opposing party can object.")

    # --- FORM 3: REPLY ---
    elif f_type == 'reply':
        st.subheader("↩️ 3. Reply to Objection (Requesting Party)")
        is_owner = (role == list_owner)
        curr_reply = req.get('reply', {})
        
        st.info(f"Opposing Party Objection: {req.get('objection', {}).get('reason', 'None')}")

        with st.form("frm_reply"):
            has_reply = st.selectbox("Reply to Objection?", YES_NO_OPTS, index=YES_NO_OPTS.index(curr_reply.get('has_replied')) if curr_reply.get('has_replied') in YES_NO_OPTS else 0, disabled=not is_owner)
            rep_date = st.date_input("Date of Reply", value=pd.to_datetime(curr_reply.get('date', date.today())), disabled=not is_owner)
            rep_text = st.text_area("Arguments / Comments", value=curr_reply.get('text', ''), disabled=not is_owner)
            
            if is_owner:
                if st.form_submit_button("Submit Reply"):
                    req['reply'] = {
                        'has_replied': has_reply,
                        'date': str(rep_date),
                        'text': rep_text
                    }
                    save_current_data()
                    st.success("Reply Saved!")
            else:
                st.warning("Read-Only: Only the requesting party can reply.")

    # --- FORM 4: DETERMINATION ---
    elif f_type == 'determination':
        st.subheader("⚖️ 4. Tribunal Determination")
        is_arb = (role == 'arbitrator')
        curr_det = req.get('determination', {})
        
        # Context Display
        c1, c2 = st.columns(2)
        c1.warning(f"Objection: {req.get('objection', {}).get('reason', 'N/A')}")
        c2.info(f"Reply: {req.get('reply', {}).get('text', 'N/A')}")
        
        with st.form("frm_determination"):
            dec = st.selectbox("Determination", DETERMINATION_OPTS, index=DETERMINATION_OPTS.index(curr_det.get('decision')) if curr_det.get('decision') in DETERMINATION_OPTS else 3, disabled=not is_arb)
            det_date = st.date_input("Date of Determination", value=pd.to_datetime(curr_det.get('date', date.today())), disabled=not is_arb)
            reason = st.text_area("Tribunal Reasoning", value=curr_det.get('reason', ''), disabled=not is_arb)
            
            if is_arb:
                if st.form_submit_button("Submit Determination"):
                    req['determination'] = {
                        'decision': dec,
                        'date': str(det_date),
                        'reason': reason
                    }
                    save_current_data()
                    st.success("Determination Issued!")
            else:
                st.warning("Read-Only: Only the Tribunal can issue rulings.")
