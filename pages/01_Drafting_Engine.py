import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline, reset_database
import os
import pandas as pd

st.set_page_config(page_title="Procedural Order No. 1", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied.")
    st.stop()

with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
        st.switch_page("main.py")
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    
    st.divider()
    st.caption("ADMIN")
    if st.button("⚠️ Factory Reset", help="Wipes Timeline & Responses.", type="secondary", use_container_width=True):
        reset_database()
        st.toast("System Reset!", icon="🗑️")
        st.rerun()

st.title("Procedural Order No. 1 | Drafting Engine")

# --- READABLE TOPIC MAP ---
TOPIC_MAP = {
    "style": "Written Submission Style", "bifurcation": "Bifurcation", "consolidation": "Consolidation",
    "deadline_timezone": "Timezone Definition", "extensions": "Extension Protocol", "doc_prod": "Doc Production Rules",
    "limits": "Doc Request Limits", "privilege_std": "Privilege Standard", "privilege_logs": "Privilege Logs",
    "shredding": "Data Shredding", "witness_exam": "Witness Examination", "expert_meeting": "Expert Meetings",
    "expert_hot_tub": "Expert Hot-Tubbing", "expert_reply": "Reply Expert Reports", "venue_type": "Physical Venue",
    "interpretation": "Interpretation", "chess_clock": "Chess Clock", "transcription": "Transcription",
    "demonstratives": "Demonstratives", "post_hearing": "Post-Hearing Briefs", "page_limits": "Page Limits",
    "ai_guidelines": "AI Guidelines", "sign_award": "Award Signature", "currency": "Award Currency",
    "interest": "Interest Calc", "last_submission": "Last Submission Def", "secretary": "Tribunal Secretary",
    "sec_fees": "Secretary Fees", "funding": "Third-Party Funding", "reps_info": "Authorised Representatives"
}

responses = load_responses()

def display_hint(key):
    c = responses.get('claimant', {}).get(key, "Pending")
    r = responses.get('respondent', {}).get(key, "Pending")
    if c == "Pending" and r == "Pending": st.info("Waiting for parties...", icon="⏳")
    elif c == r: st.success(f"Agreed: {c}")
    else: st.warning(f"Conflict: Claimant '{c}' vs Respondent '{r}'")

# [Insert save_schedule function and Tab logic from previous turn here...]
# (The rest of the file remains the same as my previous response, just ensuring TOPIC_MAP is updated)
# ...
# 1. PREFERENCES TAB (Readable)
# with tabs[0]:
    # ...
            # topic_name = TOPIC_MAP.get(k, k) # This now uses the new comprehensive map
    # ...
