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

def render_read_only_block(label, content, style="default"):
    """Renders a clean, non-input box display for read-only data"""
    if not content or content == "Pending":
        return # Don't render empty blocks if not needed
    
    with st.container(border=True):
        if style == "header":
            st.markdown(f"### {label}")
            st.write(content)
        elif style == "success":
            st.success(f"**{label}**\n\n{content}")
        elif style == "warning":
            st.warning(f"**{label}**\n\n{content}")
        elif style == "error":
            st.error(f"**{label}**\n\n{content}")
        else:
            st.markdown(f"**{label}**")
            st.caption(content)

# --- VIEW 1: REDFERN SCHEDULE (LIST VIEW) ---
if st.session_state['doc_view_mode'] == 'list':
    st.title("📂 Document Production (Redfern Schedule)")
    
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
                    "desc": "", # Empty desc to trigger validation later if needed
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

        # TABLE HEADER
        cols = st.columns([1.5, 3, 1.5, 1.5, 1.5, 2])
        headers = ["Req No.", "Category", "Date", "Urgency", "Objection?", "Tribunal Ruling"]
        for c, h in zip(cols, headers): c.markdown(f"**{h}**")
        st.divider()

        # TABLE ROWS
        for i, req in enumerate(request_list):
            c1, c2, c3, c4, c5, c6 = st.columns([1.5, 3, 1.5, 1.5, 1.5, 2])
            
            # 1. CLICKABLE REQ NO
            if c1.button(req.get('req_no', f'#{i+1}'), key=f"nav_{party_key}_{i}", use_container_width=True):
                st.session_state['active_party_list'] = party_key
                set_state('details', i)
                st.rerun()

            # 2. DATA
            cat_full = req.get('category', 'Unknown')
            cat_short = cat_full.split(' ')[1] + " " + cat_full.split(' ')[2] if len(cat_full.split(' ')) > 2 else cat_full
            c2.caption(cat_short)
            c3.write(req.get('date_req', '-'))
            
            urg = req.get('urgency', '')
            if "High" in urg: c4.error("High")
            elif "Medium" in urg: c4.warning("Medium")
            else: c4.success("Low")
            
            # 3. STATUS
            obj_status = req.get('objection', {}).get('is_objected', 'Pending')
            if "Yes" in obj_status: c5.warning("Yes")
            elif "No" in obj_status: c5.success("No")
            else: c5.write("-")

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
    
    # FIXED HEADER: Handle missing or empty req numbers
    req_title = req.get('req_no', f'Request #{idx+1}')
    req_desc_short = req.get('desc', 'No description provided')[:100]
    
    st.subheader(f"Managing: {req_title}")
    st.caption(f"Context: {req_desc_short}...")
    
    col1, col2, col3, col4 = st.columns(4)
    
    # 1. REQUEST CARD
    with col1:
        with st.container(border=True):
            st.markdown("### 1. Request")
            st.caption(f"Filed: {req.get('date_req')}")
            # Logic: Only owner can edit, but only if no objection yet (strict Redfern flow)
            has_objection = req.get('objection', {}).get('date')
            btn_label = "View Details" if has_objection else "Edit Request"
            
            if st.button(btn_label, key="btn_view_req", use_container_width=True):
                set_state('form', idx, 'request')
                st.rerun()

    # 2. OBJECTION CARD
    with col2:
        with st.container(border=True):
            st.markdown("### 2. Objection")
            obj_data = req.get('objection', {})
            
            if obj_data:
                # Already filled
                status = "Objected" if obj_data.get('is_objected') == "Yes" else "No Objection"
                style = "error" if status == "Objected" else "success"
                if style == "error": st.error(status)
                else: st.success(status)
                
                if st.button("View Objection", key="btn_view_obj", use_container_width=True):
                    set_state('form', idx, 'objection')
                    st.rerun()
            else:
                st.caption("Pending")
                # Logic: Can only file if Request exists
                if st.button("File Objection", key="btn_file_obj", use_container_width=True):
                    set_state('form', idx, 'objection')
                    st.rerun()

    # 3. REPLY CARD
    with col3:
        with st.container(border=True):
            st.markdown("### 3. Reply")
            # Logic: Can only reply if there is an objection
            is_objected = req.get('objection', {}).get('is_objected') == "Yes"
            reply_data = req.get('reply', {})

            if reply_data:
                 # Already filled
                status = "Reply Filed" if reply_data.get('has_replied') == "Yes" else "No Reply"
                st.info(status)
                if st.button("View Reply", key="btn_view_rep", use_container_width=True):
                    set_state('form', idx, 'reply')
                    st.rerun()
            elif is_objected:
                st.caption("Pending Reply")
                if st.button("File Reply", key="btn_file_rep", use_container_width=True):
                    set_state('form', idx, 'reply')
                    st.rerun()
            else:
                st.caption("N/A (No Objection)")
                st.button("No Action Needed", disabled=True, use_container_width=True)

    # 4. RULING CARD
    with col4:
        with st.container(border=True):
            st.markdown("### 4. Decision")
            det = req.get('determination', {}).get('decision', 'Pending')
            st.info(f"Status: {det}")
            
            if role == 'arbitrator':
                btn_txt = "Issue Decision" if det == "Pending" else "Edit Decision"
                if st.button(btn_txt, use_container_width=True):
                    set_state('form', idx, 'determination')
                    st.rerun()
            else:
                if st.button("View Decision", use_container_width=True):
                    set_state('form', idx, 'determination')
                    st.rerun()


# --- VIEW 3: INPUT FORMS & READ-ONLY VIEWS ---
elif st.session_state['doc_view_mode'] == 'form':
    f_type = st.session_state['active_form_type']
    req = get_active_request()
    list_owner = st.session_state['active_party_list'] 
    
    st.button("⬅️ Back to Hub", on_click=lambda: set_state('details'))
    st.divider()

    # --- FORM 1: REQUEST ---
    if f_type == 'request':
        is_owner = (role == list_owner)
        has_obj = req.get('objection', {}).get('date') # Check if locked
        
        # EDIT MODE: Only Owner AND Not yet objected to
        if is_owner and not has_obj:
            st.subheader("📝 Edit Request")
            with st.form("frm_request"):
                new_no = st.text_input("Request No.", value=req.get('req_no', ''))
                new_cat = st.selectbox("Category", CATEGORIES, index=CATEGORIES.index(req.get('category')) if req.get('category') in CATEGORIES else 0)
                new_date = st.date_input("Date", value=pd.to_datetime(req.get('date_req', date.today())))
                new_urg = st.selectbox("Urgency", URGENCY_LEVELS, index=URGENCY_LEVELS.index(req.get('urgency')) if req.get('urgency') in URGENCY_LEVELS else 0)
                new_desc = st.text_area("Description & Relevance (Required)", value=req.get('desc', ''), height=150)
                
                if st.form_submit_button("Save Request"):
                    if not new_desc.strip():
                        st.error("Description cannot be empty.")
                    else:
                        req.update({
                            'req_no': new_no, 'category': new_cat, 
                            'date_req': str(new_date), 'urgency': new_urg, 
                            'desc': new_desc
                        })
                        save_current_data()
                        st.success("Saved!")
                        set_state('details')
                        st.rerun()
        # READ ONLY MODE
        else:
            st.subheader("📄 Request Details")
            # Nice Clean Display - No Disabled Boxes
            c1, c2 = st.columns(2)
            with c1: render_read_only_block("Request No.", req.get('req_no'))
            with c2: render_read_only_block("Date", req.get('date_req'))
            
            c3, c4 = st.columns(2)
            with c3: render_read_only_block("Category", req.get('category'))
            with c4: render_read_only_block("Urgency", req.get('urgency'))
            
            render_read_only_block("Description & Relevance", req.get('desc'))


    # --- FORM 2: OBJECTION ---
    elif f_type == 'objection':
        is_opponent = (role != list_owner and role in ['claimant', 'respondent'])
        curr_obj = req.get('objection', {})
        is_submitted = bool(curr_obj)
        
        # EDIT MODE: Opponent AND Not yet submitted (One shot rule)
        if is_opponent and not is_submitted:
            st.subheader("✋ File Objection")
            st.info(f"Regarding Request: {req.get('req_no')} - {req.get('desc')[:50]}...")
            
            with st.form("frm_objection"):
                st.write("Do you object to producing these documents?")
                col_a, col_b = st.columns(2)
                
                # We use a radio to force a clear choice
                choice = st.radio("Decision", ["I Object", "No Objection (Will Produce)"], label_visibility="collapsed")
                
                comments = st.text_area("Grounds for Objection (Required if Objecting)", height=150)
                
                if st.form_submit_button("Submit Final Decision"):
                    is_obj_bool = "Yes" if choice == "I Object" else "No"
                    
                    # Validation
                    if is_obj_bool == "Yes" and not comments.strip():
                        st.error("You must provide grounds for your objection.")
                    else:
                        req['objection'] = {
                            'is_objected': is_obj_bool,
                            'date': str(date.today()),
                            'reason': comments if is_obj_bool == "Yes" else "Party confirmed no objection."
                        }
                        save_current_data()
                        st.success("Decision Recorded")
                        set_state('details')
                        st.rerun()
                        
        # READ ONLY MODE
        else:
            st.subheader("Objection Status")
            status_text = "Objected" if curr_obj.get('is_objected') == "Yes" else "No Objection"
            
            render_read_only_block("Status", status_text, style="warning" if status_text=="Objected" else "success")
            render_read_only_block("Date", curr_obj.get('date'))
            render_read_only_block("Grounds / Comments", curr_obj.get('reason'))


    # --- FORM 3: REPLY ---
    elif f_type == 'reply':
        is_owner = (role == list_owner)
        curr_reply = req.get('reply', {})
        is_submitted = bool(curr_reply)
        
        # Show context first
        render_read_only_block("Opposing Party's Objection", req.get('objection', {}).get('reason'), style="warning")
        st.divider()

        # EDIT MODE: Owner AND Not yet submitted (One shot rule)
        if is_owner and not is_submitted:
            st.subheader("↩️ File Reply")
            
            with st.form("frm_reply"):
                st.write("Do you wish to maintain your request?")
                choice = st.radio("Decision", ["Maintain Request (File Reply)", "Withdraw Request / Accept Objection"], label_visibility="collapsed")
                
                rep_text = st.text_area("Reply Arguments (Required if Maintaining)", height=150)
                
                if st.form_submit_button("Submit Final Reply"):
                    has_rep_bool = "Yes" if "Maintain" in choice else "No"
                    
                    if has_rep_bool == "Yes" and not rep_text.strip():
                        st.error("You must provide arguments to maintain your request.")
                    else:
                        req['reply'] = {
                            'has_replied': has_rep_bool,
                            'date': str(date.today()),
                            'text': rep_text if has_rep_bool == "Yes" else "Request Withdrawn / Objection Accepted."
                        }
                        save_current_data()
                        st.success("Reply Recorded")
                        set_state('details')
                        st.rerun()
                        
        # READ ONLY MODE
        else:
            st.subheader("Reply Status")
            status_text = "Maintained" if curr_reply.get('has_replied') == "Yes" else "Withdrawn"
            
            render_read_only_block("Status", status_text)
            render_read_only_block("Date", curr_reply.get('date'))
            render_read_only_block("Arguments", curr_reply.get('text'))


    # --- FORM 4: TRIBUNAL DECISION ---
    elif f_type == 'determination':
        st.subheader("⚖️ Tribunal's Decision")
        is_arb = (role == 'arbitrator')
        curr_det = req.get('determination', {})
        
        # CLEAN READ-ONLY CONTEXT
        # Instead of big empty boxes, we render nicely formatted blocks
        
        with st.expander("Show Full Request Context", expanded=True):
            st.markdown(f"**1. Request:** {req.get('desc')}")
            st.divider()
            
            c1, c2 = st.columns(2)
            with c1: 
                obj_text = req.get('objection', {}).get('reason', 'None')
                render_read_only_block("2. Objection", obj_text, style="warning")
            with c2:
                rep_text = req.get('reply', {}).get('text', 'None')
                # Only show Reply box if it exists or matters
                if rep_text != 'None':
                    render_read_only_block("3. Reply", rep_text, style="default")
        
        st.write("")
        
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
            # Parties View
            render_read_only_block("Tribunal Ruling", curr_det.get('decision', 'Pending'), style="success" if curr_det.get('decision')=="Allowed" else "default")
            render_read_only_block("Date of Decision", curr_det.get('date'))
            render_read_only_block("Tribunal's Reasoning", curr_det.get('reason'))
