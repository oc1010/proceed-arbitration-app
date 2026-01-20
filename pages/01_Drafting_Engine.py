import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline
import os
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
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("Procedural Order No. 1 | Drafting Engine")

# --- SMART LOGIC ---
responses = load_responses()

def display_hint(key):
    c = responses.get('claimant', {}).get(key, "Pending")
    r = responses.get('respondent', {}).get(key, "Pending")
    if c == "Pending" and r == "Pending": st.info("Waiting for parties...", icon="⏳")
    elif c == r: st.success(f"Agreed: {c}")
    else: st.warning(f"Conflict: Claimant '{c}' vs Respondent '{r}'")

# --- SAVE LOGIC ---
def save_schedule(dates, style):
    # (Same timeline logic as before)
    events = [
        {"date": str(dates['d1']), "event": "Statement of Case", "owner": "Claimant", "status": "Pending"},
        {"date": str(dates['d2']), "event": "Statement of Defence", "owner": "Respondent", "status": "Pending"},
        {"date": str(dates['d3']), "event": "Doc Requests", "owner": "All", "status": "Pending"},
        {"date": str(dates['d8']), "event": "Production", "owner": "All", "status": "Pending"}
    ]
    if style == "Memorial":
         events.extend([
             {"date": str(dates['d9']), "event": "Reply", "owner": "Claimant", "status": "Pending"},
             {"date": str(dates['d10']), "event": "Rejoinder", "owner": "Respondent", "status": "Pending"},
             {"date": str(dates['d12']), "event": "Hearing", "owner": "Tribunal", "status": "Pending"}
         ])
    else:
         events.extend([
             {"date": str(dates['d9']), "event": "Witness Stmts", "owner": "All", "status": "Pending"},
             {"date": str(dates['d10']), "event": "Expert Reports", "owner": "All", "status": "Pending"},
             {"date": str(dates['d14']), "event": "Hearing", "owner": "Tribunal", "status": "Pending"}
         ])
    save_timeline(events)
    return len(events)

# --- UI TABS ---
tabs = st.tabs(["Party Preferences", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])
context = {}

# 1. PREFERENCES TAB
with tabs[0]:
    st.subheader("Summary of Questionnaire Responses")
    c_data = responses.get('claimant', {})
    r_data = responses.get('respondent', {})
    all_keys = list(set(list(c_data.keys()) + list(r_data.keys())))
    if not all_keys:
        st.info("No data submitted yet.")
    else:
        summary_data = []
        for k in all_keys:
            c_val = c_data.get(k, "Pending")
            r_val = r_data.get(k, "Pending")
            match = "Yes" if c_val == r_val and c_val != "Pending" else "No"
            summary_data.append({"Topic ID": k, "Claimant": c_val, "Respondent": r_val, "Agreement": match})
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)

# 2. GENERAL TAB
with tabs[1]:
    c1, c2 = st.columns(2)
    context['Case_Number'] = c1.text_input("Case Ref", "ARB/24/001")
    context['seat_of_arbitration'] = c1.text_input("Seat", "London")
    context['meeting_date'] = c1.date_input("Meeting Date", date.today()).strftime("%d %B %Y")
    context['governing_law_of_contract'] = c2.text_input("Law", "English Law")
    context['arbitral_institution'] = c2.selectbox("Institution", ["LCIA"])
    context['Parties'] = "the Parties"
    
    st.divider()
    st.markdown("**Bifurcation & Consolidation**")
    display_hint("bifurcation")
    display_hint("consolidation")
    context['proceedings_bifurcation'] = st.selectbox("Bifurcation Status", ["not bifurcated", "bifurcated"])

# 3. PARTIES TAB
with tabs[2]:
    st.markdown("**Funding Disclosure**")
    display_hint("funding")
    c1, c2 = st.columns(2)
    with c1:
        st.caption("Claimant")
        context['claimant_rep_1'] = st.text_input("C Counsel 1", "Mr. Harvey Specter")
        context['claimant_rep_2'] = st.text_input("C Counsel 2", "Ms. Donna Paulsen")
        context['Contact_details_of_Claimant'] = st.text_area("C Client Address", "Address...")
        context['Contact_details_of_Claimant_Representative'] = st.text_area("C Counsel Contact", "Email...")
    with c2:
        st.caption("Respondent")
        context['respondent_rep_1'] = st.text_input("R Counsel 1", "Mr. Louis Litt")
        context['respondent_rep_2'] = st.text_input("R Counsel 2", "Ms. Katrina Bennett")
        context['Contact_details_of_Respondent'] = st.text_area("R Client Address", "Address...")
        context['Contact_details_of_Respondent_Representative'] = st.text_area("R Counsel Contact", "Email...")

# 4. TRIBUNAL TAB
with tabs[3]:
    context['Contact_details_of_Arbitrator_1'] = st.text_input("Arb 1", "Ms. Arbitrator One")
    context['Contact_details_of_Arbitrator_2'] = st.text_input("Arb 2", "Mr. Arbitrator Two")
    context['Contact_details_of_Arbitrator_3_Presiding'] = st.text_input("Presiding", "Prof. Presiding Three")
    
    st.divider()
    st.markdown("**Tribunal Secretary**")
    display_hint("secretary")
    display_hint("sec_fees")
    c1, c2 = st.columns(2)
    context['name_of_tribunal_secretary'] = c1.text_input("Name", "Mr. John Smith")
    context['secretary_hourly_rate'] = c2.text_input("Rate", "£200")

# 5. TIMETABLE TAB
with tabs[4]:
    st.markdown("**Style Preference**")
    display_hint("style")
    proc_style = st.radio("Style", ["Memorial", "Pleading"], horizontal=True)
    context['procedure_style'] = proc_style
    
    d = {}
    c1, c2 = st.columns(2)
    d['d1'] = c1.date_input("1. Statement of Case", date.today()+timedelta(weeks=4))
    d['d2'] = c1.date_input("2. Statement of Defence", date.today()+timedelta(weeks=8))
    d['d3'] = c1.date_input("3. Requests", date.today()+timedelta(weeks=10))
    d['d8'] = c1.date_input("8. Production", date.today()+timedelta(weeks=18))
    
    if proc_style == "Memorial":
        d['d9'] = c2.date_input("9. Reply", date.today()+timedelta(weeks=22))
        d['d10'] = c2.date_input("10. Rejoinder", date.today()+timedelta(weeks=26))
        d['d12'] = c2.date_input("12. Hearing", date.today()+timedelta(weeks=34))
    else:
        d['d9'] = c2.date_input("9. Wit Stmts", date.today()+timedelta(weeks=22))
        d['d10'] = c2.date_input("10. Experts", date.today()+timedelta(weeks=26))
        d['d14'] = c2.date_input("14. Hearing", date.today()+timedelta(weeks=36))

    # Map for Template
    context['deadline_01'] = d['d1'].strftime("%d %B %Y")
    context['deadline_02'] = d['d2'].strftime("%d %B %Y")
    context['deadline_03'] = d['d3'].strftime("%d %B %Y")
    context['deadline_08'] = d['d8'].strftime("%d %B %Y")
    if proc_style == "Memorial":
        context['deadline_09'] = d['d9'].strftime("%d %B %Y")
        context['deadline_10'] = d['d10'].strftime("%d %B %Y")
        context['deadline_12'] = d['d12'].strftime("%d %B %Y")
    else:
        context['deadline_09'] = d['d9'].strftime("%d %B %Y")
        context['deadline_10'] = d['d10'].strftime("%d %B %Y")
        context['deadline_14'] = d['d14'].strftime("%d %B %Y")
    
    for i in range(1,15):
        if f"deadline_{i:02d}" not in context: context[f"deadline_{i:02d}"] = ""

# 6. EVIDENCE TAB
with tabs[5]:
    st.markdown("**Document Production**")
    display_hint("doc_prod")
    display_hint("limits")
    display_hint("privilege_std")
    display_hint("privilege_logs")
    context['time_produce_docs'] = st.text_input("Prod Time", "14 days")
    
    st.divider()
    st.markdown("**Witnesses & Experts**")
    display_hint("witness_exam")
    display_hint("expert_meeting")
    display_hint("expert_hot_tub")
    display_hint("expert_reply")
    context['time_notify_oral'] = st.text_input("Oral Notice", "45 days")

# 7. HEARING TAB
with tabs[6]:
    st.markdown("**Hearing Logistics**")
    display_hint("venue_type")
    display_hint("interpretation")
    display_hint("chess_clock")
    display_hint("transcription")
    
    c1, c2 = st.columns(2)
    context['place_in_person'] = c1.text_input("Physical Venue", "IDRC London")
    context['physical_venue_city'] = c1.text_input("City", "London")
    context['hearing_hours'] = c2.text_input("Hours", "09:30 - 17:30")
    context['time_appoint_interpreter'] = c2.text_input("Interp Time", "14 days")
    context['schedule_oral_hearing'] = st.text_area("Agenda", "Opening, Witnesses, Experts, Closing")
    context['prehearing_matters'] = st.text_area("Pre-Hearing", "Daily schedule, chess clock.")

# 8. LOGISTICS TAB
with tabs[7]:
    st.markdown("**Submissions & Tech**")
    display_hint("page_limits")
    display_hint("ai_guidelines")
    display_hint("deadline_def")
    display_hint("shredding")
    
    c1, c2 = st.columns(2)
    context['limits_submission'] = c1.text_area("Page Limits", "Max 50 pages")
    context['max_filename_len'] = c2.text_input("Filename Len", "50 chars")
    context['deadline_timezone'] = c2.text_input("Timezone", "17:00 London time")
    context['time_shred_docs'] = c2.text_input("Shred Time", "6 months")
    
    st.markdown("**Communication**")
    display_hint("extensions")
    context['time_abbreviations'] = st.text_input("Abbrev Time", "7 days")
    context['time_confirm_contact'] = st.text_input("Contact Time", "7 days")
    context['time_notify_counsel'] = st.text_input("New Counsel Time", "immediately")
    context['time_hearing_bundle'] = st.text_input("Bundle Time", "14 days before")
    context['time_submit_exhibits'] = st.text_input("Exhibits Time", "24 hours")
    context['date_decide_venue'] = st.text_input("Venue Decision Time", "3 months prior")

# 9. AWARD TAB
with tabs[8]:
    st.markdown("**Award Specifics**")
    display_hint("sign_award")
    display_hint("currency")
    display_hint("interest")
    display_hint("last_submission")
    display_hint("post_hearing")

st.divider()

if st.button("Generate PO1 & Sync", type="primary"):
    template_path = "template_po1.docx"
    if not os.path.exists(template_path):
        st.error(f"Missing {template_path}")
    else:
        count = save_schedule(d, proc_style)
        doc = DocxTemplate(template_path)
        doc.render(context)
        buf = BytesIO()
        doc.save(buf)
        buf.seek(0)
        st.success(f"Synced {count} events. PO1 Generated!")
        st.download_button("Download PO1", buf, "PO1.docx")
