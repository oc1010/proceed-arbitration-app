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

# --- CONSTANTS ---
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

def set_state(mode, idx=None, form_type=None):
    st.session_state['doc_view_mode'] = mode
    if idx is not None: st.session_state['active_req_idx'] = idx
    if form_type is not None: st.session_state['active_form_type'] = form_type

def get_active_list():
    return doc_prod.get(st.session_state['active_party_list'], [])

def get_active_request():
    lst = get_active_list()
    idx = st.session_state['active_req_idx']
    if idx is not None and 0 <= idx < len(lst):
        return lst[idx]
    return {}

# --- VIEW 1: REDFERN SCHEDULE (LIST VIEW) ---
if st.session_state['doc_view_mode'] == 'list':
    st.title("📂 Document Production (Redfern Schedule)")
    
    # Tabs for Parties
    tab_c, tab_r = st.tabs(["Claimant's Requests", "Respondent's Requests"])
    
    def render_request_list(party_key):
        request_list = doc_prod[party_key]
        
        # New Request Button (Only for Owner)
        if role == party_key:
            if st.button(f"➕ Create New Request ({party_key.title()})", key=f"btn_new_{party_key}"):
                new_idx = len(request_list)
                new_req = {
                    "req_no": f"No. {new_idx + 1}",
                    "category": CATEGORIES[0],
                    "date_req": str(date.today()),
                    "urgency": URGENCY_LEVELS[0],
                    "desc": "Description of documents...",
                    "objection": {}, 
                    "reply": {}, 
                    "determination": {}
                }
                doc_prod[party_key].append(new_req)
                save_current_data()
                st.session_state['active_party_list'] = party_key
                set_state('form', new_idx, 'request') 
                st.rerun()

        if not request_list:
            st.info("No requests submitted yet.")
            return

        # --- UNIFIED TABLE HEADER ---
        cols = st.columns([1.5, 3, 1.5, 1.5, 1.5, 2])
        headers = ["Req No.", "Category", "Date", "Urgency", "Objection?", "Tribunal Ruling"]
        for c, h in zip(cols, headers): c.markdown(f"**{h}**")
        st.divider()

        # --- TABLE ROWS ---
        for i, req in enumerate(request_list):
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 3, 1.5, 1.5, 1.5, 2])
            
            # 1. CLICKABLE REQUEST NUMBER
            if c1.button(req.get('req_no', f'#{i+1}'), key=f"nav_{party_key}_{i}", use_container_width=True):
                st.session_state['active_party_list'] = party_key
                set_state('details', i)
                st.rerun()

            # 2. CATEGORY
            cat_full = req.get('category', 'Unknown')
            cat_short = cat_full.split(' ')[1] + " " + cat_full.split(' ')[2] if len(cat_full.split(' ')) > 2 else cat_full
            c2.caption(cat_short)
            
            # 3. DATE
            c3.write(req.get('date_req', '-'))
            
            # 4. URGENCY
            urg = req.get('urgency', '')
            if "High" in urg: c4.error("High")
            elif "Medium" in urg: c4.warning("Medium")
            else: c4.success("Low")
            
            # 5. OBJECTION STATUS
            obj_status = req.get('objection', {}).get('is_objected', 'Pending')
            if "Yes" in obj_status: c5.warning("Yes")
            elif "No" in obj_status: c5.success("No")
            else: c5.write("-")

            # 6. TRIBUNAL RULING
            det = req.get('determination', {})
            decision = det.get('decision')
            dec_date = det.get('date')
            
            if decision:
                c6.info(f"**{decision}**\n\n{dec_date}")
            else:
                c6.write("-")
            
            st.divider()

    with tab_c:
        render_request_list("claimant")
    with tab_r:
        render_request_list("respondent")


# --- VIEW 2: THE REQUEST HUB (DETAILS) ---
elif st.session_state['doc_view_mode'] == 'details':
    req = get_active_request()
    idx = st.session_state['active_req_idx']
    
    st.button("⬅️ Back to Schedule", on_click=lambda: set_state('list'))
    st.divider()
    
    # Header Info
    req_title = req.get('req_no', f'Request #{idx+1}')
    req_desc_short = req.get('desc', '')[:60] + "..." if len(req.get('desc', '')) > 60 else req.get('desc', '')
    
    st.subheader(f"Managing: {req_title}")
    st.caption(f"Context: {req_desc_short}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. REQUEST
    with col1:
        with st.container(border=True):
            st.markdown("### 1. Request")
            st.caption(f"Filed: {req.get('date_req')}")
            if st.button("View / Edit Request", use_container_width=True):
                set_state('form', idx, 'request')
                st.rerun()

    # 2. OBJECTION
    with col2:
        with st.container(border=True):
            st.markdown("### 2. Objection")
            obj_data = req.get('objection', {})
            obj_status = obj_data.get('is_objected', 'Pending')
            
            if "Yes" in obj_status: st.error("Objected")
            elif "No" in obj_status: st.success("No Objection")
            else: st.caption("Pending Response")
            
            if st.button("File / View Objection", use_container_width=True):
                set_state('form', idx, 'objection')
                st.rerun()

    # 3. REPLY
    with col3:
        with st.container(border=True):
            st.markdown("### 3. Reply")
            has_objection = "Yes" in req.get('objection', {}).get('is_objected', '')
            
            if has_objection:
                rep_status = req.get('reply', {}).get('has_replied', 'Pending')
                if "Yes" in rep_status: st.warning("Reply Filed")
                else: st.caption("Pending Reply")
                
                if st.button("File / View Reply", use_container_width=True):
                    set_state('form', idx, 'reply')
                    st.rerun()
            else:
                st.info("No Objection")
                st.caption("Reply not required.")
                st.button("File / View Reply", disabled=True, use_container_width=True)

    # 4. RULING
    with col4:
        with st.container(border=True):
            st.markdown("### 4. Decision")
            det = req.get('determination', {}).get('decision', 'Pending')
            st.info(f"Status: {det}")
            
            # Logic: Arbitrator edits, Parties VIEW.
            if role == 'arbitrator':
                if st.button("Issue Decision", use_container_width=True):
                    set_state('form', idx, 'determination')
                    st.rerun()
            else:
                if st.button("View Decision", use_container_width=True):
                    set_state('form', idx, 'determination')
                    st.rerun()


# --- VIEW 3: INPUT FORMS ---
elif st.session_state['doc_view_mode'] == 'form':
    f_type = st.session_state['active_form_type']
    req = get_active_request()
    list_owner = st.session_state['active_party_list'] # 'claimant' or 'respondent'
    
    st.button("⬅️ Back to Hub", on_click=lambda: set_state('details'))
    st.divider()

    # --- FORM 1: REQUEST ---
    if f_type == 'request':
        st.subheader("📝 Request to Produce Documents")
        is_owner = (role == list_owner)
        
        # EDIT MODE
        if is_owner:
            with st.form("frm_request"):
                new_no = st.text_input("Request No.", value=req.get('req_no', ''))
                new_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(req.get('category')) if req.get('category') in CATEGORIES else 0)
                new_date = st.date_input("Date", value=pd.to_datetime(req.get('date_req', date.today())))
                new_urg = st.selectbox("Urgency", URGENCY_LEVELS, index=URGENCY_LEVELS.index(req.get('urgency')) if req.get('urgency') in URGENCY_LEVELS else 0)
                new_desc = st.text_area("Description & Relevance", value=req.get('desc', ''), height=150)
                
                if st.form_submit_button("Save Request"):
                    req.update({
                        'req_no': new_no, 'category': new_cat, 
                        'date_req': str(new_date), 'urgency': new_urg, 
                        'desc': new_desc
                    })
                    save_current_data()
                    st.success("Saved!")
                    set_state('details')
                    st.rerun()
        # READ-ONLY MODE (DISABLED WIDGETS)
        else:
            st.info("Read-Only: You cannot edit this request.")
            st.text_input("Request No.", value=req.get('req_no', ''), disabled=True)
            st.text_input("Category", value=req.get('category', ''), disabled=True)
            st.text_input("Urgency", value=req.get('urgency', ''), disabled=True)
            st.text_area("Description & Relevance", value=req.get('desc', ''), height=150, disabled=True)

    # --- FORM 2: OBJECTION ---
    elif f_type == 'objection':
        st.subheader("✋ Objection to Production")
        is_opponent = (role != list_owner and role in ['claimant', 'respondent'])
        curr_obj = req.get('objection', {})
        
        if is_opponent:
            with st.form("frm_objection"):
                st.caption(f"Objecting to: {req.get('desc')}")
                is_obj = st.selectbox("Do you object?", YES_NO_OPTS, index=YES_NO_OPTS.index(curr_obj.get('is_objected')) if curr_obj.get('is_objected') in YES_NO_OPTS else 1)
                obj_date = st.date_input("Date", value=pd.to_datetime(curr_obj.get('date', date.today())))
                comments = st.text_area("Grounds for Objection", value=curr_obj.get('reason', ''), height=150)
                
                if st.form_submit_button("Submit Objection"):
                    req['objection'] = {
                        'is_objected': is_obj,
                        'date': str(obj_date),
                        'reason': comments
                    }
                    save_current_data()
                    st.success("Objection Recorded")
                    set_state('details')
                    st.rerun()
        else:
            st.info("Read-Only: View Objection Details")
            st.text_input("Objected?", value=curr_obj.get('is_objected', 'Pending'), disabled=True)
            st.text_area("Grounds for Objection", value=curr_obj.get('reason', ''), height=150, disabled=True)

    # --- FORM 3: REPLY ---
    elif f_type == 'reply':
        st.subheader("↩️ Reply to Objection")
        is_owner = (role == list_owner)
        curr_reply = req.get('reply', {})
        
        with st.expander("View Objection", expanded=True):
            st.write(req.get('objection', {}).get('reason', 'No text provided.'))

        if is_owner:
            with st.form("frm_reply"):
                has_reply = st.selectbox("Maintain Request?", YES_NO_OPTS, index=YES_NO_OPTS.index(curr_reply.get('has_replied')) if curr_reply.get('has_replied') in YES_NO_OPTS else 0)
                rep_date = st.date_input("Date", value=pd.to_datetime(curr_reply.get('date', date.today())))
                rep_text = st.text_area("Reply Arguments", value=curr_reply.get('text', ''), height=150)
                
                if st.form_submit_button("Submit Reply"):
                    req['reply'] = {
                        'has_replied': has_reply,
                        'date': str(rep_date),
                        'text': rep_text
                    }
                    save_current_data()
                    st.success("Reply Recorded")
                    set_state('details')
                    st.rerun()
        else:
            st.info("Read-Only: View Reply Details")
            st.text_input("Request Maintained?", value=curr_reply.get('has_replied', 'Pending'), disabled=True)
            st.text_area("Reply Arguments", value=curr_reply.get('text', ''), height=150, disabled=True)

    # --- FORM 4: TRIBUNAL DECISION ---
    elif f_type == 'determination':
        st.subheader("⚖️ Tribunal's Decision")
        is_arb = (role == 'arbitrator')
        curr_det = req.get('determination', {})
        
        c1, c2, c3 = st.columns(3)
        c1.info(f"**Request:**\n{req.get('desc')}")
        c2.warning(f"**Objection:**\n{req.get('objection', {}).get('reason', '-')}")
        c3.success(f"**Reply:**\n{req.get('reply', {}).get('text', '-')}")
        
        if is_arb:
            with st.form("frm_determination"):
                dec = st.selectbox("Ruling", DETERMINATION_OPTS, index=DETERMINATION_OPTS.index(curr_det.get('decision')) if curr_det.get('decision') in DETERMINATION_OPTS else 3)
                det_date = st.date_input("Date", value=pd.to_datetime(curr_det.get('date', date.today())))
                reason = st.text_area("Reasoning", value=curr_det.get('reason', ''), height=150)
                
                if st.form_submit_button("Issue Order"):
                    req['determination'] = {
                        'decision': dec,
                        'date': str(det_date),
                        'reason': reason
                    }
                    save_current_data()
                    st.success("Order Issued")
                    set_state('details')
                    st.rerun()
        else:
            # Parties can see this now!
            st.info("Read-Only: Tribunal Determination")
            st.text_input("Ruling", value=curr_det.get('decision', 'Pending'), disabled=True)
            st.text_input("Date of Decision", value=curr_det.get('date', '-'), disabled=True)
            st.text_area("Tribunal's Reasoning", value=curr_det.get('reason', ''), height=150, disabled=True)
