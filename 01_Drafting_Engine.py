import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline
import os

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home Dashboard", icon="🏠")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire", icon="✏️")
    st.page_link("pages/01_Drafting_Engine.py", label="Drafting Engine", icon="📝")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline", icon="📅")

st.title("PROCEED | Drafting Engine")

responses = load_responses()

def display_hint(key):
    c = responses.get('claimant', {}).get(key, "Pending")
    r = responses.get('respondent', {}).get(key, "Pending")
    if c == "Pending" and r == "Pending": st.info("Waiting for parties...", icon="⏳")
    elif c == r: st.success(f"**Agreed:** {c}", icon="✅")
    else: st.warning(f"**Conflict:**\nClaimant: {c}\nRespondent: {r}", icon="⚠️")

def save_schedule(dates, style):
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

tab1, tab2, tab3, tab4, tab5 = st.tabs(["General", "Parties", "Tribunal", "Timetable", "Logistics"])
context = {}

with tab1:
    c1, c2 = st.columns(2)
    context['Case_Number'] = c1.text_input("Case Ref", "ARB/24/001")
    context['seat_of_arbitration'] = c1.text_input("Seat", "London")
    context['meeting_date'] = c1.date_input("Meeting Date", date.today()).strftime("%d %B %Y")
    context['governing_law_of_contract'] = c1.text_input("Law", "English Law")
    with c2:
        context['arbitral_institution'] = st.selectbox("Institution", ["LCIA"])
        context['Parties'] = "the Parties"
        st.markdown("**Bifurcation**")
        display_hint("bifurcation")
        context['proceedings_bifurcation'] = st.selectbox("Status", ["not bifurcated", "bifurcated"])

with tab2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Claimant")
        context['claimant_rep_1'] = st.text_input("C Counsel 1", "Mr. Harvey Specter")
        context['claimant_rep_2'] = st.text_input("C Counsel 2", "Ms. Donna Paulsen")
        context['Contact_details_of_Claimant'] = st.text_area("C Address", "Address...")
        context['Contact_details_of_Claimant_Representative'] = st.text_area("C Rep Contact", "Email...")
    with c2:
        st.markdown("#### Respondent")
        context['respondent_rep_1'] = st.text_input("R Counsel 1", "Mr. Louis Litt")
        context['respondent_rep_2'] = st.text_input("R Counsel 2", "Ms. Katrina Bennett")
        context['Contact_details_of_Respondent'] = st.text_area("R Address", "Address...")
        context['Contact_details_of_Respondent_Representative'] = st.text_area("R Rep Contact", "Email...")

with tab3:
    context['Contact_details_of_Arbitrator_1'] = st.text_input("Arb 1", "Ms. Arbitrator One")
    context['Contact_details_of_Arbitrator_2'] = st.text_input("Arb 2", "Mr. Arbitrator Two")
    context['Contact_details_of_Arbitrator_3_Presiding'] = st.text_input("Presiding", "Prof. Presiding Three")
    st.divider()
    st.markdown("**Secretary**")
    display_hint("secretary")
    c1, c2 = st.columns(2)
    context['name_of_tribunal_secretary'] = c1.text_input("Name", "Mr. John Smith")
    context['secretary_hourly_rate'] = c2.text_input("Rate", "£200")

with tab4:
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

with tab5:
    st.markdown("**Rules**")
    display_hint("doc_prod")
    context['limits_submission'] = st.text_area("Limits", "Max 50 pages")
    context['max_filename_len'] = st.text_input("File Len", "50 chars")
    context['time_abbreviations'] = st.text_input("Abbrev Time", "7 days")
    context['time_confirm_contact'] = st.text_input("Contact Time", "7 days")
    context['time_notify_counsel'] = st.text_input("New Counsel Time", "immediately")
    context['deadline_timezone'] = st.text_input("Timezone", "17:00 London time")
    context['time_produce_docs'] = st.text_input("Prod Time", "14 days")
    context['time_shred_docs'] = st.text_input("Shred Time", "6 months")
    context['time_notify_oral'] = st.text_input("Oral Notice", "45 days")
    context['time_appoint_interpreter'] = st.text_input("Interp Time", "14 days")
    context['time_hearing_bundle'] = st.text_input("Bundle Time", "14 days before")
    context['time_submit_exhibits'] = st.text_input("Exhibits Time", "24 hours")
    context['date_decide_venue'] = st.text_input("Venue Time", "3 months prior")
    context['place_in_person'] = st.text_input("Venue", "IDRC London")
    context['hearing_hours'] = st.text_input("Hours", "09:30 - 17:30")
    context['physical_venue_city'] = st.text_input("City", "London")
    context['schedule_oral_hearing'] = st.text_area("Agenda", "Opening, Witnesses, Experts, Closing")
    context['prehearing_matters'] = st.text_area("Pre-Hearing", "Daily schedule, chess clock.")

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
