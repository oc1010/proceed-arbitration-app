import streamlit as st
import pandas as pd
from db import create_new_case, get_active_case_id, load_full_config, verify_case_access, get_all_cases_metadata, db

st.set_page_config(page_title="PROCEED | Arbitration Cloud", layout="wide")

# --- AUTH & STATE SETUP ---
if 'user_role' not in st.session_state: st.session_state['user_role'] = None
if 'active_case_id' not in st.session_state: st.session_state['active_case_id'] = None
if 'is_lcia_admin' not in st.session_state: st.session_state['is_lcia_admin'] = False

# ==============================================================================
# 1. THE LOBBY (LOGIN SCREEN)
# ==============================================================================
if not st.session_state['active_case_id'] and not st.session_state['is_lcia_admin']:
    st.title("⚖️ PROCEED: Arbitration Cloud")
    st.caption("Secure Global Arbitration Management Platform")
    
    col1, col2 = st.columns(2)
    
    # --- CARD 1: PARTY LOGIN ---
    with col1:
        with st.container(border=True):
            st.subheader("🔑 Party Login")
            st.write("Access an ongoing arbitration case.")
            
            case_input = st.text_input("Case ID", placeholder="LCIA-170...")
            pin_input = st.text_input("Access PIN", type="password", placeholder="****")
            role_input = st.selectbox("Select Role", ["Claimant", "Respondent", "Arbitrator"])
            
            if st.button("Enter Case Workspace", type="primary"):
                if not db:
                    st.error("Database connection failed.")
                else:
                    valid, meta = verify_case_access(case_input, pin_input)
                    if valid:
                        st.session_state['active_case_id'] = case_input
                        st.session_state['user_role'] = role_input.lower()
                        st.success(f"Welcome to {meta['case_name']}")
                        st.rerun()
                    else:
                        st.error("Invalid Case ID or PIN.")

    # --- CARD 2: LCIA ADMIN LOGIN ---
    with col2:
        with st.container(border=True):
            st.subheader("🏛️ LCIA Registrar")
            st.write("Administrative Console access.")
            
            admin_pass = st.text_input("Registrar Password", type="password")
            
            if st.button("Login as Registrar"):
                # Hardcoded for Hackathon Demo
                if admin_pass == "lcia123": 
                    st.session_state['is_lcia_admin'] = True
                    st.session_state['user_role'] = 'lcia'
                    st.rerun()
                else:
                    st.error("Incorrect Password.")
    st.stop()


# ==============================================================================
# 2. LCIA REGISTRAR DASHBOARD (MASTER VIEW)
# ==============================================================================
if st.session_state['is_lcia_admin'] and not st.session_state['active_case_id']:
    st.title("🏛️ LCIA Registrar Console")
    st.write("Global overview of active arbitration matters.")
    
    # 2A. ACTIVE CASES TABLE
    all_cases = get_all_cases_metadata()
    
    if all_cases:
        st.write("### 📂 Active Cases")
        df = pd.DataFrame(all_cases)
        # Display clean table
        display_df = df[['case_id', 'case_name', 'status', 'created_at']].copy()
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Selector to enter a case
        c1, c2 = st.columns([3, 1])
        selected_id = c1.selectbox("Select Case to Manage", [c['case_id'] for c in all_cases])
        if c2.button("Manage Selected Case"):
            st.session_state['active_case_id'] = selected_id
            st.rerun()
    else:
        st.info("No active cases found in the database.")

    st.divider()

    # 2B. REGISTER NEW CASE
    st.markdown("### ➕ Initiate New Proceedings")
    with st.container(border=True):
        with st.form("reg_case"):
            c_name = st.text_input("Case Name (e.g. Acme v. Wayne)")
            c1, c2 = st.columns(2)
            c_email = c1.text_input("Claimant Email")
            r_email = c2.text_input("Respondent Email")
            c3, c4 = st.columns(2)
            access_pin = c3.text_input("Set Access PIN (for Parties)", value="1234")
            
            # THE FIX: Handles the redirect correctly now
            if st.form_submit_button("🚀 Initiate Proceedings", type="primary"):
                if c_name:
                    new_id = create_new_case(c_name, c_email, r_email, access_pin)
                    # AUTO-LOGIN TO THE NEW CASE
                    st.session_state['active_case_id'] = new_id
                    st.success(f"Case {new_id} Created! Redirecting...")
                    st.rerun()
                else:
                    st.error("Case Name is required.")
                
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()
    
    st.stop()


# ==============================================================================
# 3. CASE WORKSPACE (USER DASHBOARD)
# ==============================================================================
# This loads when 'active_case_id' is set (Either by Party Login or LCIA Selection)

role = st.session_state['user_role']
case_data = load_full_config()

if not case_data:
    st.error("Error loading case data. Please return to lobby.")
    if st.button("Return to Lobby"): 
        st.session_state['active_case_id'] = None
        st.rerun()
    st.stop()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.header(case_data['meta'].get('case_name', 'Unnamed Case'))
    st.caption(f"ID: {st.session_state['active_case_id']}")
    st.write(f"Role: **{role.upper()}**")
    st.divider()
    
    st.page_link("main.py", label="🏠 Workspace Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")

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
    if st.button("Exit Workspace"):
        st.session_state['active_case_id'] = None
        st.rerun()

# --- MAIN WORKSPACE CARDS ---
st.title(f"Workspace: {role.title()}")
st.info(f"Status: {case_data['meta']['status']}")

cards = []
cards.append(("🔔", "Notifications", "View Alerts & Messages", "pages/05_Notifications.py"))

if role == 'lcia':
    st.write("### 🏛️ Institution Actions")
    st.write("Configure and send the Pre-Tribunal Questionnaire to parties.")
    cards.append(("✏️", "Phase 1 Configuration", "Edit & Send Pre-Tribunal Questionnaire", "pages/00_Edit_Questionnaire.py"))

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
