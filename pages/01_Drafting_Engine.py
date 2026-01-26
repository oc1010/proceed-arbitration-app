import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_complex_data, load_complex_data, send_email_notification
import pandas as pd
import os

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
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

# --- 1. INITIALIZE SESSION STATE (Anti-Jump & Anti-Duplicate Fix) ---
DEFAULTS = {
    'de_case_number': 'ARB/24/001',
    'de_seat': 'London',
    'de_law': 'English Law',
    'de_meeting_date': date.today(),
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
    # Timetable Dates (Prefix 'tt_' to avoid conflicts)
    'de_tt_d1': date.today(), 
    'de_tt_d2': date.today() + timedelta(weeks=4),
    'de_tt_d3': date.today() + timedelta(weeks=6), 
    'de_tt_d8': date.today() + timedelta(weeks=10),
    'de_tt_d9_mem': date.today() + timedelta(weeks=14), 
    'de_tt_d10_mem': date.today() + timedelta(weeks=18),
    'de_tt_d12_mem': date.today() + timedelta(weeks=22),
    'de_tt_d9_pl': date.today() + timedelta(weeks=14), 
    'de_tt_d10_pl': date.today() + timedelta(weeks=18),
    'de_tt_d14_pl': date.today() + timedelta(weeks=24)
}

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
            if extracted.endswith(":"): extracted = extracted[:-1]
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

def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

def sync_timeline_to_phase4(style):
    # Access dates from session state using 'tt' keys
    d1 = st.session_state.de_tt_d1
    d2 = st.session_state.de_tt_d2
    d3 = st.session_state.de_tt_d3
    d8 = st.session_state.de_tt_d8
    
    # Structure: id, event, original_date, current_date, status, owner, logistics, history
    new_events = [
        {"id": "ev_1", "event": "Statement of Case", "original_date": str(d1), "current_date": str(d1), "owner": "Claimant", "status": "Upcoming", "logistics": "Submit via Portal", "history": []},
        {"id": "ev_2", "event": "Statement of Defence", "original_date": str(d2), "current_date": str(d2), "owner": "Respondent", "status": "Upcoming", "logistics": "Submit via Portal", "history": []},
        {"id": "ev_3", "event": "Doc Production Requests", "original_date": str(d3), "current_date": str(d3), "owner": "Both", "status": "Upcoming", "logistics": "Use 'Doc Production' Tab", "history": []},
        {"id": "ev_4", "event": "Document Production", "original_date": str(d8), "current_date": str(d8), "owner": "Both", "status": "Upcoming", "logistics": "Exchange via Secure Link (No Upload)", "history": []},
    ]
    
    if style == "Memorial":
        d9, d10, d12 = st.session_state.de_tt_d9_mem, st.session_state.de_tt_d10_mem, st.session_state.de_tt_d12_mem
        new_events.extend([
            {"id": "ev_5", "event": "Statement of Reply", "original_date": str(d9), "current_date": str(d9), "owner": "Claimant", "status": "Upcoming", "logistics": "Submit via Portal", "history": []},
            {"id": "ev_6", "event": "Statement of Rejoinder", "original_date": str(d10), "current_date": str(d10), "owner": "Respondent", "status": "Upcoming", "logistics": "Submit via Portal", "history": []},
            {"id": "ev_7", "event": "Oral Hearing", "original_date": str(d12), "current_date": str(d12), "owner": "Tribunal", "status": "Upcoming", "logistics": "See Logistics Tab", "history": []}
        ])
    else:
        d9, d10, d14 = st.session_state.de_tt_d9_pl, st.session_state.de_tt_d10_pl, st.session_state.de_tt_d14_pl
        new_events.extend([
            {"id": "ev_5", "event": "Witness Statements", "original_date": str(d9), "current_date": str(d9), "owner": "Both", "status": "Upcoming", "logistics": "Exchange via Email", "history": []},
            {"id": "ev_6", "event": "Expert Reports", "original_date": str(d10), "current_date": str(d10), "owner": "Both", "status": "Upcoming", "logistics": "Exchange via Email", "history": []},
            {"id": "ev_7", "event": "Oral Hearing", "original_date": str(d14), "current_date": str(d14), "owner": "Tribunal", "status": "Upcoming", "logistics": "See Logistics Tab", "history": []}
        ])
    
    save_complex_data("timeline", new_events)
    
    # Notify
    emails = get_party_emails()
    send_email_notification(emails, "Procedural Order No. 1 Issued", "The Tribunal has established the Procedural Timetable. Log in to viewing the schedule.")
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
    # FORM WRAPPER TO PREVENT JUMPING
    with st.form("gen_form"):
        c1, c2 = st.columns(2)
        st.text_input("Case Reference Number", key="de_case_number")
        st.text_input("Seat of Arbitration", key="de_seat")
        st.date_input("First Procedural Meeting Date", key="de_meeting_date")
        st.text_input("Governing Law", key="de_law")
        st.selectbox("Arbitral Institution", ["LCIA", "ICC", "SIAC", "HKIAC", "ICDR"], key="de_inst")
        st.divider()
        st.markdown("#### Procedural Structure")
        display_hint("bifurcation")
        display_hint("consolidation")
        st.selectbox("Bifurcation Status", ["not bifurcated", "bifurcated"], key="de_bifurc_status")
        
        if st.form_submit_button("💾 Save General Details"):
            st.success("Saved.")

# --- TAB 4: PARTIES ---
with tabs[3]:
    st.subheader("Parties & Representatives")
    st.markdown("#### Funding Disclosure")
    display_hint("funding")
    st.divider()
    
    with st.form("parties_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### Claimant")
            st.text_input("Lead Counsel (Claimant)", key="de_claimant_rep1")
            st.text_input("Co-Counsel (Claimant)", key="de_claimant_rep2")
            st.text_area("Client Address (Claimant)", key="de_claimant_addr")
            st.text_area("Counsel Contact (Claimant)", key="de_claimant_contact", height=150)
        with c2:
            st.markdown("### Respondent")
            st.text_input("Lead Counsel (Respondent)", key="de_resp_rep1")
            st.text_input("Co-Counsel (Respondent)", key="de_resp_rep2")
            st.text_area("Client Address (Respondent)", key="de_resp_addr")
            st.text_area("Counsel Contact (Respondent)", key="de_resp_contact", height=150)
        
        if st.form_submit_button("💾 Save Parties"):
            st.success("Saved.")

# --- TAB 5: TRIBUNAL ---
with tabs[4]:
    st.subheader("Tribunal Members")
    with st.form("trib_form"):
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
        
        if st.form_submit_button("💾 Save Tribunal"):
            st.success("Saved.")

# --- TAB 6: TIMETABLE ---
with tabs[5]:
    st.subheader("Procedural Timetable")
    st.markdown("#### Style Preference")
    display_hint("style")
    # Radio needs to be outside form if it triggers conditional logic rendering
    proc_style = st.radio("Select Style", ["Memorial", "Pleading"], horizontal=True, key="de_style")
    
    with st.form("time_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.date_input("1. Statement of Case", key="de_tt_d1")
            st.date_input("2. Statement of Defence", key="de_tt_d2")
            st.date_input("3. Doc Production Requests", key="de_tt_d3")
            st.date_input("8. Document Production", key="de_tt_d8")
        with c2:
            if proc_style == "Memorial":
                st.date_input("9. Statement of Reply", key="de_tt_d9_mem")
                st.date_input("10. Statement of Rejoinder", key="de_tt_d10_mem")
                st.date_input("12. Oral Hearing", key="de_tt_d12_mem")
            else:
                st.date_input("9. Witness Statements", key="de_tt_d9_pl")
                st.date_input("10. Expert Reports", key="de_tt_d10_pl")
                st.date_input("14. Oral Hearing", key="de_tt_d14_pl")
        
        if st.form_submit_button("💾 Save Timetable"):
            st.success("Saved.")

# --- TAB 7: EVIDENCE ---
with tabs[6]:
    st.subheader("Evidence Protocols")
    st.markdown("#### Document Production")
    display_hint("doc_prod")
    display_hint("limits")
    display_hint("privilege_std")
    display_hint("privilege_logs")
    
    with st.form("ev_form"):
        st.text_input("Time to Produce Docs", key="de_time_docs")
        st.divider()
        st.markdown("#### Witnesses & Experts")
        display_hint("witness_exam")
        display_hint("expert_meeting")
        display_hint("expert_hot_tub")
        display_hint("expert_reply")
        st.text_input("Notice for Oral Evidence", key="de_time_oral")
        if st.form_submit_button("💾 Save Evidence"):
            st.success("Saved.")

# --- TAB 8: HEARING ---
with tabs[7]:
    st.subheader("Hearing Logistics")
    display_hint("physical_venue_preference")
    display_hint("interpretation")
    display_hint("chess_clock")
    display_hint("transcription")
    display_hint("demonstratives")
    
    with st.form("hear_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Physical Venue Name", key="de_venue_name")
            st.text_input("City", key="de_venue_city")
            st.text_input("Hearing Hours", key="de_hours")
        with c2:
            st.text_input("Time to Appoint Interpreter", key="de_time_interp")
        st.text_area("Hearing Agenda", key="de_agenda")
        st.text_area("Pre-Hearing Matters", key="de_prehear")
        if st.form_submit_button("💾 Save Hearing"):
            st.success("Saved.")

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
    
    with st.form("log_form"):
        c1, c2 = st.columns(2)
        with c1:
            st.text_area("Page Limits Clause", key="de_limits")
            st.text_input("Max Filename Length", key="de_file_len")
            st.text_input("Deadline Timezone", key="de_timezone")
            st.text_input("Time to Shred Docs", key="de_time_shred")
        with c2:
            st.text_input("Time for Abbreviations", key="de_time_abbr")
            st.text_input("Time to Confirm Contact", key="de_time_contact")
            st.text_input("Time to Notify New Counsel", key="de_time_new_counsel")
            st.text_input("Bundle Deadline", key="de_time_bundle")
            st.text_input("Hearing Exhibits Deadline", key="de_time_exhibits")
            st.text_input("Venue Decision Deadline", key="de_date_venue")
        
        if st.form_submit_button("💾 Save Logistics"):
            st.success("Saved.")

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
        count = sync_timeline_to_phase4(st.session_state.de_style)
        st.success(f"PO1 Generated. {count} events synced.")
        
        # Build Context for Doc Generation (Mapping 'tt' keys back to doc vars)
        style = st.session_state.de_style
        d9 = st.session_state.de_tt_d9_mem if style == "Memorial" else st.session_state.de_tt_d9_pl
        d10 = st.session_state.de_tt_d10_mem if style == "Memorial" else st.session_state.de_tt_d10_pl
        d_final = st.session_state.de_tt_d12_mem if style == "Memorial" else st.session_state.de_tt_d14_pl

        ctx = {
            'Case_Number': st.session_state.de_case_number,
            'seat_of_arbitration': st.session_state.de_seat,
            'meeting_date': st.session_state.de_meeting_date.strftime("%d %B %Y"),
            'deadline_01': st.session_state.de_tt_d1.strftime("%d %B %Y"),
            'deadline_02': st.session_state.de_tt_d2.strftime("%d %B %Y"),
            'deadline_03': st.session_state.de_tt_d3.strftime("%d %B %Y"),
            'deadline_08': st.session_state.de_tt_d8.strftime("%d %B %Y"),
            'deadline_09': d9.strftime("%d %B %Y"),
            'deadline_10': d10.strftime("%d %B %Y"),
            'deadline_12': d_final.strftime("%d %B %Y") if style == "Memorial" else "N/A",
            'deadline_14': d_final.strftime("%d %B %Y") if style == "Pleading" else "N/A"
        }
        
        try:
            doc = DocxTemplate(template_path)
            doc.render(ctx)
            buffer = BytesIO()
            doc.save(buffer)
            buffer.seek(0)
            st.download_button("Download Order (.docx)", data=buffer, file_name="PO1.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
        except Exception as e:
            st.error(f"Generation Failed: {e}")
