import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_complex_data

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied. Only the Arbitrator can draft PO1.")
    st.stop()

# --- 1. LOAD DATA ---
p1 = load_responses("phase1")
p2 = load_responses("phase2")
claimant = p2.get('claimant', {})
respondent = p2.get('respondent', {})
# Load Phase 1 for specific hearing preferences
c_p1 = p1.get('claimant', {})
r_p1 = p1.get('respondent', {})

# --- 2. HELPER: TIMELINE SYNC (Restored Feature) ---
def sync_timeline_to_db(d1, d2):
    """Syncs the key PO1 dates to the Smart Timeline module."""
    # Basic structure for the timeline
    new_events = [
        {"id": "ev_1", "event": "Statement of Case", "current_date": str(d1), "owner": "Claimant", "status": "Upcoming", "logistics": "Submit via Portal"},
        {"id": "ev_2", "event": "Statement of Defence", "current_date": str(d2), "owner": "Respondent", "status": "Upcoming", "logistics": "Submit via Portal"},
        {"id": "ev_3", "event": "Document Production", "current_date": str(d1 + timedelta(weeks=8)), "owner": "Both", "status": "Upcoming", "logistics": "See Redfern Schedule"},
    ]
    save_complex_data("timeline", new_events)
    return len(new_events)

# --- 3. HELPER: DECISION WIDGET (The Efficiency Engine) ---
def decision_widget(label, var_name, key_in_db, clause_map=None, default_text="", help_note=""):
    """
    Smart component that displays Party preferences and returns the Arbitrator's final text.
    """
    st.markdown(f"**{label}**")
    if help_note: st.caption(help_note)
    
    # Extract answers
    c_ans = claimant.get(key_in_db, "Pending")
    r_ans = respondent.get(key_in_db, "Pending")
    
    # Visual Comparison
    cols = st.columns([1, 1, 2])
    with cols[0]:
        st.info(f"👤 **Claimant:**\n{c_ans}")
    with cols[1]:
        st.warning(f"👤 **Respondent:**\n{r_ans}")
    
    # Determine Default Logic
    # 1. Map the answer to legal text (if map exists)
    c_text = clause_map.get(c_ans, c_ans) if clause_map else c_ans
    
    # 2. Logic: If parties agree, use that. If not, default to Claimant (arbitrary start point) or existing default.
    final_default = default_text
    if c_ans == r_ans and c_ans != "Pending":
        final_default = c_text
    elif c_ans != "Pending":
        final_default = c_text

    # Input Box
    with cols[2]:
        val = st.text_area(f"Final Clause: {label}", value=final_default, key=f"in_{var_name}", height=100)
    
    st.divider()
    return val

# --- 4. CLAUSE LIBRARIES (Logic Mapping) ---
# Maps short Questionnaire Options -> Full Legal Text
LIB = {
    "bifurcation": {
        "Option A: Single Phase.": "The Tribunal shall hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
        "Option B: Bifurcation Requested.": "The proceedings are bifurcated. Phase 1 shall address Liability only pursuant to LCIA Article 22.1(vii)."
    },
    "doc_prod_rules": {
        "Option A: IBA Rules (Binding).": "The IBA Rules on the Taking of Evidence (2020) shall apply as binding rules.",
        "Option B: IBA Rules (Guidelines).": "The Tribunal shall be guided by the IBA Rules on the Taking of Evidence (2020) but they shall not be binding.",
        "Option C: No specific guidelines.": "The Tribunal shall apply the general evidentiary powers under the LCIA Rules."
    },
    "limits": {
        "Option A: Standard (IBA).": "Document requests shall be subject to the standard of relevance and materiality in the IBA Rules.",
        "Option B: Capped.": "Each Party is limited to a maximum of 25 document production requests to control costs.",
        "Option C: None.": "There shall be no document production phase."
    },
    "platform": {
        "Option A: PROCEED Platform.": "The Parties shall use the 'PROCEED' platform for all filings. The timeline on the Platform constitutes the official record.",
        "Option B: Email Only.": "The Parties shall conduct case management via email. Filings shall be submitted in PDF format via email."
    },
    "cost_alloc": {
        "Option A: Costs follow the event.": "Costs shall be allocated on the principle that 'costs follow the event' (loser pays).",
        "Option B: Apportionment.": "Costs shall be apportioned reflecting the relative success of the Parties on individual issues.",
        "Option C: Split Costs.": "Each Party shall bear its own legal costs; administrative costs shall be split 50/50."
    },
    "venue": {
        "At Seat": "physically at the Seat of Arbitration",
        "Neutral Venue": "physically at a neutral venue (IDRC London)",
        "Virtual": "virtually via video conference"
    }
}

# --- 5. MAIN APP ---
st.title("📝 Procedural Order No. 1 - Drafting Cockpit")
st.markdown("This engine synthesizes questionnaire data into a legally binding Procedural Order.")

ctx = {} # Dictionary to store final variables for the template

# --- TABS ---
t1, t2, t3, t4, t5 = st.tabs(["1. Constitution", "2. Evidence", "3. Hearing", "4. Costs & Award", "5. Tech & Misc"])

with t1:
    st.header("General Details & Parties")
    c1, c2 = st.columns(2)
    ctx['seat_of_arbitration'] = c1.text_input("Seat", "London")
    ctx['governing_law_of_contract'] = c2.text_input("Governing Law", "English Law")
    ctx['meeting_date'] = str(date.today())
    ctx['date_of_order'] = str(date.today())
    
    st.subheader("Parties & Tribunal")
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("**Claimant**")
        ctx['claimant_rep_1'] = st.text_input("Claimant Rep Name", "Ms. Jane Doe")
        ctx['claimant_rep_2'] = st.text_input("Claimant Co-Counsel", "")
        ctx['Contact_details_of_Claimant_Representative'] = st.text_area("Claimant Contact", "jane.doe@lawfirm.com", height=68)
    with c4:
        st.markdown("**Respondent**")
        ctx['respondent_rep_1'] = st.text_input("Respondent Rep Name", "Mr. John Smith")
        ctx['respondent_rep_2'] = st.text_input("Respondent Co-Counsel", "")
        ctx['Contact_details_of_Respondent_Representative'] = st.text_area("Respondent Contact", "john.smith@citylaw.com", height=68)

    st.markdown("**Tribunal Members**")
    t_c1, t_c2, t_c3 = st.columns(3)
    ctx['Contact_details_of_Arbitrator_1'] = t_c1.text_input("Co-Arbitrator 1", "Dr. A")
    ctx['Contact_details_of_Arbitrator_2'] = t_c2.text_input("Co-Arbitrator 2", "Ms. B")
    ctx['Contact_details_of_Arbitrator_3_Presiding'] = t_c3.text_input("Presiding Arbitrator", "Prof. C")

    st.markdown("---")
    ctx['bifurcation_decision'] = decision_widget("Bifurcation", "bifurcation", "bifurcation", LIB['bifurcation'])
    ctx['consolidation_decision'] = decision_widget("Consolidation", "consolidation", "consolidation")
    
    st.subheader("Tribunal Secretary")
    sec_appt_map = {"Option A: Consent.": "The Tribunal appoints a Secretary.", "Option B: Object.": "No Secretary is appointed."}
    ctx['tribunal_secretary_clause'] = decision_widget("Appointment", "sec_appt", "secretary", sec_appt_map)
    ctx['tribunal_secretary_fees'] = decision_widget("Fees", "sec_fees", "sec_fees")
    
    st.subheader("Key Dates (Timeline)")
    d1 = st.date_input("Statement of Case Deadline", date.today() + timedelta(weeks=4))
    d2 = st.date_input("Statement of Defence Deadline", date.today() + timedelta(weeks=8))
    ctx['include_mediation_window'] = st.checkbox("Include Mediation Window?", value=False)
    if ctx['include_mediation_window']:
        ctx['mediation_window_clause'] = decision_widget("Mediation Window", "mediation", "mediation")

with t2:
    st.header("Evidence & Documents")
    
    ctx['platform_usage_clause'] = decision_widget("Case Management Platform", "platform", "platform", LIB['platform'])
    ctx['submission_style_decision'] = decision_widget("Submission Style", "style", "style")
    ctx['page_limits_decision'] = decision_widget("Page Limits", "pg_limits", "limits_submission")
    ctx['last_submission_definition'] = decision_widget("Definition of 'Last Submission'", "last_sub", "last_submission")
    
    st.markdown("---")
    ctx['evidence_rules_decision'] = decision_widget("Evidentiary Rules (IBA)", "rules", "doc_prod", LIB['doc_prod_rules'])
    ctx['doc_prod_limits_decision'] = decision_widget("Document Limits", "limits", "limits", LIB['limits'])
    ctx['privilege_standard_decision'] = decision_widget("Privilege Standard", "priv", "privilege_std")
    ctx['privilege_logs_status'] = decision_widget("Privilege Logs", "logs", "privilege_logs")

with t3:
    st.header("Hearing & Witnesses")
    
    # Logic: Fallback to Phase 1 data if Phase 2 is empty for Venue
    c_p1_val = c_p1.get('p1_hearing', 'N/A')
    r_p1_val = r_p1.get('p1_hearing', 'N/A')
    st.caption(f"Phase 1 Venue Prefs -> Claimant: {c_p1_val} | Respondent: {r_p1_val}")
    
    ctx['hearing_venue_decision'] = decision_widget("Hearing Venue", "venue", "physical_venue_preference", LIB['venue'])
    ctx['hearing_format_decision'] = ctx['hearing_venue_decision'] # Duplicate for safety in template
    
    ctx['witness_exam_rule'] = decision_widget("Witness Exam Scope", "wit_scope", "witness_exam")
    ctx['interpretation_decision'] = decision_widget("Interpretation", "interp", "interpretation")
    ctx['expert_meeting_decision'] = decision_widget("Expert Meetings", "exp_meet", "expert_meeting")
    ctx['expert_hottubing_decision'] = decision_widget("Expert Hot-Tubbing", "exp_tub", "expert_hot_tub")
    ctx['chess_clock_decision'] = decision_widget("Time Allocation (Chess Clock)", "clock", "chess_clock")
    ctx['transcription_decision'] = decision_widget("Transcription", "trans", "transcription")
    ctx['demonstratives_decision'] = decision_widget("Demonstrative Exhibits", "demos", "demonstratives")

with t4:
    st.header("Costs & The Award")
    
    ctx['cost_allocation_decision'] = decision_widget("Cost Allocation Principle", "cost_alloc", "cost_allocation", LIB['cost_alloc'])
    ctx['counsel_fee_cap_decision'] = decision_widget("Counsel Fee Caps", "fees", "counsel_fees")
    ctx['internal_costs_decision'] = decision_widget("Internal Mgmt Costs", "int_cost", "internal_costs")
    ctx['deposit_structure_decision'] = decision_widget("Deposits", "deposits", "deposits")
    
    st.divider()
    ctx['award_currency_decision'] = decision_widget("Award Currency", "currency", "currency")
    ctx['interest_decision'] = decision_widget("Interest", "interest", "interest")
    ctx['signature_format_decision'] = decision_widget("Signature Format", "sign", "sign_award")
    ctx['publication_decision'] = decision_widget("Publication", "pub", "publication")

with t5:
    st.header("Modern Procedures & Misc")
    
    ctx['funding_disclosure_clause'] = decision_widget("TPF Disclosure", "funding", "funding")
    ctx['gdpr_clause'] = decision_widget("GDPR Protocol", "gdpr", "gdpr")
    
    st.markdown("### Optional Clauses")
    col_a, col_b, col_c = st.columns(3)
    
    ctx['include_ai_clause'] = col_a.checkbox("Include AI Clause", value=True)
    if ctx['include_ai_clause']:
        ctx['ai_guidelines_clause'] = decision_widget("AI Guidelines", "ai", "ai_guidelines")
        
    ctx['include_green_protocols'] = col_b.checkbox("Include Green Protocols", value=True)
    if ctx['include_green_protocols']:
        ctx['green_protocols_clause'] = decision_widget("Green Protocols", "green", "sustainability")
        
    ctx['include_disability'] = col_c.checkbox("Include Accessibility", value=False)
    if ctx['include_disability']:
        ctx['disability_clause'] = decision_widget("Accessibility", "disability", "disability")

# --- GENERATE & SYNC ---
st.divider()
c_gen, c_sync = st.columns([1, 4])

with c_gen:
    if st.button("🚀 Generate PO1 (.docx)", type="primary"):
        try:
            doc = DocxTemplate("template_po1.docx")
            doc.render(ctx)
            buf = BytesIO()
            doc.save(buf)
            buf.seek(0)
            
            st.download_button(
                label="📥 Download File",
                data=buf,
                file_name="Procedural_Order_1_Final.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.toast("Document Ready!", icon="✅")
        except Exception as e:
            st.error(f"Template Error: {e}")

with c_sync:
    if st.button("🔄 Sync Dates to Timeline"):
        count = sync_timeline_to_db(d1, d2)
        st.success(f"Synced {count} events to the Smart Timeline module.")
