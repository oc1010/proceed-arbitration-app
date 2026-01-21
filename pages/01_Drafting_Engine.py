import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline, reset_database, load_structure
import pandas as pd
import os

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
    
    st.divider()
    st.caption("ADMIN CONTROLS")
    if st.button("⚠️ Factory Reset", help="Wipes Timeline & Responses.", type="secondary", use_container_width=True):
        reset_database()
        st.toast("System Reset!", icon="🗑️")
        st.rerun()

st.title("Procedural Order No. 1 | Drafting Engine")

# --- 1. INITIALIZE CONTEXT (Prevent KeyError) ---
context = {
    'Case_Number': 'ARB/24/001', 
    'seat_of_arbitration': 'London', 
    'meeting_date': date.today().strftime("%d %B %Y"), 
    'governing_law_of_contract': 'English Law',
    'claimant_rep_1': '', 'claimant_rep_2': '', 
    'Contact_details_of_Claimant': '', 'Contact_details_of_Claimant_Representative': '',
    'respondent_rep_1': '', 'respondent_rep_2': '', 
    'Contact_details_of_Respondent': '', 'Contact_details_of_Respondent_Representative': '',
    'Contact_details_of_Arbitrator_1': '', 'Contact_details_of_Arbitrator_2': '', 
    'Contact_details_of_Arbitrator_3_Presiding': '',
    'name_of_tribunal_secretary': '', 'secretary_hourly_rate': '',
    'limits_submission': '', 
    'max_filename_len': '50 chars', 
    'deadline_timezone': '17:00 London', 
    'time_produce_docs': '14 days', 
    'time_shred_docs': '6 months', 
    'time_notify_oral': '45 days',
    'time_appoint_interpreter': '14 days', 
    'time_hearing_bundle': '14 days before', 
    'time_submit_exhibits': '24 hours', 
    'date_decide_venue': '3 months prior',
    'place_in_person': 'IDRC London', 
    'physical_venue_city': 'London', 
    'hearing_hours': '09:30 - 17:30',
    'schedule_oral_hearing': '', 
    'prehearing_matters': '', 
    'time_abbreviations': '7 days',
    'time_confirm_contact': '7 days', 
    'time_notify_counsel': 'immediately'
}
for i in range(1, 16):
    context[f"deadline_{i:02d}"] = "TBD"

responses = load_responses()

def display_hint(key):
    """
    Shows a small colored box indicating if parties agree or conflict on a specific issue.
    """
    c = responses.get('claimant', {}).get(key, "Pending")
    r = responses.get('respondent', {}).get(key, "Pending")
    
    # Helper to clean the displayed hint text (remove bolding/long descriptions)
    def clean_hint(txt):
        if "**" in txt:
            parts = txt.split("**")
            if len(parts) >= 2: return parts[1].strip()
        return txt.split(".")[0] if txt else "Pending"

    c_clean = clean_hint(c)
    r_clean = clean_hint(r)

    if c == "Pending" and r == "Pending": 
        st.info("Waiting for parties...", icon="⏳")
    elif c == r: 
        st.success(f"Agreed: {c_clean}", icon="✅")
    else: 
        st.warning(f"Conflict: Claimant '{c_clean}' vs Respondent '{r_clean}'", icon="⚠️")

def save_schedule(dates, style):
    """
    Saves the procedural timetable to the cloud database for the Smart Timeline view.
    """
    events = [
        {"date": str(dates['d1']), "event": "Statement of Case", "owner": "Claimant", "status": "Pending"},
        {"date": str(dates['d2']), "event": "Statement of Defence", "owner": "Respondent", "status": "Pending"},
        {"date": str(dates['d3']), "event": "Doc Production Requests", "owner": "All", "status": "Pending"},
        {"date": str(dates['d8']), "event": "Document Production", "owner": "All", "status": "Pending"}
    ]
    
    if style == "Memorial":
         events.extend([
             {"date": str(dates['d9']), "event": "Statement of Reply", "owner": "Claimant", "status": "Pending"},
             {"date": str(dates['d10']), "event": "Statement of Rejoinder", "owner": "Respondent", "status": "Pending"},
             {"date": str(dates['d12']), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending"}
         ])
    else:
         events.extend([
             {"date": str(dates['d9']), "event": "Witness Statements", "owner": "All", "status": "Pending"},
             {"date": str(dates['d10']), "event": "Expert Reports", "owner": "All", "status": "Pending"},
             {"date": str(dates['d14']), "event": "Oral Hearing", "owner": "Tribunal", "status": "Pending"}
         ])
    
    save_timeline(events)
    return len(events)

# --- UI TABS ---
tabs = st.tabs(["Preferences", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])

# 1. PREFERENCES TAB (Summary Table)
with tabs[0]:
    st.subheader("Questionnaire Responses")
    st.caption("A comparison of the Claimant's and Respondent's answers.")
    
    try:
        c_data = responses.get('claimant', {})
        r_data = responses.get('respondent', {})
        
        # Load the question structure to map IDs to Real Question Text
        structure = load_structure()
        dynamic_map = {}
        if structure:
            for q in structure:
                dynamic_map[q['id']] = q['question']
        
        # Filter keys: only actual questions, not the comment keys
        all_keys = [k for k in list(set(list(c_data.keys()) + list(r_data.keys()))) if not k.endswith("_comment")]
        
        if not all_keys:
            st.info("No data submitted yet.")
        else:
            summary_data = []
            # Sort keys based on their numeric prefix
            def sort_key(k):
                text = dynamic_map.get(k, k)
                try:
                    return int(text.split(".")[0])
                except:
                    return 999
            
            for k in sorted(all_keys, key=sort_key):
                # Get Readable Question Title
                topic = dynamic_map.get(k, k)
                
                c_val = c_data.get(k, "Pending")
                r_val = r_data.get(k, "Pending")
                
                # Fetch Comments
                c_comm = c_data.get(f"{k}_comment", "")
                r_comm = r_data.get(f"{k}_comment", "")
                
                # CLEANER: Extract only the bold title "Option A: Style"
                def clean_val(v):
                    if "**" in v:
                        parts = v.split("**")
                        if len(parts) >= 2: return parts[1].strip()
                    return v.split(".")[0] if v and "." in v else v
                
                c_clean = clean_val(c_val)
                r_clean = clean_val(r_val)
                
                # Append comment hint icon if present
                if c_comm: c_clean += " 💬"
                if r_comm: r_clean += " 💬"
                
                match = "✅" if c_val == r_val and c_val != "Pending" else "❌"
                
                summary_data.append({
                    "Question": topic, 
                    "Claimant": c_clean, 
                    "Respondent": r_clean, 
                    "Match": match
                })
            
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
            
            # --- DETAILED COMMENTS VIEW ---
            st.markdown("### 💬 Party Comments")
            with st.expander("Click to view detailed comments from the parties"):
                found_comments = False
                for k in sorted(all_keys, key=sort_key):
                    c_comm = c_data.get(f"{k}_comment", "")
                    r_comm = r_data.get(f"{k}_comment", "")
                    
                    if c_comm or r_comm:
                        found_comments = True
                        st.markdown(f"**{dynamic_map.get(k, k)}**")
                        if c_comm: 
                            st.info(f"**Claimant:** {c_comm}", icon="🔵")
                        if r_comm: 
                            st.warning(f"**Respondent:** {r_comm}", icon="🟠")
                        st.divider()
                
                if not found_comments:
                    st.write("No additional comments provided by the parties.")
            
    except Exception as e:
        st.error(f"Error loading summary table: {e}")

# 2. GENERAL TAB
with tabs[1]:
    st.subheader("General Details")
    c1, c2 = st.columns(2)
    context['Case_Number'] = c1.text_input("Case Reference Number", context['Case_Number'])
    context['seat_of_arbitration'] = c1.text_input("Seat of Arbitration", context['seat_of_arbitration'])
    
    try:
        default_date = date.today()
    except:
        default_date = date.today()
        
    context['meeting_date'] = c1.date_input("First Procedural Meeting Date", default_date).strftime("%d %B %Y")
    context['governing_law_of_contract'] = c2.text_input("Governing Law", context['governing_law_of_contract'])
    context['arbitral_institution'] = c2.selectbox("Arbitral Institution", ["LCIA", "ICC", "SIAC", "HKIAC", "ICDR"])
    context['Parties'] = "the Parties"
    
    st.divider()
    st.markdown("#### Procedural Structure")
    display_hint("bifurcation")
    display_hint("consolidation")
    context['proceedings_bifurcation'] = st.selectbox("Bifurcation Status", ["not bifurcated", "bifurcated"])

# 3. PARTIES TAB
with tabs[2]:
    st.subheader("Parties & Representatives")
    
    st.markdown("#### Funding Disclosure")
    display_hint("funding")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Claimant")
        rep_info_c = responses.get('claimant', {}).get('reps_info', '')
        
        context['claimant_rep_1'] = st.text_input("Lead Counsel (Claimant)", context['claimant_rep_1'])
        context['claimant_rep_2'] = st.text_input("Co-Counsel (Claimant)", context['claimant_rep_2'])
        context['Contact_details_of_Claimant'] = st.text_area("Client Address (Claimant)", context['Contact_details_of_Claimant'])
        context['Contact_details_of_Claimant_Representative'] = st.text_area("Counsel Contact (Claimant)", value=rep_info_c if rep_info_c and rep_info_c!="Pending" else context['Contact_details_of_Claimant_Representative'], height=150)
        
    with c2:
        st.markdown("### Respondent")
        rep_info_r = responses.get('respondent', {}).get('reps_info', '')
        
        context['respondent_rep_1'] = st.text_input("Lead Counsel (Respondent)", context['respondent_rep_1'])
        context['respondent_rep_2'] = st.text_input("Co-Counsel (Respondent)", context['respondent_rep_2'])
        context['Contact_details_of_Respondent'] = st.text_area("Client Address (Respondent)", context['Contact_details_of_Respondent'])
        context['Contact_details_of_Respondent_Representative'] = st.text_area("Counsel Contact (Respondent)", value=rep_info_r if rep_info_r and rep_info_r!="Pending" else context['Contact_details_of_Respondent_Representative'], height=150)

# 4. TRIBUNAL TAB
with tabs[3]:
    st.subheader("Tribunal Members")
    context['Contact_details_of_Arbitrator_1'] = st.text_input("Co-Arbitrator 1", context['Contact_details_of_Arbitrator_1'])
    context['Contact_details_of_Arbitrator_2'] = st.text_input("Co-Arbitrator 2", context['Contact_details_of_Arbitrator_2'])
    context['Contact_details_of_Arbitrator_3_Presiding'] = st.text_input("Presiding Arbitrator", context['Contact_details_of_Arbitrator_3_Presiding'])
    
    st.divider()
    st.markdown("#### Tribunal Secretary")
    display_hint("secretary")
    display_hint("sec_fees")
    
    c1, c2 = st.columns(2)
    context['name_of_tribunal_secretary'] = c1.text_input("Secretary Name", context['name_of_tribunal_secretary'])
    context['secretary_hourly_rate'] = c2.text_input("Secretary Hourly Rate", context['secretary_hourly_rate'])

# 5. TIMETABLE TAB
with tabs[4]:
    st.subheader("Procedural Timetable")
    
    st.markdown("#### Style Preference")
    display_hint("style")
    
    proc_style = st.radio("Select Style", ["Memorial", "Pleading"], horizontal=True)
    context['procedure_style'] = proc_style
    
    d = {}
    c1, c2 = st.columns(2)
    with c1:
        d['d1'] = st.date_input("1. Statement of Case", date.today() + timedelta(weeks=4))
        d['d2'] = st.date_input("2. Statement of Defence", date.today() + timedelta(weeks=8))
        d['d3'] = st.date_input("3. Doc Production Requests", date.today() + timedelta(weeks=10))
        d['d8'] = st.date_input("8. Document Production", date.today() + timedelta(weeks=18))
    
    with c2:
        if proc_style == "Memorial":
            d['d9'] = st.date_input("9. Statement of Reply", date.today() + timedelta(weeks=22))
            d['d10'] = st.date_input("10. Statement of Rejoinder", date.today() + timedelta(weeks=26))
            d['d12'] = st.date_input("12. Oral Hearing", date.today() + timedelta(weeks=34))
        else:
            d['d9'] = st.date_input("9. Witness Statements", date.today() + timedelta(weeks=22))
            d['d10'] = st.date_input("10. Expert Reports", date.today() + timedelta(weeks=26))
            d['d14'] = st.date_input("14. Oral Hearing", date.today() + timedelta(weeks=36))

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

# 6. EVIDENCE TAB
with tabs[5]:
    st.subheader("Evidence Protocols")
    
    st.markdown("#### Document Production")
    display_hint("doc_prod")
    display_hint("limits")
    display_hint("privilege_std")
    display_hint("privilege_logs")
    
    context['time_produce_docs'] = st.text_input("Time to Produce Docs", context['time_produce_docs'])
    
    st.divider()
    st.markdown("#### Witnesses & Experts")
    display_hint("witness_exam")
    display_hint("expert_meeting")
    display_hint("expert_hot_tub")
    display_hint("expert_reply")
    
    context['time_notify_oral'] = st.text_input("Notice for Oral Evidence", context['time_notify_oral'])

# 7. HEARING TAB
with tabs[6]:
    st.subheader("Hearing Logistics")
    
    display_hint("venue_type")
    display_hint("physical_venue_preference")
    display_hint("interpretation")
    display_hint("chess_clock")
    display_hint("transcription")
    display_hint("demonstratives")
    
    c1, c2 = st.columns(2)
    context['place_in_person'] = c1.text_input("Physical Venue Name", context['place_in_person'])
    context['physical_venue_city'] = c1.text_input("City", context['physical_venue_city'])
    context['hearing_hours'] = c2.text_input("Hearing Hours", context['hearing_hours'])
    context['time_appoint_interpreter'] = c2.text_input("Time to Appoint Interpreter", context['time_appoint_interpreter'])
    
    context['schedule_oral_hearing'] = st.text_area("Hearing Agenda", context['schedule_oral_hearing'])
    context['prehearing_matters'] = st.text_area("Pre-Hearing Matters", context['prehearing_matters'])

# 8. LOGISTICS TAB
with tabs[7]:
    st.subheader("Procedural Logistics")
    
    st.markdown("#### Submissions & Technology")
    display_hint("limits_submission")
    display_hint("ai_guidelines")
    display_hint("deadline_timezone")
    display_hint("time_shred_docs")
    display_hint("platform")
    display_hint("bundling")
    
    c1, c2 = st.columns(2)
    context['limits_submission'] = c1.text_area("Page Limits Clause", context['limits_submission'])
    context['max_filename_len'] = c2.text_input("Max Filename Length", context['max_filename_len'])
    context['deadline_timezone'] = c2.text_input("Deadline Timezone", context['deadline_timezone'])
    context['time_shred_docs'] = c2.text_input("Time to Shred Docs", context['time_shred_docs'])
    
    st.divider()
    st.markdown("#### Communications")
    display_hint("extensions")
    
    c1, c2 = st.columns(2)
    context['time_abbreviations'] = c1.text_input("Time for Abbreviations", context['time_abbreviations'])
    context['time_confirm_contact'] = c1.text_input("Time to Confirm Contact", context['time_confirm_contact'])
    context['time_notify_counsel'] = c2.text_input("Time to Notify New Counsel", context['time_notify_counsel'])
    context['time_hearing_bundle'] = c2.text_input("Bundle Deadline", context['time_hearing_bundle'])
    context['time_submit_exhibits'] = c1.text_input("Hearing Exhibits Deadline", context['time_submit_exhibits'])
    context['date_decide_venue'] = c2.text_input("Venue Decision Deadline", context['date_decide_venue'])

# 9. AWARD TAB
with tabs[8]:
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

# --- GENERATION BUTTON ---
if st.button("Generate PO1 & Sync", type="primary", use_container_width=True):
    template_path = "template_po1.docx"
    
    if not os.path.exists(template_path):
        st.error(f"System Error: Template file '{template_path}' not found. Please upload it to GitHub.")
    else:
        # 1. Sync Timeline to Database
        count = save_schedule(d, proc_style)
        st.toast(f"System Update: Synced {count} events to Smart Timeline.")
        
        # 2. Generate Document
        try:
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
        except Exception as e:
            st.error(f"Generation Failed: {e}")
