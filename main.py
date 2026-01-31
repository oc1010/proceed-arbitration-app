import streamlit as st
import pandas as pd
from db import create_new_case, get_active_case_id, load_full_config, db

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

# --- AUTH & SESSION STATE ---
if 'user_role' not in st.session_state: st.session_state['user_role'] = None
if 'active_case_id' not in st.session_state: st.session_state['active_case_id'] = None

# --- LOBBY: SELECT OR CREATE CASE ---
if not st.session_state['active_case_id']:
    st.title("⚖️ PROCEED: Arbitration Manager")
    st.markdown("### Secure Cloud Gateway")
    
    tab1, tab2 = st.tabs(["📂 Load Existing Case", "🆕 Register New Case"])
    
    with tab1:
        st.write("Enter the Case ID provided by the LCIA.")
        cid_input = st.text_input("Case ID", placeholder="LCIA-170...")
        
        # Simple Role Selection for Demo purposes
        role_input = st.selectbox("Select Your Role", ["arbitrator", "claimant", "respondent", "lcia"])
        
        if st.button("Access Case"):
            if not db:
                st.error("Database not connected. Check your secrets.")
            else:
                doc = db.collection("arbitrations").document(cid_input).get()
                if doc.exists:
                    st.session_state['active_case_id'] = cid_input
                    st.session_state['user_role'] = role_input
                    st.success("Case Found! Loading...")
                    st.rerun()
                else:
                    st.error("Case ID not found in the Cloud Database.")

    with tab2:
        st.write("Initialize a new arbitration matter (LCIA Registrar Only).")
        c_name = st.text_input("Case Name (e.g. Alpha v. Beta)")
        c_email = st.text_input("Claimant Email")
        r_email = st.text_input("Respondent Email")
        
        if st.button("Initialize New Case"):
            if not db:
                st.error("Database not connected.")
            else:
                new_id = create_new_case(c_name, c_email, r_email)
                st.success(f"Case Created Successfully!")
                st.code(new_id, language="text")
                st.info("Please copy this ID. You will need it to log in on the 'Load Existing Case' tab.")

    st.stop() # Prevent the rest of the app from loading until logged in

# --- LOGGED IN DASHBOARD ---
role = st.session_state['user_role']
case_data = load_full_config()

# If data load fails for some reason, provide a safe fallback
if not case_data:
    st.error("Failed to load case data. Please re-login.")
    if st.button("Back to Lobby"):
        st.session_state['active_case_id'] = None
        st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.header(f"{case_data['meta']['case_name']}")
    st.caption(f"ID: {st.session_state['active_case_id']}")
    st.write(f"User: **{role.upper()}**")
    st.divider()
    
    st.page_link("main.py", label="🏠 Home Dashboard")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")

    # Role-Based Navigation
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Phase 1")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Phase 2")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 PO1 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    elif role in ['claimant', 'respondent']:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")

    st.divider()
    if st.button("Logout / Switch Case", use_container_width=True):
        st.session_state['active_case_id'] = None
        st.rerun()

# --- MAIN DASHBOARD CONTENT ---
st.title(f"Welcome, {role.title()}")
st.markdown(f"### Case Dashboard: {case_data['meta']['case_name']}")
st.info(f"Current Phase: {case_data['meta']['status']}")

# --- CARDS LOGIC ---
cards = []
cards.append(("🔔", "Notifications", "View Alerts & Messages", "pages/05_Notifications.py"))

if role == 'lcia':
    cards.append(("✏️", "Phase 1 Configuration", "Edit Pre-Tribunal Questionnaires", "pages/00_Edit_Questionnaire.py"))

elif role == 'arbitrator':
    cards.extend([
        ("✏️", "Phase 2 Configuration", "Edit Pre-Hearing Questionnaire", "pages/00_Edit_Questionnaire.py"),
        ("📝", "Drafting Engine", "Generate Procedural Order No. 1", "pages/01_Drafting_Engine.py"),
        ("📂", "Document Production", "Review Requests & Redfern Sched.", "pages/02_Doc_Production.py"),
        ("📅", "Smart Timeline", "Manage Deadlines & Logistics", "pages/03_Smart_Timeline.py"),
        ("💰", "Cost Management", "Track Deposits & Allocations", "pages/04_Cost_Management.py")
    ])

elif role in ['claimant', 'respondent']:
    cards.extend([
        ("📝", "Procedural Forms", "Fill Active Questionnaires", "pages/00_Fill_Questionnaire.py"),
        ("📂", "Document Production", "Submit Requests & Objections", "pages/02_Doc_Production.py"),
        ("📅", "Case Timeline", "View Schedule & Request Delays", "pages/03_Smart_Timeline.py"),
        ("💰", "Cost Submission", "Upload Costs & Final Subs.", "pages/04_Cost_Management.py")
    ])

cols = st.columns(3)
for i, (icon, title, desc, link) in enumerate(cards):
    with cols[i % 3]:
        with st.container(border=True):
            st.write(f"### {icon} {title}")
            st.caption(desc)
            if st.button(f"Open {title}", key=f"btn_{i}", use_container_width=True):
                st.switch_page(link)

st.divider()
st.caption("PROCEED Arbitration Management System | Powered by Google Cloud")
