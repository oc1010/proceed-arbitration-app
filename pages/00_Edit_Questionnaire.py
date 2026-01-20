import streamlit as st
from db import load_structure, save_structure

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

# --- SIDEBAR ---
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

st.title("✏️ Questionnaire Editor")
st.caption("Customize the questions sent to the parties. Changes are saved to the Cloud instantly.")

# --- COMPREHENSIVE QUESTION BANK ---
DEFAULT_QUESTIONS = [
    # I. GENERAL PROCEDURE
    {"id": "style", "question": "1. Style of Written Submissions", "type": "radio", "options": ["Memorial Style (Simultaneous, Front-loaded)", "Pleading Style (Sequential, Traditional)"]},
    {"id": "bifurcation", "question": "2. Bifurcation of Proceedings", "type": "radio", "options": ["Single Phase (All issues together)", "Request Bifurcation (Liability first)"]},
    {"id": "consolidation", "question": "3. Consolidation & Concurrent Conduct (Art 22A)", "type": "radio", "options": ["Stand-alone Arbitration", "Request Consolidation (Single proceeding)", "Concurrent Conduct (Separate awards, synced timetable)"]},
    
    # II. TIMETABLE & DEADLINES
    {"id": "deadline_def", "question": "4. Definition of 'Deadline' (Timezone)", "type": "radio", "options": ["Time of the Seat (e.g. 17:00 London)", "Time of Presiding Arbitrator", "Time of Filing Party"]},
    {"id": "extensions", "question": "5. Protocol for Time Extensions", "type": "selectbox", "options": ["Standard (Good cause required)", "Strict (Exceptional circumstances only)", "Flexible (Party agreement allowed)"]},
    
    # III. DOCUMENTS & EVIDENCE
    {"id": "doc_prod", "question": "6. Document Production Guidelines", "type": "selectbox", "options": ["IBA Rules (Binding)", "IBA Rules (Guidelines only)", "Prague Rules", "None", "Other"]},
    {"id": "limits", "question": "7. Limitations on Document Requests", "type": "radio", "options": ["Standard (No specific limit)", "Capped (e.g. 20 requests per party)", "None (No production phase)"]},
    {"id": "privilege_std", "question": "8. Standard of Legal Privilege", "type": "radio", "options": ["Rules of the Seat", "Rules of Party claiming privilege (Closest connection)", "Strictest applicable rule"]},
    {"id": "privilege_logs", "question": "9. Privilege Logs", "type": "radio", "options": ["Detailed Privilege Log required", "Not required unless ordered"]},
    {"id": "shredding", "question": "10. Data Retention / Shredding", "type": "radio", "options": ["Shred immediately upon Final Award", "Retain for limitation period (e.g. 28 days)"]},
    
    # IV. WITNESSES & EXPERTS
    {"id": "witness_exam", "question": "11. Witness Examination", "type": "radio", "options": ["Statement stands as direct evidence (No direct exam)", "Full direct examination required", "Written statements only (No hearing)"]},
    {"id": "expert_meeting", "question": "12. Meetings of Experts", "type": "radio", "options": ["Mandatory Joint Report before hearing", "Independent reports only"]},
    {"id": "expert_hot_tub", "question": "13. Mode of Expert Questioning", "type": "radio", "options": ["Sequential Examination", "Witness Conferencing ('Hot-Tubbing')"]},
    {"id": "expert_reply", "question": "14. Reply Expert Reports", "type": "radio", "options": ["Simultaneous Reply Reports allowed", "No Reply Reports (unless new factual evidence)"]},
    
    # V. HEARING LOGISTICS
    {"id": "venue_type", "question": "15. Physical Hearing Venue", "type": "radio", "options": ["At the Seat of Arbitration", "Different Neutral Venue (e.g. IDRC London)", "Virtual Hearing"]},
    {"id": "interpretation", "question": "16. Interpretation & Translation", "type": "radio", "options": ["Proceedings entirely in English", "Simultaneous Interpretation required"]},
    {"id": "chess_clock", "question": "17. Time Allocation (Chess Clock)", "type": "radio", "options": ["Chess Clock (Fixed split)", "Tribunal Discretion (Per witness)"]},
    {"id": "transcription", "question": "18. Transcription Services", "type": "selectbox", "options": ["Live / Real-time", "Daily Turnaround", "Standard Turnaround (1-2 weeks)", "None"]},
    {"id": "demonstratives", "question": "19. Demonstrative Exhibits", "type": "radio", "options": ["Exchange 24h before use", "Exchange immediately prior", "No specific rule"]},
    {"id": "post_hearing", "question": "20. Post-Hearing Briefs", "type": "radio", "options": ["Oral Closings only", "Written Post-Hearing Briefs required", "Costs Submissions only"]},
    
    # VI. SUBMISSIONS & AWARD
    {"id": "page_limits", "question": "21. Page Limits for Submissions", "type": "radio", "options": ["No specific limits", "Strict page limits apply", "Limits on legal argument only"]},
    {"id": "ai_guidelines", "question": "22. AI Guidelines", "type": "radio", "options": ["Adopt CIArb Guidelines on AI", "No specific guidelines"]},
    {"id": "sign_award", "question": "23. Electronic Signature of Award", "type": "radio", "options": ["Electronic Signature accepted", "Wet Ink (Hard Copy) required"]},
    {"id": "currency", "question": "24. Currency of Award", "type": "radio", "options": ["Currency of Contract", "Currency of Costs Incurred", "Tribunal Discretion"]},
    {"id": "interest", "question": "25. Interest Calculation", "type": "radio", "options": ["Applicable Law", "Simple Interest", "Compound Interest"]},
    {"id": "last_submission", "question": "26. Definition of 'Last Submission' (for 3-month deadline)", "type": "radio", "options": ["Final Brief on Merits", "Final Filing including Costs"]},
    
    # VII. TRIBUNAL & PARTIES
    {"id": "secretary", "question": "27. Tribunal Secretary Appointment", "type": "radio", "options": ["Consent to Appointment", "Object to Appointment"]},
    {"id": "sec_fees", "question": "28. Secretary Fees (if appointed)", "type": "radio", "options": ["£75 - £175 / hr (LCIA Standard)", "£100 - £250 / hr (Draft PO1)"]},
    {"id": "funding", "question": "29. Third-Party Funding Disclosure", "type": "radio", "options": ["No third-party funding", "Funding is in place (Disclose immediately)"]}
]

current_structure = load_structure()
# Reset to default if it's the old short version
if not current_structure or len(current_structure) < 10:
    current_structure = DEFAULT_QUESTIONS

with st.form("editor_form"):
    updated_structure = []
    st.markdown("### Questions Configuration")
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            new_q_text = c1.text_input(f"Question #{i+1}", value=q['question'], key=f"q_{i}")
            
            # User-friendly names
            type_map = {"radio": "List View", "selectbox": "Dropdown"}
            rev_map = {"List View": "radio", "Dropdown": "selectbox"}
            
            curr_type = type_map.get(q['type'], "List View")
            new_type_disp = c2.selectbox("Type", ["List View", "Dropdown"], index=0 if curr_type=="List View" else 1, key=f"t_{i}")
            new_type = rev_map[new_type_disp]
            
            options_str = ", ".join(q['options'])
            new_options_str = st.text_area(f"Options #{i+1}", value=options_str, key=f"o_{i}")
            
            updated_structure.append({
                "id": q['id'], "question": new_q_text, "type": new_type, 
                "options": [opt.strip() for opt in new_options_str.split(",")]
            })
    
    if st.form_submit_button("💾 Publish to Parties", type="primary"):
        save_structure(updated_structure)
        st.success("✅ Updated Questionnaire published!")
