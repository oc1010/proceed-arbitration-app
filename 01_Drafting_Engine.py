import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline
import os

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied. Please log in via the Dashboard.")
    st.stop()

st.title("PROCEED | Drafting Engine")

# --- 1. SMART LOGIC (Reads Questionnaire) ---
responses = load_responses()

def display_hint(key):
    """
    Checks what Claimant and Respondent selected in the Questionnaire
    and displays a helpful hint to the Arbitrator.
    """
    c_val = responses.get('claimant', {}).get(key, "Pending")
    r_val = responses.get('respondent', {}).get(key, "Pending")
    
    if c_val == "Pending" and r_val == "Pending":
        st.info("Waiting for parties to submit questionnaire...", icon="⏳")
    elif c_val == r_val:
        st.success(f"**Parties Agree:** {c_val}", icon="✅")
    else:
        st.warning(f"**Conflict:**\n\n**Claimant:** {c_val}\n\n**Respondent:** {r_val}", icon="⚠️")

# --- 2. DATABASE CONNECTOR (Cloud) ---
def save_schedule_to_cloud(dates, style):
    events = []
    events.append({"date": str(dates['deadline_01']), "event": "Statement of Case", "owner": "Claimant", "status": "Pending"})
    events.append({"date": str(dates['deadline_02']), "event": "Statement of Defence", "owner": "Respondent", "status": "Pending"})
    events.append({"date": str(dates['deadline_03']), "event": "Doc Production Requests", "owner": "All", "status": "Pending"})
    events.append({"date": str(dates['deadline_08']), "event": "Document Production", "owner": "All", "status": "Pending"})
    
    if style == "Memorial":
        events.append({"date": str(dates['deadline_09']), "event": "Statement of Reply", "owner": "Claimant", "status": "Pending"})
        events.append({"date": str(dates['deadline_10']), "event": "Statement of Rejoinder", "owner": "Respondent", "status": "Pending"})
        events.append({"date": str(dates['deadline_12']), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending"})
    else:
        events.append({"date": str(dates['deadline_09']), "event": "Witness Statements", "owner": "All", "status": "Pending"})
        events.append({"date": str(dates['deadline_10']), "event": "Expert Reports", "owner": "All", "status": "Pending"})
        events.append({"date": str(dates['deadline_14']), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending"})

    # SAVE TO CLOUD (JsonBin) instead of local file
    save_timeline(events)
    return len(events)

# --- 3. INPUT FORM ---
tab_gen, tab_parties, tab_tribunal, tab_schedule, tab_logistics = st.tabs([
    "General & Law", "Parties", "Tribunal", "Timetable", "Logistics"
])

context = {}

with tab_gen:
    st.subheader("General Case Details")
    c1, c2 = st.columns(2)
    with c1:
        context['Case_Number'] = st.text_input("Case Number", "ARB/24/001")
        context['meeting_date'] = st.date_input("Preliminary Meeting Date", date.today()).strftime("%d %B %Y")
        context['seat_of_arbitration'] = st.text_input("Seat of Arbitration", "London, United Kingdom")
        context['governing_law_of_contract'] = st.text_input("Governing Law", "the laws of England and Wales")
    with c2:
        context['arbitral_institution'] = st.selectbox("Arbitral Institution", ["LCIA"], help("Locked to LCIA for this template version."))
        context['Parties'] = "the Parties"
        
        st.divider()
        st.markdown("#### Bifurcation")
        # SMART HINT: Shows what parties want regarding bifurcation
        display_hint("bifurcation") 
        context['proceedings_bifurcation'] = st.selectbox("Tribunal Decision", ["not bifurcated", "bifurcated"])

with tab_parties:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Claimant")
        context['claimant_rep_1'] = st.text_input("Lead Counsel (Claimant)", "Mr. Harvey Specter")
        context['claimant_rep_2'] = st.text_input("Co-Counsel (Claimant)", "Ms. Donna Paulsen")
        context['Contact_details_of_Claimant'] = st.text_area("Client Address (Claimant)", "Specter Litt, 123 Law St...")
        context['Contact_details_of_Claimant_Representative'] = st.text_area("Counsel Contact (Claimant)", "Email: harvey@specter.com...")
    with c2:
        st.markdown("#### Respondent")
        context['respondent_rep_1'] = st.text_input("Lead Counsel (Respondent)", "Mr. Louis Litt")
        context['respondent_rep_2'] = st.text_input("Co-Counsel (Respondent)", "Ms. Katrina Bennett")
        context['Contact_details_of_Respondent'] = st.text_area("Client Address (Respondent)", "Litt & Co, 456 Legal Ave...")
        context['Contact_details_of_Respondent_Representative'] = st.text_area("Counsel Contact (Respondent)", "Email: louis@litt.com...")
        
    st.divider()
    st.markdown("#### Third-Party Funding")
    display_hint("funding")

with tab_tribunal:
    st.subheader("Tribunal Composition")
    context['Contact_details_of_Arbitrator_1'] = st.text_input("Co-Arbitrator 1", "Ms. Arbitrator One")
    context['Contact_details_of_Arbitrator_2'] = st.text_input("Co-Arbitrator 2", "Mr. Arbitrator Two")
    context['Contact_details_of_Arbitrator_3_Presiding'] = st.text_input("Presiding Arbitrator", "Prof. Presiding Three")
    
    st.divider()
    st.subheader("Administrative Secretary")
    # SMART HINT: Shows if parties consented to secretary & fees
    display_hint("secretary")
    display_hint("sec_fees")
    
    c1, c2 = st.columns(2)
    context['name_of_tribunal_secretary'] = c1.text_input("Secretary Name", "Mr. John Smith")
    context['secretary_hourly_rate'] = c2.text_input("Hourly Rate", "£200")

with tab_schedule:
    st.subheader("Procedural Calendar")
    
    st.markdown("#### Procedure Style")
    # SMART HINT: Memorial vs Pleading
    display_hint("style")
    
    proc_style = st.radio("Select Style", ["Memorial", "Pleading"], horizontal=True)
    context['procedure_style'] = proc_style
    
    dates = {}
    c1, c2 = st.columns(2)
    with c1:
        dates['deadline_01'] = st.date_input("1. Statement of Case", date.today() + timedelta(weeks=4))
        dates['deadline_02'] = st.date_input("2. Statement of Defence", date.today() + timedelta(weeks=8))
        dates['deadline_03'] = st.date_input("3. Doc Requests", date.today() + timedelta(weeks=10))
        dates['deadline_08'] = st.date_input("8. Production", date.today() + timedelta(weeks=18))
    with c2:
        if proc_style == "Memorial":
            dates['deadline_09'] = st.date_input("9. Reply", date.today() + timedelta(weeks=22))
            dates['deadline_10'] = st.date_input("10. Rejoinder", date.today() + timedelta(weeks=26))
            dates['deadline_12'] = st.date_input("12. Hearing", date.today() + timedelta(weeks=34))
        else:
            dates['deadline_09'] = st.date_input("9. Witness Stmts", date.today() + timedelta(weeks=22))
            dates['deadline_10'] = st.date_input("10. Expert Rpts", date.today() + timedelta(weeks=26))
            dates['deadline_14'] = st.date_input("14. Hearing", date.today() + timedelta(weeks=36))
    
    for i in range(1, 15):
        k = f"deadline_{i:02d}"
        if k not in dates: dates[k] = date.today()
    for k, v in dates.items():
        context[k] = v.strftime("%d %B %Y")

with tab_logistics:
    st.subheader("Procedural Logistics")
    
    st.markdown("#### Document Production Rules")
    display_hint("doc_prod")
    display_hint("limits")
    
    st.markdown("#### Extensions Protocol")
    display_hint("extensions")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        context['limits_submission'] = st.text_area("Submission Limits", "Max 50 pages.")
        context['max_filename_len'] = st.text_input("Max Filename Length", "50 chars")
        context['time_abbreviations'] = st.text_input("Time for Abbreviations", "7 days")
        context['time_confirm_contact'] = st.text_input("Time to Confirm Contact", "7 days")
        context['time_notify_counsel'] = st.text_input("Time to Notify New Counsel", "immediately")
        context['deadline_timezone'] = st.text_input("Deadline Timezone", "17:00 London time")
    with c2:
        context['time_produce_docs'] = st.text_input("Time to Produce Docs", "14 days")
        context['time_shred_docs'] = st.text_input("Time to Shred Docs", "6 months")
        context['time_notify_oral'] = st.text_input("Notice for Oral Evidence", "45 days")
        context['time_appoint_interpreter'] = st.text_input("Time to Appoint Interpreter", "14 days")
        context['time_hearing_bundle'] = st.text_input("Bundle Deadline", "14 days before Hearing")
        context['time_submit_exhibits'] = st.text_input("Hearing Exhibits Deadline", "24 hours")
        context['date_decide_venue'] = st.text_input("Venue Decision Deadline", "3 months prior")
        context['place_in_person'] = st.text_input("Physical Venue", "IDRC London")
        context['hearing_hours'] = st.text_input("Hearing Hours", "09:30 - 17:30")
        context['physical_venue_city'] = st.text_input("City", "London")
        context['schedule_oral_hearing'] = st.text_area("Hearing Agenda", "Opening, Witnesses, Experts, Closing")
        context['prehearing_matters'] = st.text_area("Pre-Hearing Matters", "Daily schedule, chess clock.")

st.divider()

if st.button("Generate Procedural Order No. 1", type="primary", use_container_width=True):
    # Ensure this file name matches what you uploaded
    template_path = "template_po1.docx" 
    
    if not os.path.exists(template_path):
        st.error(f"System Error: Template file '{template_path}' not found.")
    else:
        # Sync to Cloud
        count = save_schedule_to_cloud(dates, proc_style)
        st.toast(f"System Update: Synced {count} events to Smart Timeline.")
        
        # Generate Doc
        doc = DocxTemplate(template_path)
        doc.render(context)
        
        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        
        st.success("Document Generated Successfully.")
        st.download_button(
            label="Download Order (.docx)",
            data=buffer,
            file_name=f"PO1_{context['Case_Number']}.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )