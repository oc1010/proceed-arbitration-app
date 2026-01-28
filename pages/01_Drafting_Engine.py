import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
import pandas as pd
from db import load_responses, save_complex_data
import re

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied. Only the Arbitrator can draft PO1.")
    st.stop()

# --- 1. LOAD DATA ---
p1 = load_responses("phase1")
p2 = load_responses("phase2")
claimant = p2.get('claimant', {})
respondent = p2.get('respondent', {})
c_p1 = p1.get('claimant', {})

# --- 2. LOGIC HELPERS ---
def clean_answer(raw_text):
    """
    Strips '**Option X:**' and markdown to find the core meaning.
    Example: "**Option A:** Single Phase." -> "Single Phase"
    """
    if not raw_text or raw_text == "Pending": return ""
    # Remove markdown bolding
    text = raw_text.replace("**", "")
    # Remove "Option X:" prefix
    if "Option " in text and ":" in text:
        return text.split(":", 1)[1].strip()
    return text.strip()

def get_legal_text(key, raw_answer):
    """
    Maps the cleaned answer to the full legal clause in LIB.
    """
    clean = clean_answer(raw_answer)
    # 1. Try exact match in LIB
    if key in LIB:
        for option_key, legal_clause in LIB[key].items():
            if option_key in raw_answer: # "Option A" in "**Option A:**..."
                return legal_clause
            if clean in legal_clause: # Content match
                return legal_clause
    # 2. Fallback: Return the cleaned text (better than raw option)
    return clean

def decision_widget(label, var_name, key_in_db, lib_key=None, default_text="", help_note=""):
    """
    Visual widget for Arbitrator decision making.
    """
    with st.container():
        c_top, c_chk = st.columns([4, 1])
        c_top.markdown(f"**{label}**")
        
        # Unique key using var_name to prevent duplicates
        is_included = c_chk.checkbox("Include?", value=True, key=f"chk_{var_name}")
        
        if not is_included:
            st.divider()
            return "" # Returns empty string to template

        if help_note: st.caption(help_note)
        
        c_ans = claimant.get(key_in_db, "Pending")
        r_ans = respondent.get(key_in_db, "Pending")
        
        cols = st.columns([1, 1, 2])
        with cols[0]:
            st.info(f"👤 **Claimant:**\n\n{c_ans}")
        with cols[1]:
            st.warning(f"👤 **Respondent:**\n\n{r_ans}")
        
        # Determine Default Text
        # If LIB key provided, try to map the answer to legal text
        if lib_key:
            suggested_text = get_legal_text(lib_key, c_ans)
        else:
            suggested_text = clean_answer(c_ans)
            
        final_default = default_text if default_text else suggested_text

        with cols[2]:
            val = st.text_area(f"Final Clause ({label})", value=final_default, key=f"in_{var_name}", height=100)
        
        st.divider()
        return val

# --- 3. CLAUSE LIBRARIES ---
# Maps "Option" keywords to Full Professional Legal Text
LIB = {
    "bifurcation": {
        "Option A": "The Tribunal shall hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
        "Option B": "Pursuant to LCIA Article 22.1(vii), the proceedings are bifurcated. Phase 1 shall address Liability only."
    },
    "consolidation": {
        "Option A": "This arbitration stands alone; no consolidation or concurrent conduct is anticipated.",
        "Option B": "The proceedings shall be consolidated."
    },
    "style": {
        "Option A": "The Parties shall submit written submissions in the Memorial Style (simultaneous exchange of evidence).",
        "Option B": "The Parties shall submit written submissions in the Pleading Style (evidence follows disclosure)."
    },
    "doc_prod": {
        "Option A": "The Tribunal shall be bound by the IBA Rules on the Taking of Evidence (2020).",
        "Option B": "The Tribunal shall be guided by the IBA Rules on the Taking of Evidence (2020).",
        "Option C": "The Tribunal shall apply the general evidentiary powers under the LCIA Rules."
    },
    "limits": {
        "Option A": "Requests shall be subject to the standard of relevance and materiality in the IBA Rules.",
        "Option B": "Requests are capped at 20 per party.",
        "Option C": "No document production shall take place."
    },
    "venue": {
        "At Seat": "The Oral Hearing shall be held physically at the Seat of Arbitration.",
        "Neutral Venue": "The Oral Hearing shall be held physically at a neutral venue (IDRC London).",
        "Virtual": "The Oral Hearing shall be held virtually via video conference."
    },
    "cost_alloc": {
        "Option A": "Costs shall be allocated on the principle that 'costs follow the event' (loser pays).",
        "Option B": "Costs shall be apportioned reflecting the relative success of the Parties on individual issues."
    }
}

# --- 4. APP UI ---
st.title("📝 Procedural Order No. 1 - Drafting Cockpit")

# Initialize Timetable State
if "timetable_df" not in st.session_state:
    st.session_state.timetable_df = pd.DataFrame([
        {"Step": 1, "Date": date.today() + timedelta(weeks=4), "Party": "Claimant", "Action": "Statement of Case", "Notes": "Incl. Witness Statements"},
        {"Step": 2, "Date": date.today() + timedelta(weeks=8), "Party": "Respondent", "Action": "Statement of Defence", "Notes": "Incl. Witness Statements"},
    ])

# TABS
t1, t2, t3, t4, t5, t6 = st.tabs(["1. General", "2. Timetable Builder", "3. Evidence", "4. Hearing", "5. Costs", "6. Misc"])

ctx = {} # Dictionary for Jinja2

with t1:
    st.header("General & Constitution")
    c1, c2 = st.columns(2)
    ctx['Case_Number'] = c1.text_input("Case Reference", "ARB/24/001")
    ctx['seat_of_arbitration'] = c2.text_input("Seat", "London")
    ctx['meeting_date'] = str(date.today())
    ctx['date_of_order'] = str(date.today())
    ctx['governing_law_of_contract'] = st.text_input("Governing Law", "English Law")
    
    with st.expander("Edit Party & Tribunal Names (Fill this to populate PO1)", expanded=True):
        c3, c4 = st.columns(2)
        ctx['claimant_rep_1'] = c3.text_input("Claimant Rep 1", "Ms. Jane Doe")
        ctx['claimant_rep_2'] = c3.text_input("Claimant Rep 2", "")
        ctx['respondent_rep_1'] = c4.text_input("Respondent Rep 1", "Mr. John Smith")
        ctx['respondent_rep_2'] = c4.text_input("Respondent Rep 2", "")
        
        # Hidden Address Fields (Populated with defaults to prevent blank lines)
        ctx['Contact_details_of_Claimant'] = "Claimant Address"
        ctx['Contact_details_of_Respondent'] = "Respondent Address"
        ctx['Contact_details_of_Claimant_Representative'] = "counsel@claimant.com"
        ctx['Contact_details_of_Respondent_Representative'] = "counsel@respondent.com"
        
        t1, t2, t3 = st.columns(3)
        ctx['Contact_details_of_Arbitrator_1'] = t1.text_input("Co-Arb 1", "Dr. A")
        ctx['Contact_details_of_Arbitrator_2'] = t2.text_input("Co-Arb 2", "Ms. B")
        ctx['Contact_details_of_Arbitrator_3_Presiding'] = t3.text_input("Presiding", "Prof. C")

    ctx['bifurcation_decision'] = decision_widget("Bifurcation", "bif", "bifurcation", "bifurcation")
    ctx['consolidation_decision'] = decision_widget("Consolidation", "con", "consolidation", "consolidation")
    
    sec_clause = decision_widget("Secretary Appointment", "sec", "secretary", 
        default_text="The Tribunal appoints a Secretary with the consent of the Parties.")
    ctx['tribunal_secretary_appointment'] = sec_clause
    
    # Conditional Fees
    if sec_clause:
        ctx['tribunal_secretary_fees'] = decision_widget("Secretary Fees", "sec_fees", "sec_fees")
    else:
        ctx['tribunal_secretary_fees'] = ""

with t2:
    st.header("📅 Sophisticated Timetable Builder")
    st.info("Design the procedural calendar. The table below will be inserted directly into the PO1.")
    
    # A. PRESET GENERATOR
    col_preset, col_act = st.columns([3, 1])
    preset = col_preset.radio("Load Preset Template:", ["Memorial Style (Front Loaded)", "Pleading Style (Sequential)"], horizontal=True)
    
    if col_act.button("🔄 Apply Preset"):
        base = date.today()
        if "Memorial" in preset:
            data = [
                {"Step": 1, "Date": base + timedelta(weeks=4), "Party": "Claimant", "Action": "Statement of Case", "Notes": "Facts, Law, WS, Experts"},
                {"Step": 2, "Date": base + timedelta(weeks=8), "Party": "Respondent", "Action": "Statement of Defence", "Notes": "Facts, Law, WS, Experts"},
                {"Step": 3, "Date": base + timedelta(weeks=10), "Party": "Both", "Action": "Redfern Requests", "Notes": "Simultaneous exchange"},
                {"Step": 4, "Date": base + timedelta(weeks=12), "Party": "Both", "Action": "Production of Documents", "Notes": "Rolling basis"},
                {"Step": 5, "Date": base + timedelta(weeks=16), "Party": "Claimant", "Action": "Reply Memorial", "Notes": "Responsive evidence only"},
                {"Step": 6, "Date": base + timedelta(weeks=20), "Party": "Respondent", "Action": "Rejoinder Memorial", "Notes": "Responsive evidence only"},
                {"Step": 7, "Date": base + timedelta(weeks=24), "Party": "All", "Action": "Pre-Hearing Conference", "Notes": "Virtual"},
                {"Step": 8, "Date": base + timedelta(weeks=28), "Party": "All", "Action": "Oral Hearing", "Notes": "10 Days reserved"}
            ]
        else:
            data = [
                {"Step": 1, "Date": base + timedelta(weeks=4), "Party": "Claimant", "Action": "Statement of Case", "Notes": "Pleadings only"},
                {"Step": 2, "Date": base + timedelta(weeks=8), "Party": "Respondent", "Action": "Statement of Defence", "Notes": "Pleadings only"},
                {"Step": 3, "Date": base + timedelta(weeks=12), "Party": "Both", "Action": "Document Production", "Notes": "Standard Redfern"},
                {"Step": 4, "Date": base + timedelta(weeks=16), "Party": "Both", "Action": "Exchange of Witness Statements", "Notes": "Simultaneous"},
                {"Step": 5, "Date": base + timedelta(weeks=24), "Party": "All", "Action": "Oral Hearing", "Notes": ""}
            ]
        st.session_state.timetable_df = pd.DataFrame(data)
        st.rerun()

    # B. INTERACTIVE EDITOR
    st.markdown("### ✏️ Edit Schedule")
    edited_df = st.data_editor(
        st.session_state.timetable_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Step": st.column_config.NumberColumn(width="small"),
            "Date": st.column_config.DateColumn(format="DD MMM YYYY"),
            "Party": st.column_config.SelectboxColumn(options=["Claimant", "Respondent", "Both", "Tribunal", "All"]),
            "Action": st.column_config.TextColumn(width="large"),
            "Notes": st.column_config.TextColumn(width="medium")
        }
    )
    st.session_state.timetable_df = edited_df
    
    # C. FORMATTING FOR WORD (Text-Table)
    table_text = ""
    for _, row in edited_df.iterrows():
        d_str = row['Date'].strftime("%d %B %Y") if isinstance(row['Date'], date) else str(row['Date'])
        table_text += f"{row['Step']}. {d_str} | {row['Party']}: {row['Action']} ({row['Notes']})\n"
    
    ctx['procedural_timetable_table'] = table_text
    
    # Mediation Window Logic
    ctx['mediation_window_clause'] = decision_widget("Mediation Window", "med", "mediation")

with t3:
    st.header("Evidence")
    
    # Platform Logic (Matches template {{ platform_usage_clause }})
    plat_choice = claimant.get("platform", "Pending")
    
    PROCEED_PROTOCOL = "The Parties and the Arbitral Tribunal shall use the PROCEED platform for all filings and the procedural calendar."
    EMAIL_PROTOCOL = "The Parties shall conduct case management via email."
    
    default_plat = PROCEED_PROTOCOL if "PROCEED" in plat_choice else EMAIL_PROTOCOL
    ctx['platform_usage_clause'] = decision_widget("Platform Usage Protocol", "plat", "platform", default_text=default_plat)

    ctx['submission_style_decision'] = decision_widget("Submission Style", "style", "style", "style")
    ctx['page_limits_decision'] = decision_widget("Page Limits", "pg", "limits_submission")
    ctx['last_submission_definition'] = decision_widget("Last Submission Def.", "last", "last_submission")
    
    st.divider()
    ctx['evidence_rules_decision'] = decision_widget("IBA Rules", "iba", "doc_prod", "doc_prod")
    ctx['doc_prod_limits_decision'] = decision_widget("Doc Prod Limits", "lim", "limits", "limits")
    ctx['privilege_standard_decision'] = decision_widget("Privilege Standard", "priv", "privilege_std")
    ctx['privilege_logs_decision'] = decision_widget("Privilege Logs", "logs", "privilege_logs")
    
    st.subheader("Witnesses & Experts")
    ctx['witness_exam_rule'] = decision_widget("Witness Exam Scope", "wit", "witness_exam")
    ctx['expert_meeting_decision'] = decision_widget("Expert Meetings", "exp_meet", "expert_meeting")
    ctx['expert_hottubing_decision'] = decision_widget("Expert Hot-Tubbing", "exp_tub", "expert_hot_tub")

with t4:
    st.header("Hearing")
    c_p1_val = c_p1.get('p1_hearing', '')
    ctx['hearing_venue_decision'] = decision_widget("Hearing Venue", "venue", "physical_venue_preference", "venue", help_note=f"Phase 1 Pref: {c_p1_val}")
    
    # Add input for the Missing City Variable
    ctx['physical_venue_city'] = st.text_input("City of Hearing (e.g. London)", "London")
    
    ctx['chess_clock_decision'] = decision_widget("Chess Clock", "clock", "chess_clock")
    ctx['transcription_decision'] = decision_widget("Transcription", "trans", "transcription")
    ctx['demonstratives_decision'] = decision_widget("Demonstratives", "demo", "demonstratives")
    ctx['interpretation_decision'] = decision_widget("Interpretation", "interp", "interpretation")

with t5:
    st.header("Costs & Award")
    ctx['cost_allocation_decision'] = decision_widget("Cost Principle", "cost", "cost_allocation", "cost_alloc")
    ctx['counsel_fee_cap_decision'] = decision_widget("Fee Caps", "fees", "counsel_fees")
    
    # FIXED KEYS TO PREVENT CRASH
    ctx['internal_costs_decision'] = decision_widget("Internal Costs", "int_cost", "internal_costs")
    ctx['deposit_structure_decision'] = decision_widget("Deposits", "dep", "deposits")
    
    st.divider()
    ctx['award_currency_decision'] = decision_widget("Currency", "curr", "currency")
    ctx['interest_decision'] = decision_widget("Interest", "interest_rate", "interest")
    ctx['signature_format_decision'] = decision_widget("Signature", "sign", "sign_award")
    ctx['publication_decision'] = decision_widget("Publication", "pub", "publication")

with t6:
    st.header("Misc & Tech")
    ctx['funding_disclosure_clause'] = decision_widget("TPF Disclosure", "fund", "funding")
    ctx['ai_guidelines_clause'] = decision_widget("AI Guidelines", "ai", "ai_guidelines")
    ctx['green_protocols_clause'] = decision_widget("Green Protocols", "green", "sustainability")
    ctx['disability_clause'] = decision_widget("Accessibility", "dis", "disability")
    ctx['gdpr_clause'] = decision_widget("GDPR", "gdpr", "gdpr")
    
    # Fillers for other template variables to avoid errors
    ctx['deadline_timezone'] = "17:00 (Seat of Arbitration)"
    ctx['time_abbreviations'] = "7 days"
    ctx['time_confirm_contact'] = "7 days"
    ctx['time_notify_counsel'] = "immediately"
    ctx['time_shred_docs'] = "6 months"
    ctx['time_notify_oral'] = "45 days"
    ctx['time_appoint_interpreter'] = "14 days"
    ctx['time_submit_exhibits'] = "48 hours"
    ctx['hearing_hours'] = "09:30 to 17:30"
    ctx['schedule_oral_hearing'] = "Standard Agenda"
    ctx['time_hearing_bundle'] = "14 days"
    ctx['time_produce_docs'] = "28 days"
    ctx['max_filename_len'] = "50 characters"
    ctx['prehearing_matters'] = "Logistics, Bundles, and Demonstratives"

# --- GENERATE ---
st.divider()
c_gen, c_sync = st.columns([1, 4])

with c_gen:
    if st.button("🚀 Generate PO1", type="primary"):
        try:
            doc = DocxTemplate("template_po1.docx")
            doc.render(ctx)
            
            buf = BytesIO()
            doc.save(buf)
            buf.seek(0)
            
            st.download_button("📥 Download PO1", buf, "Procedural_Order_1.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
            st.success("Draft Generated!")
        except Exception as e:
            st.error(f"Template Error: {e}")

with c_sync:
    if st.button("🔄 Sync Timetable to Phase 4"):
        # Convert df to timeline events for Smart Timeline
        events = []
        for _, row in st.session_state.timetable_df.iterrows():
            events.append({
                "id": f"evt_{row['Step']}",
                "event": row['Action'],
                "current_date": str(row['Date']),
                "owner": row['Party'],
                "status": "Upcoming",
                "logistics": row['Notes']
            })
        save_complex_data("timeline", events)
        st.success(f"Synced {len(events)} events to Smart Timeline.")
