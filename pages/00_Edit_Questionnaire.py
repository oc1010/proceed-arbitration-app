import streamlit as st
import pandas as pd
from db import load_structure, save_structure, set_release_status, get_release_status

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

# --- AUTHENTICATION & ACCESS CONTROL ---
role = st.session_state.get('user_role')
if role not in ['lcia', 'arbitrator']:
    st.error("Access Denied. Only LCIA or Arbitrator can edit questionnaires.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR (Persistent) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
        
    st.divider()
    if st.button("Logout"): 
        st.session_state['user_role'] = None
        st.switch_page("main.py")

# --- MAIN CONTENT ---
# Determine which questionnaire to edit based on role
phase = "phase1" if role == 'lcia' else "phase2"
title = "Phase 1: Pre-Tribunal Questionnaire" if role == 'lcia' else "Phase 2: Pre-Hearing Questionnaire"

st.title(f"✏️ {title}")
st.caption("Add or modify questions for the parties. Once finalized, click 'Release' to make it visible to them.")

# --- LOAD DATA ---
questions = load_structure(phase)
status = get_release_status()
is_released = status.get(phase, False)

# --- RELEASE STATUS BANNER ---
st.divider()
c1, c2 = st.columns([3, 1])

with c1:
    if is_released:
        st.success("✅ **Status: RELEASED** | Parties can currently view and answer this questionnaire.")
    else:
        st.warning("⚠️ **Status: DRAFT** | This is hidden from parties. Release it when ready.")

with c2:
    if is_released:
        if st.button("Recall (Un-publish)", use_container_width=True):
            set_release_status(phase, False)
            st.rerun()
    else:
        if st.button("🚀 Release to Parties", type="primary", use_container_width=True):
            set_release_status(phase, True)
            st.rerun()

st.divider()

# --- EDITOR ---
if not questions:
    # Seed with default example if empty
    questions = [
        {"id": "q1", "question": "Example Question 1?", "type": "text"},
        {"id": "q2", "question": "Example Question 2?", "type": "date"}
    ]

# Convert to DataFrame for Editor
df = pd.DataFrame(questions)

st.subheader("Question Editor")
edited_df = st.data_editor(
    df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "id": st.column_config.TextColumn("ID (Unique)", disabled=True, help="Generated automatically"),
        "question": st.column_config.TextColumn("Question Text", width="large"),
        "type": st.column_config.SelectboxColumn(
            "Input Type", 
            options=["text", "date", "number", "selection"],
            help="Determines the input field type for the user."
        )
    }
)

# --- SAVE LOGIC ---
if st.button("💾 Save Changes"):
    # Convert DataFrame back to list of dicts
    new_data = edited_df.to_dict(orient="records")
    
    # Validation & ID Generation
    for i, q in enumerate(new_data):
        # Generate ID if missing (e.g. new row added)
        if not q.get("id"):
            q["id"] = f"q_{i+1}_{phase}_{int(pd.Timestamp.now().timestamp())}"
        
        # Ensure mandatory fields
        if not q.get("question"):
            q["question"] = "New Question"
        if not q.get("type"):
            q["type"] = "text"
            
    save_structure(new_data, phase)
    st.success("Configuration Saved Successfully.")
    st.rerun()
