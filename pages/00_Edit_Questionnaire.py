import streamlit as st
from db import load_structure, save_structure, reset_database

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    
    st.divider()
    st.caption("ADMIN ACTIONS")
    # THE "NOT FOREVER" SOLUTION:
    if st.button("🔄 Restore Default Questions", help="Bring back all deleted questions from the master bank.", use_container_width=True):
        save_structure({"initial_setup": True}) # Wipes the edits, forcing defaults to load
        st.toast("Questions restored!")
        st.rerun()

st.title("✏️ Questionnaire Editor")
st.caption("Uncheck 'Include' to remove a question from THIS specific case. Click 'Restore Defaults' to bring them back later.")

# --- MASTER QUESTION BANK (Sources: Your Docx + Your Prompt) ---
DEFAULT_QUESTIONS = [
    # I. GENERAL PROCEDURE
    {"id": "style", "question": "1. Style of Written Submissions", "type": "radio", "options": ["Memorial Style (Simultaneous)", "Pleading Style (Sequential)"]},
    {"id": "bifurcation", "question": "2. Bifurcation of Proceedings", "type": "radio", "options": ["Single Phase (All issues together)", "Request Bifurcation (Liability first)"]},
    {"id": "consolidation", "question": "3. Consolidation & Concurrent Conduct", "type": "radio", "options": ["Stand-alone Arbitration", "Request Consolidation", "Concurrent Conduct"]},
    
    # II. TIMETABLE & DEADLINES
    {"id": "deadline_timezone", "question": "4. Definition of 'Deadline' (Timezone)", "type": "radio", "options": ["Time of the Seat", "Time of Presiding Arbitrator", "Time of Filing Party"]},
    {"id": "extensions", "question": "5. Protocol for Time Extensions", "type": "selectbox", "options": ["Standard (Good cause)", "Strict (Exceptional only)", "Flexible (Party agreed)"]},
    
    # III. DOCUMENTS & EVIDENCE
    {"id": "doc_prod", "question": "6. Document Production Guidelines", "type": "selectbox", "options": ["IBA Rules (Binding)", "IBA Rules (Guidelines only)", "Prague Rules", "None", "Other"]},
    {"id": "limits", "question": "7. Limitations on Document Requests", "type": "radio", "options": ["Standard (IBA)", "Capped (e.g. 20 requests)", "None"]},
    {"id": "privilege_std", "question": "8. Standard of Legal Privilege", "type": "radio", "options": ["Rules of the Seat", "Rules of Party claiming privilege", "Strictest applicable rule"]},
    {"id": "privilege_logs", "question": "9. Privilege Logs", "type": "radio", "options": ["Detailed Privilege Log required", "Not required unless ordered"]},
    {"id": "shredding", "question": "10. Data Retention / Shredding", "type": "radio", "options": ["Shred immediately upon Final Award", "Retain for limitation period"]},
    
    # IV. WITNESSES & EXPERTS
    {"id": "witness_exam", "question": "11. Witness Examination", "type": "radio", "options": ["Statement stands as direct evidence", "Full direct examination required", "Written statements only"]},
    {"id": "expert_meeting", "question": "12. Meetings of Experts", "type": "radio", "options": ["Mandatory Joint Report", "Independent reports only"]},
    {"id": "expert_hot_tub", "question": "13. Mode of Expert Questioning", "type": "radio", "options": ["Sequential Examination", "Witness Conferencing ('Hot-Tubbing')"]},
    {"id": "expert_reply", "question": "14. Reply Expert Reports", "type": "radio", "options": ["Simultaneous Reply Reports", "No Reply Reports"]},
    
    # V. HEARING LOGISTICS
    {"id": "venue_type", "question": "15. Physical Hearing Venue", "type": "radio", "options": ["At the Seat of Arbitration", "Different Neutral Venue", "Virtual Hearing"]},
    {"id": "interpretation", "question": "16. Interpretation & Translation", "type": "radio", "options": ["Proceedings entirely in English", "Simultaneous Interpretation required"]},
    {"id": "chess_clock", "question": "17. Time Allocation (Chess Clock)", "type": "radio", "options": ["Chess Clock (Fixed split)", "Tribunal Discretion"]},
    {"id": "transcription", "question": "18. Transcription Services", "type": "selectbox", "options": ["Live / Real-time", "Daily Turnaround", "Standard Turnaround", "None"]},
    {"id": "demonstratives", "question": "19. Demonstrative Exhibits", "type": "radio", "options": ["Exchange 24h before use", "Exchange immediately prior", "No specific rule"]},
    {"id": "post_hearing", "question": "20. Post-Hearing Briefs", "type": "radio", "options": ["Oral Closings only", "Written Post-Hearing Briefs", "Costs Submissions only"]},
    
    # VI. SUBMISSIONS & AWARD
    {"id": "page_limits", "question": "21. Page Limits for Submissions", "type": "radio", "options": ["No specific limits", "Strict page limits apply", "Limits on legal argument only"]},
    {"id": "ai_guidelines", "question": "22. AI Guidelines", "type": "radio", "options": ["Adopt CIArb Guidelines on AI", "No specific guidelines"]},
    {"id": "sign_award", "question": "23. Electronic Signature of Award", "type": "radio", "options": ["Electronic Signature accepted", "Wet Ink (Hard Copy) required"]},
    {"id": "currency", "question": "24. Currency of Award", "type": "radio", "options": ["Currency of Contract", "Currency of Costs Incurred", "Tribunal Discretion"]},
    {"id": "interest", "question": "25. Interest Calculation", "type": "radio", "options": ["Applicable Law", "Simple Interest", "Compound Interest"]},
    {"id": "last_submission", "question": "26. Definition of 'Last Submission'", "type": "radio", "options": ["Final Brief on Merits", "Final Filing including Costs"]},
    
    # VII. ADMIN & FUNDING
    {"id": "secretary", "question": "27. Tribunal Secretary Appointment", "type": "radio", "options": ["Consent to Appointment", "Object to Appointment"]},
    {"id": "sec_fees", "question": "28. Secretary Fees (if appointed)", "type": "radio", "options": ["£75 - £175 / hr (LCIA Standard)", "£100 - £250 / hr (Draft PO1)"]},
    {"id": "funding", "question": "29. Third-Party Funding Disclosure", "type": "radio", "options": ["No third-party funding", "Funding is in place"]},
    
    # VIII. DATA ENTRY (Placed at end as requested)
    {"id": "reps_info", "question": "30. Authorised Representatives (Contact Details)", "type": "text_area", "options": ["Enter Name, Firm, and Email..."]}
]

# --- LOAD DATA ---
current_structure = load_structure()
# If database is reset/empty, load the master list
if not current_structure:
    current_structure = DEFAULT_QUESTIONS

# --- EDITOR UI ---
with st.form("editor_form"):
    updated_structure = []
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 2, 1])
            
            # Question Text
            new_q_text = c1.text_input(f"Question #{i+1}", value=q['question'], key=f"q_{i}")
            
            # Type Selector
            type_map = {"radio": "List (Radio)", "selectbox": "Dropdown", "text_area": "Text Input"}
            rev_map = {"List (Radio)": "radio", "Dropdown": "selectbox", "Text Input": "text_area"}
            curr_type = type_map.get(q['type'], "List (Radio)")
            new_type_disp = c2.selectbox("Type", ["List (Radio)", "Dropdown", "Text Input"], index=["List (Radio)", "Dropdown", "Text Input"].index(curr_type), key=f"t_{i}")
            new_type = rev_map[new_type_disp]
            
            # Include/Delete Toggle
            is_included = c3.checkbox("✅ Include", value=True, key=f"inc_{i}", help="Uncheck to hide this question from the parties for THIS case.")
            
            # Options (Only if not text input)
            if new_type != "text_area":
                options_str = ", ".join(q.get('options', []))
                new_options_str = st.text_area(f"Options (comma separated)", value=options_str, key=f"o_{i}", height=68)
                new_options = [opt.strip() for opt in new_options_str.split(",")]
            else:
                new_options = ["Text Input"] # Placeholder
            
            if is_included:
                updated_structure.append({
                    "id": q['id'], "question": new_q_text, "type": new_type, "options": new_options
                })
    
    if st.form_submit_button("💾 Publish Questionnaire to Parties", type="primary"):
        save_structure(updated_structure)
        st.success(f"✅ Published {len(updated_structure)} questions to the active case.")
