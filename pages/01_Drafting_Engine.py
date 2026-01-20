import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline, reset_database
import pandas as pd

st.set_page_config(page_title="Procedural Order No. 1", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
        st.switch_page("main.py")
    st.divider()
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    st.divider()
    if st.button("⚠️ Factory Reset", type="secondary", use_container_width=True):
        reset_database()
        st.rerun()

st.title("Procedural Order No. 1 | Drafting Engine")

# --- CONTEXT DEFAULTS ---
context = {
    'Case_Number': 'ARB/24/001', 'seat_of_arbitration': 'London', 
    'meeting_date': date.today().strftime("%d %B %Y"), 'governing_law_of_contract': 'English Law',
    'claimant_rep_1': '', 'claimant_rep_2': '', 'Contact_details_of_Claimant': '', 
    'respondent_rep_1': '', 'respondent_rep_2': '', 'Contact_details_of_Respondent': '',
    'Contact_details_of_Arbitrator_1': '', 'Contact_details_of_Arbitrator_2': '', 'Contact_details_of_Arbitrator_3_Presiding': '',
    'name_of_tribunal_secretary': '', 'secretary_hourly_rate': '',
    'limits_submission': '', 'max_filename_len': '50 chars', 'deadline_timezone': '17:00 London', 
    'time_produce_docs': '14 days', 'time_shred_docs': '6 months', 'time_notify_oral': '45 days',
    'time_appoint_interpreter': '14 days', 'time_hearing_bundle': '14 days before', 
    'time_submit_exhibits': '24 hours', 'date_decide_venue': '3 months prior',
    'place_in_person': 'IDRC London', 'physical_venue_city': 'London', 'hearing_hours': '09:30 - 17:30',
    'schedule_oral_hearing': '', 'prehearing_matters': '', 'time_abbreviations': '7 days',
    'time_confirm_contact': '7 days', 'time_notify_counsel': 'immediately'
}
for i in range(1, 16): context[f"deadline_{i:02d}"] = "TBD"

# --- TOPIC MAP (Readable Names) ---
TOPIC_MAP = {
    "style": "1. Submission Style", "bifurcation": "2. Bifurcation", "doc_prod": "3. Doc Guidelines",
    "limits": "4. Doc Limits", "witness_exam": "5. Witness Exam", "platform": "6. Platform",
    "bundling": "7. Bundling", "gdpr": "8. GDPR", "cost_allocation": "9. Cost Alloc.",
    "counsel_fees": "10. Counsel Fees", "internal_costs": "11. Internal Costs", "deposits": "12. Deposits",
    "secretary": "13. Secretary", "sec_fees": "14. Sec Fees", "extensions": "15. Extensions",
    "funding": "16. Funding", "deadline_timezone": "17. Timezone", "physical_venue_preference": "18. Venue Pref.",
    "interpretation": "19. Interpretation", "limits_submission": "20. Page Limits", "ai_guidelines": "21. AI Rules",
    "consolidation": "22. Consolidation", "chess_clock": "23. Chess Clock", "post_hearing": "24. Post-Hearing",
    "time_shred_docs": "25. Shredding", "expert_meeting": "26. Expert Meetings", "expert_hot_tub": "27. Hot-Tubbing",
    "expert_reply": "28. Reply Experts", "sign_award": "29. Sign Award", "currency": "30. Currency",
    "interest": "31. Interest", "last_submission": "32. Last Sub. Def.", "transcription": "33. Transcription",
    "demonstratives": "34. Demonstratives", "privilege_std": "35. Privilege Std", "privilege_logs": "36. Privilege Logs",
    "reps_info": "37. Representatives"
}

responses = load_responses()

def display_hint(key):
    c = responses.get('claimant', {}).get(key, "Pending")
    r = responses.get('respondent', {}).get(key, "Pending")
    if c == "Pending" and r == "Pending": st.info("Waiting...", icon="⏳")
    elif c == r: st.success(f"Agreed: {c[:50]}...") # Truncate long text in hint
    else: st.warning(f"Conflict.")

def save_schedule(dates, style):
    # Standard timeline logic (omitted for brevity, same as previous)
    events = [{"date": str(dates['d1']), "event": "Statement of Case", "owner": "Claimant", "status": "Pending"}]
    save_timeline(events)
    return len(events)

# --- TABS ---
tabs = st.tabs(["Preferences", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])

with tabs[0]:
    st.subheader("Questionnaire Responses")
    try:
        c_data = responses.get('claimant', {})
        r_data = responses.get('respondent', {})
        all_keys = list(set(list(c_data.keys()) + list(r_data.keys())))
        
        if not all_keys:
            st.info("No data submitted.")
        else:
            summary_data = []
            # Sort keys based on question number if possible, or just list
            for k in sorted(all_keys):
                topic = TOPIC_MAP.get(k, k)
                c_val = c_data.get(k, "Pending")
                r_val = r_data.get(k, "Pending")
                # Clean up "Option A:" prefixes for the table
                c_clean = c_val.split(".")[0] if "." in c_val else c_val
                r_clean = r_val.split(".")[0] if "." in r_val else r_val
                
                match = "✅" if c_val == r_val and c_val != "Pending" else "❌"
                summary_data.append({"Topic": topic, "Claimant": c_clean, "Respondent": r_clean, "Match": match})
            
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error loading table: {e}")

# The rest of the tabs (General, Parties, etc.) remain as they were, 
# just ensure display_hint calls use the new keys (like 'physical_venue_preference' etc.)
# ...
