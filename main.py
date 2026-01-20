import streamlit as st

st.set_page_config(page_title="PROCEED Dashboard", layout="wide", initial_sidebar_state="expanded")

# --- AUTHENTICATION ---
USERS = {
    "admin": "admin123",       
    "claimant": "party123",    
    "respondent": "party123"   
}

if 'user_role' not in st.session_state:
    st.session_state['user_role'] = None

def login():
    u = st.session_state.get("username", "").strip().lower()
    p = st.session_state.get("password", "").strip()
    if u in USERS and USERS[u] == p:
        st.session_state['user_role'] = "arbitrator" if u == "admin" else u
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
            with st.expander("Demo Credentials"):
                st.code("admin / admin123\nclaimant / party123")
    st.stop()

# --- NAVIGATION SIDEBAR ---
with st.sidebar:
    st.markdown(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Sign Out"): logout()
    st.divider()
    
    if st.session_state['user_role'] == 'arbitrator':
        st.page_link("main.py", label="Home Dashboard", icon="🏠")
        st.subheader("1. Setup")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire", icon="✏️")
        st.subheader("2. Manage")
        st.page_link("pages/01_Drafting_Engine.py", label="Drafting Engine", icon="📝")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline", icon="📅")
    else:
        st.page_link("main.py", label="Home Dashboard", icon="🏠")
        st.page_link("pages/00_Fill_Questionnaire.py", label="Procedural Questionnaire", icon="📋")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline", icon="📅")

st.title("PROCEED: Tribunal Dashboard")

if st.session_state['user_role'] == 'arbitrator':
    st.success("System Status: Online. Database Connected.")
    c1, c2, c3 = st.columns(3)
    
    # CARD 1: QUESTIONNAIRE (NEW)
    with c1:
        with st.container(border=True):
            st.markdown("### 1. Questionnaire")
            st.write("Customize and publish the procedural questionnaire to parties.")
            if st.button("Edit Questionnaire"): st.switch_page("pages/00_Edit_Questionnaire.py")
            
    # CARD 2: DRAFTING
    with c2:
        with st.container(border=True):
            st.markdown("### 2. Drafting")
            st.write("Generate PO1 using party responses and smart logic.")
            if st.button("Open Drafting Engine"): st.switch_page("pages/01_Drafting_Engine.py")
            
    # CARD 3: TIMELINE
    with c3:
        with st.container(border=True):
            st.markdown("### 3. Timeline")
            st.write("View live schedule and approve extension requests.")
            if st.button("View Timeline"): st.switch_page("pages/02_Smart_Timeline.py")
else:
    st.info(f"Welcome, Counsel for {st.session_state['user_role'].title()}.")
    st.markdown("### Active Tasks")
    with st.container(border=True):
        st.warning("⚠️ Action Required: Pre-Hearing Questionnaire")
        st.write("The Tribunal requests your preferences for the conduct of the arbitration.")
        if st.button("Start Questionnaire", type="primary"): st.switch_page("pages/00_Fill_Questionnaire.py")
