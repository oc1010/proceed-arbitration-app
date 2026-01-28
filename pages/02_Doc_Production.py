import streamlit as st
import pandas as pd
from datetime import date, datetime
from db import load_complex_data, save_complex_data
import json

# --- PAGE SETUP ---
st.set_page_config(page_title="Document Production", layout="wide")

# --- AUTH & SESSION STATE INITIALIZATION ---
if 'doc_view_mode' not in st.session_state: st.session_state['doc_view_mode'] = 'list' # list, details, form
if 'active_req_idx' not in st.session_state: st.session_state['active_req_idx'] = None
if 'active_party_list' not in st.session_state: st.session_state['active_party_list'] = 'claimant' # claimant or respondent
if 'active_form_type' not in st.session_state: st.session_state['active_form_type'] = None # request, response, determination

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

# --- HELPER FUNCTIONS ---

def save_current_data():
    """Saves the global doc_prod dictionary to the DB"""
    save_complex_data("doc_prod", doc_prod)
    # st.toast("Changes saved automatically.", icon="💾")

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

# --- VIEW 1: THE DASHBOARD (LIST VIEW) ---
if st.session_state['doc_view_mode'] == 'list':
    st.title("📂 Document Production Management")
    
    # 1. Select List (Tab-like behavior using radio or actual tabs)
    party_tab = st.radio("Select Schedule to View:", ["Claimant's Requests", "Respondent's Requests"], horizontal=True)
    current_list_key = "claimant" if "Claimant" in party_tab else "respondent"
    st.session_state['active_party_list'] = current_list_key
    
    request_list = doc_prod[current_list_key]

    # 2. Add New Request Button (Only if you are the owner of this list)
    if role == current_list_key:
        with st.expander("➕ Create New Request"):
            with st.form("new_req_form"):
                n_desc = st.text_input("Description of Documents")
                n_cat = st.selectbox("Category", ["Technical", "Financial", "Legal/Contractual", "Internal Comms", "Other"])
                if st.form_submit_button("Add Request"):
                    new_req = {
                        "id": len(request_list) + 1,
                        "desc": n_desc,
                        "category": n_cat,
                        "date": str(date.today()),
                        "response": {},     # Nested Object for Response
                        "determination": {} # Nested Object for Ruling
                    }
                    doc_prod[current_list_key].append(new_req)
                    save_current_data()
                    st.success("Request Created")
                    st.rerun()

    # 3. Display List Summary
    if not request_list:
        st.info("No requests found in this schedule.")
    else:
        st.write("### Request List")
        st.caption("Click 'Manage' to view details, responses, or rulings.")
        
        # We build a custom clean table
        for i, req in enumerate(request_list):
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 4, 2, 2])
                c1.write(f"**#{req.get('id', i+1)}**")
                c1.caption(req.get('category'))
                c2.write(req.get('desc', 'No Description'))
                
                # Status badges
                has_resp = "✅ Responded" if req.get('response', {}).get('text') else "⏳ Wait for Resp."
                has_det = "⚖️ Ruled" if req.get('determination', {}).get('decision') else "⏳ Pending"
                c3.caption(f"{has_resp} | {has_det}")
                
                if c4.button("Manage / View", key=f"btn_{current_list_key}_{i}"):
                    navigate_to('details', i)

# --- VIEW 2: THE "3 CLICKABLE OPTIONS" (HUB) ---
elif st.session_state['doc_view_mode'] == 'details':
    req = get_active_request()
    idx = st.session_state['active_req_idx'] + 1
    
    st.button("⬅️ Back to List", on_click=lambda: navigate_to('list'))
    st.divider()
    
    st.markdown(f"## Request #{idx}")
    st.markdown(f"**Summary:** {req.get('desc')}")
    
    st.write("")
    
    # THE 3 BIG CLICKABLE CARDS
    c1, c2, c3 = st.columns(3)
    
    # CARD 1: REQUEST
    with c1:
        with st.container(border=True):
            st.markdown("### 📄 Request")
            st.caption("View full details and justification.")
            if st.button("Open Request Details", use_container_width=True):
                navigate_to('form', form_type='request')

    # CARD 2: RESPONSE
    with c2:
        with st.container(border=True):
            st.markdown("### 🗣️ Response")
            # Logic: Has it been filled?
            if req.get('response'):
                st.success("Response Submitted")
            else:
                st.warning("Pending Response")
            
            if st.button("Open Response", use_container_width=True):
                navigate_to('form', form_type='response')

    # CARD 3: DETERMINATION
    with c3:
        with st.container(border=True):
            st.markdown("### ⚖️ Determination")
            if req.get('determination'):
                st.info(f"Ruling: {req.get('determination', {}).get('decision')}")
            else:
                st.caption("No ruling yet.")
                
            if st.button("Open Determination", use_container_width=True):
                navigate_to('form', form_type='determination')

# --- VIEW 3: SPECIFIC DRILL-DOWN FORMS ---
elif st.session_state['doc_view_mode'] == 'form':
    f_type = st.session_state['active_form_type']
    req = get_active_request()
    list_owner = st.session_state['active_party_list'] # 'claimant' or 'respondent'
    
    st.button("⬅️ Back to Options", on_click=lambda: navigate_to('details'))
    st.divider()

    # --- FORM A: REQUEST DETAILS (Editable by Owner Only) ---
    if f_type == 'request':
        st.subheader("📄 Request Details")
        
        # Permission: Only the list owner can edit request text
        is_editable = (role == list_owner)
        
        with st.form("req_edit_form"):
            desc = st.text_area("Description", value=req.get('desc', ''), disabled=not is_editable)
            cat = st.selectbox("Category", ["Technical", "Financial", "Legal", "Other"], 
                             index=0, disabled=not is_editable) # Simple index logic for demo
            relevance = st.text_area("Relevance & Materiality", value=req.get('relevance', ''), disabled=not is_editable)
            
            if is_editable:
                if st.form_submit_button("💾 Save Changes"):
                    req['desc'] = desc
                    req['category'] = cat
                    req['relevance'] = relevance
                    save_current_data()
                    st.success("Updated.")
            else:
                st.form_submit_button("Read Only Mode", disabled=True)

    # --- FORM B: RESPONSE (Editable by OPPOSING party only) ---
    elif f_type == 'response':
        st.subheader("🗣️ Response & Objections")
        
        # Context: Show what we are responding to
        st.info(f"**Responding to Request:** {req.get('desc')}")
        
        # Permission: If List Owner is Claimant, Respondent edits. If List Owner is Respondent, Claimant edits.
        # Arbitrator can always edit? Or Read Only? Usually Arbitrator doesn't write the response.
        can_edit = False
        if list_owner == 'claimant' and role == 'respondent': can_edit = True
        if list_owner == 'respondent' and role == 'claimant': can_edit = True
        
        curr_resp = req.get('response', {})
        
        with st.form("resp_form"):
            obj_status = st.selectbox("Objection?", ["No - Will Produce", "Yes - Objecting"], 
                                      index=1 if curr_resp.get('objection') == "Yes" else 0,
                                      disabled=not can_edit)
            
            resp_text = st.text_area("Objection Reason / Comments", 
                                     value=curr_resp.get('text', ''), 
                                     disabled=not can_edit)
            
            if can_edit:
                if st.form_submit_button("Submit Response"):
                    req['response'] = {
                        "objection": "Yes" if "Yes" in obj_status else "No",
                        "text": resp_text,
                        "date": str(date.today()),
                        "author": role
                    }
                    save_current_data()
                    st.success("Response Recorded.")
                    navigate_to('details')
            else:
                st.warning(f"Only the **{ 'Respondent' if list_owner == 'claimant' else 'Claimant' }** can edit this.")
                st.form_submit_button("Read Only", disabled=True)

    # --- FORM C: DETERMINATION (Editable by Arbitrator Only) ---
    elif f_type == 'determination':
        st.subheader("⚖️ Tribunal Determination")
        
        # Context
        c1, c2 = st.columns(2)
        c1.info(f"**Request:** {req.get('desc')}")
        resp_data = req.get('response', {})
        c2.warning(f"**Response:** {resp_data.get('text', 'No response yet')}")
        
        curr_det = req.get('determination', {})
        is_arb = (role == 'arbitrator')
        
        with st.form("det_form"):
            decision = st.selectbox("Decision", ["Allowed", "Allowed in Part", "Denied", "Reserved"], 
                                  index=0, disabled=not is_arb)
            
            reason = st.text_area("Tribunal's Reasoning", value=curr_det.get('reason', ''), disabled=not is_arb)
            
            if is_arb:
                if st.form_submit_button("Issue Ruling"):
                    req['determination'] = {
                        "decision": decision,
                        "reason": reason,
                        "date": str(date.today())
                    }
                    save_current_data()
                    st.success("Ruling Issued.")
                    navigate_to('details')
            else:
                st.info("Waiting for Tribunal Decision.")
