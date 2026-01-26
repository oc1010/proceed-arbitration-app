import streamlit as st
import pandas as pd
from db import load_responses

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

# --- AUTHENTICATION CONFIGURATION ---
# Simple mock authentication for demonstration purposes.
# In a real production app, this would check against a secure database.
USERS = {
    "lcia": "lcia123", 
    "arbitrator": "arbitrator123", 
    "claimant": "party123", 
    "respondent": "party123"
}

# Initialize Session State for User Role if not present
if 'user_role' not in st.session_state: 
    st.session_state['user_role'] = None

def login():
    """Validates user credentials and sets the session state."""
    u = st.session_state.get("username", "").strip().lower()
    p = st.session_state.get("password", "").strip()
    if USERS.get(u) == p: 
        st.session_state['user_role'] = u
    else: 
        st.error("Invalid Credentials")

def logout():
    """Clears the session state and reloads the app."""
    st.session_state['user_role'] = None
    st.rerun()

# --- LOGIN SCREEN ---
# If no user is logged in, show the login form and stop execution of the rest of the page.
if st.session_state['user_role'] is None:
    st.title("PROCEED | Secure Gateway")
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        with st.container(border=True):
            st.subheader("System Access")
            st.info("Please log in to access your case file.")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            if st.button("Log In", type="primary", use_container_width=True): 
                login()
                st.rerun()
    st.stop()

# --- LOGGED IN USER CONTEXT ---
role = st.session_state['user_role']

# --- SIDEBAR NAVIGATION (Persistent) ---
# This sidebar appears on the Home page and should be replicated in pages for consistency.
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications") # New Notifications Tab
    
    # Dynamic Navigation Links based on Role
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
    
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 PO1 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
        
    elif role in ['claimant', 'respondent']:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")

    st.divider()
    if st.button("Logout", use_container_width=True): 
        logout()

# --- MAIN DASHBOARD CONTENT ---
st.title(f"Welcome, {role.title()}")
st.markdown("### Case Dashboard: ARB/24/001")
st.info("Select a module below to proceed with your case management tasks.")

# --- DASHBOARD CARDS CONFIGURATION ---
# Define the available modules for each role.
# Format: (Icon, Title, Description, Page Path)
cards = []

# Base card for everyone
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

# --- RENDER DASHBOARD GRID ---
# Uses a 3-column layout to display the cards cleanly.
cols = st.columns(3)
for i, (icon, title, desc, link) in enumerate(cards):
    with cols[i % 3]: # Distribute cards across 3 columns
        with st.container(border=True):
            st.write(f"### {icon} {title}")
            st.caption(desc)
            if st.button(f"Open {title}", key=f"btn_{i}", use_container_width=True):
                st.switch_page(link)

st.divider()
st.caption("PROCEED Arbitration Management System | v2.0")
