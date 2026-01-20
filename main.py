import streamlit as st

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

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
        if u == "admin":
            st.session_state['user_role'] = "arbitrator"
        else:
            st.session_state['user_role'] = u 
    else:
        st.error("Invalid Credentials")

def logout():
    st.session_state['user_role'] = None
    st.rerun()

# --- LOGIN SCREEN ---
# If not logged in, show login form and STOP. Do not render sidebar.
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

# --- SIDEBAR NAVIGATION (Only renders AFTER login) ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True):
        logout()
    
    st.divider()
    st.caption("NAVIGATION")
    
    if st.session_state['user_role'] == 'arbitrator':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    else:
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Fill_Questionnaire.py", label="Procedural Questionnaire")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

# --- MAIN DASHBOARD CONTENT ---
st.title("PROCEED: Tribunal Dashboard")

if st.session_state['user_role'] == 'arbitrator':
    st.info("System Status: Online. Database Connected.")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        with st.container(border=True):
            st.markdown("### Questionnaire")
            st.write("Customize and publish.")
            if st.button("Edit"): st.switch_page("pages/00_Edit_Questionnaire.py")
            
    with c2:
        with st.container(border=True):
            st.markdown("### Procedural Order No. 1")
            st.write("Drafting Engine.")
            if st.button("Draft Order"): st.switch_page("pages/01_Drafting_Engine.py")
            
    with c3:
        with st.container(border=True):
            st.markdown("### Timeline")
            st.write("Live Schedule.")
            if st.button("View"): st.switch_page("pages/02_Smart_Timeline.py")

else:
    st.info(f"Welcome, Counsel for {st.session_state['user_role'].title()}.")
    st.markdown("### Active Tasks")
    with st.container(border=True):
        st.markdown("#### Pre-Hearing Questionnaire")
        st.write("Please submit your procedural preferences.")
        if st.button("Start Questionnaire", type="primary"): 
            st.switch_page("pages/00_Fill_Questionnaire.py")
            
    with st.container(border=True):
        st.markdown("#### Case Timeline")
        st.write("View deadlines and request extensions.")
        if st.button("View Schedule"): 
            st.switch_page("pages/02_Smart_Timeline.py")
