import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_complex_data, load_complex_data, load_structure
import pandas as pd
import os

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    st.divider()
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Doc_Production.py", label="Doc Production")
    st.page_link("pages/03_Smart_Timeline.py", label="Timeline & Logistics")
    st.page_link("pages/04_Cost_Management.py", label="Cost Management")
    st.divider()
    if st.button("⚠️ Factory Reset", type="secondary"):
        from db import reset_database
        reset_database()
        st.rerun()

st.title("Procedural Order No. 1 | Drafting Engine")

# --- 1. INITIALIZE SESSION STATE (Anti-Jump Fix) ---
DEFAULTS = {
    'de_case_number': 'ARB/24/001',
    'de_seat': 'London',
    'de_law': 'English Law',
    'de_meeting_date': date.today(), # FIXED: Unique key for meeting date
    'de_claimant_rep1': '', 'de_claimant_rep2': '',
    'de_claimant_addr': '', 'de_claimant_contact': '',
    'de_resp_rep1': '', 'de_resp_rep2': '',
    'de_resp_addr': '', 'de_resp_contact': '',
    'de_arb1': '', 'de_arb2': '', 'de_arb3': '',
    'de_sec_name': '', 'de_sec_rate': '',
    'de_limits': '', 'de_file_len': '50 chars',
    'de_timezone': '17:00 London',
    'de_time_docs': '14 days', 'de_time_shred': '6 months',
    'de_time_oral': '45 days', 'de_time_interp': '14 days',
    'de_time_bundle': '14 days before', 'de_time_exhibits': '24 hours',
    'de_date_venue': '3 months prior',
    'de_venue_name': 'IDRC London', 'de_venue_city': 'London',
    'de_hours': '09:30 - 17:30',
    'de_agenda': '', 'de_prehear': '',
    'de_time_abbr': '7 days', 'de_time_contact': '7 days', 'de_time_new_counsel': 'immediately',
    'de_style': 'Memorial', 
    'de_bifurc_status': 'not bifurcated',
    'de_inst': 'LCIA',
    # Timetable Dates
    'de_d1': date.today(), 
    'de_d2': date.today() + timedelta(weeks=4),
    'de_d3': date.today() + timedelta(weeks=6), 
    'de_d8': date.today() + timedelta(weeks=10),
    'de_d9': date.today() + timedelta(weeks=14), 
    'de_d10': date.today() + timedelta(weeks=18),
    'de_d12': date.today() + timedelta(weeks=22), 
    'de_d14': date.today() + timedelta(weeks=24)
}

# Initialize state if missing
for key, default_val in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default_val

# --- TOPIC MAP ---
TOPIC_MAP = {
    "style": "1. Style of Written Submissions", 
    "bifurcation": "2. Bifurcation of Proceedings", 
    "doc_prod": "3. Applicable Guidelines (Evidence)", 
    "limits": "4. Limitations on Document Requests", 
    "witness_exam": "5. Witness Examination", 
    "platform": "6. Case Management Platform", 
    "bundling": "7. Electronic Bundling", 
    "gdpr": "8. Data Protection (GDPR)", 
    "cost_allocation": "9. Cost Allocation Methodology", 
    "counsel_fees": "10. Counsel Fees (Recoverability)", 
    "internal_costs": "11. Internal Management Costs", 
    "deposits": "12. Administrative Deposits", 
    "secretary": "13. Tribunal Secretary", 
    "sec_fees": "14. Tribunal Secretary Fees", 
    "extensions": "15. Protocol for Time Extensions", 
    "funding": "16. Third-Party Funding", 
    "deadline_timezone": "17. Definition of 'Deadline'", 
    "physical_venue_preference": "18. Physical Hearing Venue Preference", 
    "interpretation": "19. Interpretation and Translation", 
    "limits_submission": "20. Page Limits for Written Submissions", 
    "ai_guidelines": "21. Artificial Intelligence Guidelines", 
    "consolidation": "22. Consolidation and Concurrent Conduct", 
    "chess_clock": "23. Time Allocation (Chess Clock)", 
    "post_hearing": "24. Post-Hearing Briefs", 
    "time_shred_docs": "25. Destruction of Documents", 
    "expert_meeting": "26. Meetings of Experts", 
    "expert_hot_tub": "27. Mode of Expert Questioning", 
    "expert_reply": "28. Reply Expert Reports", 
    "sign_award": "29. Electronic Signatures on Award", 
    "currency": "30. Currency of the Award", 
    "interest": "31. Interest Calculation", 
    "last_submission": "32. Definition of 'Last Submission'", 
    "transcription": "33. Transcription Services", 
    "demonstratives": "34. Demonstrative Exhibits", 
    "privilege_std": "35. Standard of Legal Privilege", 
    "privilege_logs": "36. Privilege Logs", 
    "reps_info": "16. Authorised Representatives",
    "publication": "38. Publication of the Award",
    "disability": "39. Accommodations for Participants",
    "sustainability": "40. Green Protocols",
    "ethics": "41. Guidelines on Party Representation",
    "mediation": "42. Mediation Window / Settlement"
}

# --- LOAD DATA ---
resp_p1 = load_responses("phase1")
resp_p2 = load_responses("phase2")

# --- HELPER FUNCTIONS ---
def clean_text(text):
    if not text: return "Pending"
    if "**" in text:
        parts = text.split("**")
        if len(parts) > 1:
            extracted = parts[1].strip()
            if extracted.endswith(":"):
                extracted = extracted[:-1]
            return extracted
    return text

def display_hint(key):
    c = resp_p2.get('claimant', {}).get(key, "Pending")
    r = resp_p2.get('respondent', {}).get(key, "Pending")
    topic_title = TOPIC_MAP.get(key, key)
    c_clean = clean_text(c)
    r_clean = clean_text(r)

    if c == "Pending" and r == "Pending": 
        st.info("Waiting for parties...", icon="⏳")
    elif c == r: 
        st.success(f"**{topic_title}**\n\n✅ **Agreed:** {c_clean}", icon="✅")
    else: 
        st.warning(f"**{topic_title}**\n\n⚠️ **Conflict Detected**\n\n* **Claimant wants:** {c_clean}\n* **Respondent wants:** {r_clean}", icon="⚠️")

def sync_timeline_to_phase4(style):
    d1 = st.session_state.de_d1
    d2 = st.session_state.de_d2
    d3 = st.session_state.de_d3
    d8 = st.session_state.de_d8
    
    new_events = [
        {"date": str(d1), "event": "Statement of Case", "owner": "Claimant", "status": "Pending", "logistics": "Submit via Portal"},
        {"date": str(d2), "event": "Statement of Defence", "owner": "Respondent", "status": "Pending", "logistics": "Submit via Portal"},
        {"date": str(d3), "event": "Doc Production Requests", "owner": "Both", "status": "Pending", "logistics": "Use Phase 3 Tab"},
        {"date": str(d8), "event": "Document Production", "owner": "Both", "status": "Pending", "logistics": "Via Portal"},
    ]
    
    if style == "Memorial":
        d9, d10, d12 = st.session_state.de_d9, st.session_state.de_d10, st.session_state.de_d12
        new_events.extend([
            {"date": str(d9), "event": "Statement of Reply", "owner": "Claimant", "status": "Pending", "logistics": "-"},
            {"date": str(d10), "event": "Statement of Rejoinder", "owner": "Respondent", "status": "Pending", "logistics": "-"},
            {"date": str(d12), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending", "logistics": "See Logistics Tab"}
        ])
    else:
        d9, d10, d14 = st.session_state.de_d9, st.session_state.de_d10, st.session_state.de_d14
        new_events.extend([
            {"date": str(d9), "event": "Witness Statements", "owner": "Both", "status": "Pending", "logistics": "-"},
            {"date": str(d10), "event": "Expert Reports", "owner": "Both", "status": "Pending", "logistics": "-"},
            {"date": str(d14), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending", "logistics": "See Logistics Tab"}
        ])
    
    save_complex_data("timeline", new_events)
    return len(new_events)

def render_phase1_table():
    P1_MAP = {
        "p1_duration": "1. Target Procedural Timetable",
        "p1_qual": "2. Arbitrator Availability",
        "p1_early": "3. Early Determination Application",
        "p1_days": "4. Est. Hearing Days",
        "p1_block": "5. Hearing Block Reservation",
        "p1_dates": "6. Blackout Dates",
        "p1_format": "7. Admin Conference Format",
        "p1_hearing": "8. Main Hearing Format",
        "p1_data": "9. Data Protocol"
    }
    
    c_data = resp_p1.get('claimant', {})
    r_data = resp_p1.get('respondent', {})
    
    if not c_data and not r_data:
        st.info("No Phase 1 data found.")
        return

    table_rows = []
    
    for key, topic in P1_MAP.items():
        c_raw = c_data.get(key, "")
        r_raw = r_data.get(key, "")
        c_com = c_data.get(f"{key}_comment", "")
        r_com = r_data.get(f"{key}_comment", "")
        
        c_disp = clean_text(c_raw)
        r_disp = clean_text(r_raw)
        
        status = "⏳"
        if c_raw and r_raw:
            status = "✅" if c_raw == r_raw else "❌"
        
        if c_com: c_disp += " 💬"
        if r_com: r_disp += " 💬"
        
        if c_raw or r_raw:
            table_rows.append({
                "Match?": status,
                "Question": topic,
                "Claimant": c_disp,
                "Respondent": r_disp,
                "_c_com": c_com,
                "_r_com": r_com
            })
            
    if table_rows:
        st.dataframe(
            pd.DataFrame(table_rows)[["Match?", "Question", "Claimant", "Respondent"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Match?": st.column_config.TextColumn("Match?", width="small"),
                "Question": st.column_config.TextColumn("Question", width="medium"),
                "Claimant": st.column_config.TextColumn("Claimant", width="large"),
                "Respondent": st.column_config.TextColumn("Respondent", width="large")
            }
        )
        
        for row in table_rows:
            if row["_c_com"] or row["_r_com"]:
                with st.expander(f"💬 Comments: {row['Question']}"):
                    c1, c2 = st.columns(2)
                    if row["_c_com"]: c1.info(f"**Claimant:** {row['_c_com']}")
                    if row["_r_com"]: c2.warning(f"**Respondent:** {row['_r_com']}")

# --- TABS ---
tabs = st.tabs(["Phase 1 Review", "Phase 2 Analysis", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])

# --- TAB 1: PHASE 1 REVIEW ---
with tabs[0]:
    st.subheader("Review: Pre-Tribunal Questionnaire")
    st.caption("Responses collected by the LCIA prior to your appointment.")
    render_phase1_table()

# --- TAB 2: PHASE 2 ANALYSIS ---
with tabs[1]:
    st.subheader("Analysis: Pre-Hearing Questionnaire")
    c_data = resp_p2.get('claimant', {})
    r_data = resp_p2.get('respondent', {})
    
    structure_p2 = load_structure("phase2")
    q_map_2 = {q['id']: q['question'] for q in structure_p2} if structure_p2 else {}
    
    all_keys = [k for k in list(set(list(c_data.keys()) + list(r_data.keys()))) if not k.endswith("_comment")]
    
    if not all_keys:
        st.info("No Phase 2 data submitted yet.")
    else:
        summary_data = []
        def sort_key(k):
            text = q_map_2.get(k, TOPIC_MAP.get(k, k))
            try: return int(text.split(".")[0])
            except: return 999
            
        for k in sorted(all_keys, key=sort_key):
            topic = q_map_2.get(k, TOPIC_MAP.get(k, k))
            c_val = c_data.get(k, "Pending")
            r_val = r_data.get(k, "Pending")
            c_comm = c_data.get(f"{k}_comment", "")
            r_comm = r_data.get(f"{k}_comment", "")
            
            c_clean = clean_text(c_val)
            r_clean = clean_text(r_val)
            
            if c_comm: c_clean += " 💬"
            if r_comm: r_clean += " 💬"
            
            match = "✅" if c_val == r_val and c_val != "Pending" else "❌"
            
            summary_data.append({
                "Match?": match,
                "Question": topic, 
                "Claimant": c_clean, 
                "Respondent": r_clean,
                "_c_com": c_comm,
                "_r_com": r_comm
            })
        
        st.dataframe(
            pd.DataFrame(summary_data)[["Match?", "Question", "Claimant", "Respondent"]], 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "Match?": st.column_config.TextColumn("Match?", width="small"),
                "Question": st.column_config.TextColumn("Question", width="medium"),
                "Claimant": st.column_config.TextColumn("Claimant", width="large"),
                "Respondent": st.column_config.TextColumn("Respondent", width="large")
            }
        )
        
        st.markdown("### 💬 Party Comments")
        with st.expander("View Detailed Comments"):
            for row in summary_data:
                if row["_c_com"] or row["_r_com"]:
                    st.markdown(f"**{row['Question']}**")
                    if row["_c_com"]: st.info(f"**Claimant:** {row['_c_com']}")
                    if row["_r_com"]: st.warning(f"**Respondent:** {row['_r_com']}")
                    st.divider()

# --- TAB 3: GENERAL ---
with tabs[2]:
    st.subheader("General Details")
    c1, c2 = st.columns(2)
    st.text_input("Case Reference Number", key="de_case_number")
    st.text_input("Seat of Arbitration", key="de_seat")
    
    # FIXED: Unique key 'de_meeting_date' instead of 'de_d1'
    st.date_input("First Procedural Meeting Date", key="de_meeting_date") 
    
    st.text_input("Governing Law", key="de_law")
    st.selectbox("Arbitral Institution", ["LCIA", "ICC", "SIAC", "HKIAC", "ICDR"], key="de_inst")
    
    st.divider()
    st.markdown("#### Procedural Structure")
    display_hint("bifurcation")
    display_hint("consolidation")
    st.selectbox("Bifurcation Status", ["not bifurcated", "bifurcated"], key="de_bifurc_status")

# --- TAB 4: PARTIES ---
with tabs[3]:
    st.subheader("Parties & Representatives")
    st.markdown("#### Funding Disclosure")
    display_hint("funding")
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Claimant")
        rep_info_c = resp_p2.get('claimant', {}).get('reps_info', '')
        st.text_input("Lead Counsel (Claimant)", key="de_claimant_rep1")
        st.text_input("Co-Counsel (Claimant)", key="de_claimant_rep2")
        st.text_area("Client Address (Claimant)", key="de_claimant_addr")
        if rep_info_c and rep_info_c != "Pending" and not st.session_state.de_claimant_contact:
             st.session_state.de_claimant_contact = rep_info_c
        st.text_area("Counsel Contact (Claimant)", key="de_claimant_contact", height=150)
        
    with c2:
        st.markdown("### Respondent")
        rep_info_r = resp_p2.get('respondent', {}).get('reps_info', '')
        st.text_input("Lead Counsel (Respondent)", key="de_resp_rep1")
        st.text_input("Co-Counsel (Respondent)", key="de_resp_rep2")
        st.text_area("Client Address (Respondent)", key="de_resp_addr")
        if rep_info_r and rep_info_r != "Pending" and not st.session_state.de_resp_contact:
             st.session_state.de_resp_contact = rep_info_r
        st.text_area("Counsel Contact (Respondent)", key="de_resp_contact", height=150)

# --- TAB 5: TRIBUNAL ---
with tabs[4]:
    st.subheader("Tribunal Members")
    st.text_input("Co-Arbitrator 1", key="de_arb1")
    st.text_input("Co-Arbitrator 2", key="de_arb2")
    st.text_input("Presiding Arbitrator", key="de_arb3")
    
    st.divider()
    st.markdown("#### Tribunal Secretary")
    display_hint("secretary")
    display_hint("sec_fees")
    c1, c2 = st.columns(2)
    st.text_input("Secretary Name", key="de_sec_name")
    st.text_input("Secretary Hourly Rate", key="de_sec_rate")

# --- TAB 6: TIMETABLE ---
with tabs[5]:
    st.subheader("Procedural Timetable")
    st.markdown("#### Style Preference")
    display_hint("style")
    proc_style = st.radio("Select Style", ["Memorial", "Pleading"], horizontal=True, key="de_style")
    
    c1, c2 = st.columns(2)
    with c1:
        st.date_input("1. Statement of Case", key="de_d1")
        st.date_input("2. Statement of Defence", key="de_d2")
        st.date_input("3. Doc Production Requests", key="de_d3")
        st.date_input("8. Document Production", key="de_d8")
    with c2:
        if proc_style == "Memorial":
            st.date_input("9. Statement of Reply", key="de_d9")
            st.date_input("10. Statement of Rejoinder", key="de_d10")
            st.date_input("12. Oral Hearing", key="de_d12")
        else:
            st.date_input("9. Witness Statements", key="de_d9")
            st.date_input("10. Expert Reports", key="de_d10")
            st.date_input("14. Oral Hearing", key="de_d14")

# --- TAB 7: EVIDENCE ---
with tabs[6]:
    st.subheader("Evidence Protocols")
    st.markdown("#### Document Production")
    display_hint("doc_prod")
    display_hint("limits")
    display_hint("privilege_std")
    display_hint("privilege_logs")
    st.text_input("Time to Produce Docs", key="de_time_docs")
    
    st.divider()
    st.markdown("#### Witnesses & Experts")
    display_hint("witness_exam")
    display_hint("expert_meeting")
    display_hint("expert_hot_tub")
    display_hint("expert_reply")
    st.text_input("Notice for Oral Evidence", key="de_time_oral")

# --- TAB 8: HEARING ---
with tabs[7]:
    st.subheader("Hearing Logistics")
    display_hint("physical_venue_preference")
    display_hint("interpretation")
    display_hint("chess_clock")
    display_hint("transcription")
    display_hint("demonstratives")
    c1, c2 = st.columns(2)
    st.text_input("Physical Venue Name", key="de_venue_name")
    st.text_input("City", key="de_venue_city")
    st.text_input("Hearing Hours", key="de_hours")
    st.text_input("Time to Appoint Interpreter", key="de_time_interp")
    st.text_area("Hearing Agenda", key="de_agenda")
    st.text_area("Pre-Hearing Matters", key="de_prehear")

# --- TAB 9: LOGISTICS ---
with tabs[8]:
    st.subheader("Procedural Logistics")
    st.markdown("#### Submissions & Technology")
    display_hint("limits_submission")
    display_hint("ai_guidelines")
    display_hint("deadline_timezone")
    display_hint("time_shred_docs")
    display_hint("platform")
    display_hint("bundling")
    c1, c2 = st.columns(2)
    st.text_area("Page Limits Clause", key="de_limits")
    st.text_input("Max Filename Length", key="de_file_len")
    st.text_input("Deadline Timezone", key="de_timezone")
    st.text_input("Time to Shred Docs", key="de_time_shred")
    
    st.divider()
    st.markdown("#### Communications")
    display_hint("extensions")
    c1, c2 = st.columns(2)
    st.text_input("Time for Abbreviations", key="de_time_abbr")
    st.text_input("Time to Confirm Contact", key="de_time_contact")
    st.text_input("Time to Notify New Counsel", key="de_time_new_counsel")
    st.text_input("Bundle Deadline", key="de_time_bundle")
    st.text_input("Hearing Exhibits Deadline", key="de_time_exhibits")
    st.text_input("Venue Decision Deadline", key="de_date_venue")

# --- TAB 10: AWARD ---
with tabs[9]:
    st.subheader("Award Specifics")
    display_hint("sign_award")
    display_hint("currency")
    display_hint("interest")
    display_hint("last_submission")
    display_hint("post_hearing")
    display_hint("cost_allocation")
    display_hint("counsel_fees")
    display_hint("deposits")
    st.divider()
    st.markdown("#### Other Matters")
    display_hint("publication")
    display_hint("disability")
    display_hint("sustainability")
    display_hint("ethics")
    display_hint("mediation")

st.divider()

# --- GENERATION & SYNC ---
if st.button("Generate PO1 & Sync to Phase 4", type="primary"):
    template_path = "template_po1.docx"
    
    if not os.path.exists(template_path):
        st.error(f"System Error: Template file '{template_path}' not found. Please upload it to GitHub.")
    else:
        # 1. Sync dates
        count = sync_timeline_to_phase4(st.session_state.de_style)
        st.toast(f"System Update: Synced {count} events to Smart Timeline.")
        
        # 2. Build final context
        final_context = {
            'Case_Number': st.session_state.de_case_number,
            'seat_of_arbitration': st.session_state.de_seat,
            'meeting_date': st.session_state.de_meeting_date.strftime("%d %B %Y"), # Corrected
            'governing_law_of_contract': st.session_state.de_law,
            'claimant_rep_1': st.session_state.de_claimant_rep1,
            'claimant_rep_2': st.session_state.de_claimant_rep2,
            'Contact_details_of_Claimant': st.session_state.de_claimant_addr,
            'Contact_details_of_Claimant_Representative': st.session_state.de_claimant_contact,
            'respondent_rep_1': st.session_state.de_resp_rep1,
            'respondent_rep_2': st.session_state.de_resp_rep2,
            'Contact_details_of_Respondent': st.session_state.de_resp_addr,
            'Contact_details_of_Respondent_Representative': st.session_state.de_resp_contact,
            'Contact_details_of_Arbitrator_1': st.session_state.de_arb1,
            'Contact_details_of_Arbitrator_2': st.session_state.de_arb2,
            'Contact_details_of_Arbitrator_3_Presiding': st.session_state.de_arb3,
            'name_of_tribunal_secretary': st.session_state.de_sec_name,
            'secretary_hourly_rate': st.session_state.de_sec_rate,
            'limits_submission': st.session_state.de_limits,
            'max_filename_len': st.session_state.de_file_len,
            'deadline_timezone': st.session_state.de_timezone,
            'time_produce_docs': st.session_state.de_time_docs,
            'time_shred_docs': st.session_state.de_time_shred,
            'time_notify_oral': st.session_state.de_time_oral,
            'time_appoint_interpreter': st.session_state.de_time_interp,
            'time_hearing_bundle': st.session_state.de_time_bundle,
            'time_submit_exhibits': st.session_state.de_time_exhibits,
            'date_decide_venue': st.session_state.de_date_venue,
            'place_in_person': st.session_state.de_venue_name,
            'physical_venue_city': st.session_state.de_venue_city,
            'hearing_hours': st.session_state.de_hours,
            'schedule_oral_hearing': st.session_state.de_agenda,
            'prehearing_matters': st.session_state.de_prehear,
            'time_abbreviations': st.session_state.de_time_abbr,
            'time_confirm_contact': st.session_state.de_time_contact,
            'time_notify_counsel': st.session_state.de_time_new_counsel,
            # Dates
            'deadline_01': st.session_state.de_d1.strftime("%d %B %Y"),
            'deadline_02': st.session_state.de_d2.strftime("%d %B %Y"),
            'deadline_03': st.session_state.de_d3.strftime("%d %B %Y"),
            'deadline_08': st.session_state.de_d8.strftime("%d %B %Y"),
        }
        
        # Add conditional dates
        if st.session_state.de_style == "Memorial":
            final_context['deadline_09'] = st.session_state.de_d9.strftime("%d %B %Y")
            final_context['deadline_10'] = st.session_state.de_d10.strftime("%d %B %Y")
            final_context['deadline_12'] = st.session_state.de_d12.strftime("%d %B %Y")
        else:
            final_context['deadline_09'] = st.session_state.de_d9.strftime("%d %B %Y")
            final_context['deadline_10'] = st.session_state.de_d10.strftime("%d %B %Y")
            final_context['deadline_14'] = st.session_state.de_d14.strftime("%d %B %Y")

        try:
            doc = DocxTemplate(template_path)
            doc.render(final_context)
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            
            st.success("Document Generated Successfully.")
            st.download_button(
                label="Download Order (.docx)",
                data=buffer,
                file_name=f"PO1_{st.session_state.de_case_number}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        except Exception as e:
            st.error(f"Generation Failed: {e}")
