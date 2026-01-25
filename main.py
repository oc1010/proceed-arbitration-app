import streamlit as st
import pandas as pd
from db import load_responses

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

# --- AUTHENTICATION ---
USERS = {
    "lcia": "lcia123",             
    "arbitrator": "arbitrator123", 
    "claimant": "party123",        
    "respondent": "party123"       
}

if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None

def login():
    u = st.session_state.get("username", "").strip().lower()
    p = st.session_state.get("password", "").strip()
    if u in USERS and USERS[u] == p:
        st.session_state['user_role'] = u
    else:
        st.error("Invalid Credentials")

def logout():
    st.session_state['user_role'] = None
    st.rerun()

# --- LOGIN SCREEN ---
if st.session_state['user_role'] is None:
    st.title("PROCEED | Secure Gateway")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            st.subheader("System Access")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            if st.button("Log In", type="primary", use_container_width=True):
                login()
                st.rerun()
    st.stop()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    role = st.session_state['user_role']
    st.write(f"User: **{role.upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    
    st.divider()
    st.caption("NAVIGATION")
    
    if role == 'lcia':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 1 Qs")
    elif role == 'arbitrator':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    else:
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Fill_Questionnaire.py", label="Fill Questionnaires")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

# --- MAIN DASHBOARD ---
st.title("PROCEED: Arbitration Dashboard")
role = st.session_state['user_role']

if role == 'lcia':
    st.info("Logged in as: LCIA Institution")
    
    # 1. EDITING
    with st.container(border=True):
        st.markdown("### 1. Phase 1: Pre-Tribunal Appointment")
        st.write("Edit and release the initial questionnaire to the parties.")
        if st.button("Edit Questionnaire"): st.switch_page("pages/00_Edit_Questionnaire.py")

    # 2. VIEWING RESPONSES
    st.divider()
    st.markdown("### 2. Monitor Responses")
    with st.expander("🔎 View Phase 1 Responses (Pre-Tribunal)", expanded=True):
        p1_resp = load_responses("phase1")
        c_data = p1_resp.get('claimant', {})
        r_data = p1_resp.get('respondent', {})
        
        if not c_data and not r_data:
            st.warning("No responses submitted yet.")
        else:
            all_keys = list(set(list(c_data.keys()) + list(r_data.keys())))
            q_keys = [k for k in all_keys if not k.endswith("_comment")]
            
            data = []
            for k in q_keys:
                data.append({
                    "Question ID": k,
                    "Claimant": c_data.get(k, "-"),
                    "Respondent": r_data.get(k, "-")
                })
            st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

elif role == 'arbitrator':
    st.info("Logged in as: Arbitral Tribunal")
    
    # 1. REVIEW PHASE 1
    with st.expander("📄 Review Pre-Tribunal Questionnaire (Phase 1)"):
        p1_resp = load_responses("phase1")
        c_data = p1_resp.get('claimant', {})
        r_data = p1_resp.get('respondent', {})
        if not c_data and not r_data:
            st.warning("Parties have not submitted Phase 1 yet.")
        else:
            st.write("Responses received from parties prior to your appointment:")
            # Simple view
            df_p1 = pd.DataFrame([c_data, r_data], index=["Claimant", "Respondent"]).T
            st.dataframe(df_p1)

    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### Phase 2: Pre-Hearing")
            st.write("Configure & Release PO1 Questionnaire.")
            if st.button("Edit Phase 2"): st.switch_page("pages/00_Edit_Questionnaire.py")
    with c2:
        with st.container(border=True):
            st.markdown("### Drafting Engine")
            st.write("View Responses & Draft Order.")
            if st.button("Open Engine"): st.switch_page("pages/01_Drafting_Engine.py")
    with c3:
        with st.container(border=True):
            st.markdown("### Smart Timeline")
            st.write("View or Edit Deadlines.")
            if st.button("Open Timeline"): st.switch_page("pages/02_Smart_Timeline.py")
            
elif role in ['claimant', 'respondent']:
    st.info(f"Welcome, Counsel for {role.title()}.")
    st.markdown("### Active Tasks")
    with st.container(border=True):
        st.markdown("#### Procedural Questionnaires")
        st.write("Please check for pending questionnaires from the LCIA or the Tribunal.")
        if st.button("Go to Questionnaires", type="primary"): 
            st.switch_page("pages/00_Fill_Questionnaire.py")
