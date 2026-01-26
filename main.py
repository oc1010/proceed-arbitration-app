import streamlit as st
from db import load_responses

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

# --- AUTH ---
USERS = {"lcia": "lcia123", "arbitrator": "arbitrator123", "claimant": "party123", "respondent": "party123"}
if 'user_role' not in st.session_state: st.session_state['user_role'] = None

def login():
    u = st.session_state.get("username", "").strip().lower()
    p = st.session_state.get("password", "").strip()
    if USERS.get(u) == p: st.session_state['user_role'] = u
    else: st.error("Invalid Credentials")

def logout(): st.session_state['user_role'] = None; st.rerun()

if st.session_state['user_role'] is None:
    st.title("PROCEED | Secure Gateway")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            if st.button("Log In", type="primary", use_container_width=True): login(); st.rerun()
    st.stop()

# --- SIDEBAR ---
role = st.session_state['user_role']
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications") # NEW
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    else:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Qs")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    
    st.divider()
    if st.button("Logout", use_container_width=True): logout()

# --- DASHBOARD ---
st.title(f"Welcome, {role.title()}")
cards = []

# Base card for everyone
cards.append(("🔔", "Notifications", "View Alerts & Messages", "pages/05_Notifications.py"))

if role == 'lcia':
    cards.append(("✏️", "Phase 1 Configuration", "Edit Pre-Tribunal Questionnaires", "pages/00_Edit_Questionnaire.py"))
elif role == 'arbitrator':
    cards.extend([
        ("✏️", "Phase 2 Config", "Edit Qs", "pages/00_Edit_Questionnaire.py"),
        ("📝", "Drafting Engine", "Generate PO1", "pages/01_Drafting_Engine.py"),
        ("📂", "Document Production", "Manage Redfern", "pages/02_Doc_Production.py"),
        ("📅", "Smart Timeline", "Deadlines & Logistics", "pages/03_Smart_Timeline.py"),
        ("💰", "Costs", "Track Deposits", "pages/04_Cost_Management.py")
    ])
else:
    cards.extend([
        ("📝", "Procedural Forms", "Fill Active Qs", "pages/00_Fill_Questionnaire.py"),
        ("📂", "Document Production", "Requests & Objections", "pages/02_Doc_Production.py"),
        ("📅", "Case Timeline", "Schedule & Delays", "pages/03_Smart_Timeline.py"),
        ("💰", "Cost Submission", "Upload Costs", "pages/04_Cost_Management.py")
    ])

cols = st.columns(3)
for i, (icon, title, desc, link) in enumerate(cards):
    with cols[i % 3]:
        with st.container(border=True):
            st.write(f"### {icon} {title}")
            st.caption(desc)
            if st.button(f"Open {title}", key=f"btn_{i}", use_container_width=True): st.switch_page(link)
