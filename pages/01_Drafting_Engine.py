import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
import pandas as pd
from db import load_responses, save_complex_data
import os
import traceback

st.set_page_config(page_title="Drafting Engine", layout="wide")

# --- ACCESS CONTROL ---
if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied. Only the Arbitrator can draft PO1.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- 1. LOAD DATA ---
p1 = load_responses("phase1")
p2 = load_responses("phase2")
claimant = p2.get('claimant', {})
respondent = p2.get('respondent', {})
c_p1 = p1.get('claimant', {})

# --- 2. LOGIC HELPERS ---
def clean_answer(raw_text):
    if not raw_text or raw_text == "Pending": return "Pending"
    text = raw_text.replace("**", "").replace("*", "")
    if "Option " in text and ":" in text:
        parts = text.split(":", 1)
        if len(parts) > 1:
            return parts[1].strip()
    return text.strip()

def update_clause_text(var_name, lib_key):
    """Callback: Updates the text area when radio button changes."""
    radio_key = f"rad_{var_name}"
    text_key = f"in_{var_name}"
    if radio_key in st.session_state:
        selected_label = st.session_state[radio_key]
        if lib_key in LIB and selected_label in LIB[lib_key]:
            new_text = LIB[lib_key][selected_label]
            st.session_state[text_key] = new_text

def decision_widget(label, var_name, key_in_db, lib_key=None, default_text="", help_note=""):
    with st.container():
        c_top, c_chk = st.columns([4, 1])
        c_top.markdown(f"**{label}**")
        is_included = c_chk.checkbox("Include?", value=True, key=f"chk_{var_name}")
        if not is_included:
            st.divider()
            return "" 

        c_ans = claimant.get(key_in_db, "Pending")
        r_ans = respondent.get(key_in_db, "Pending")
        
        cols = st.columns([1, 1, 2])
        with cols[0]:
            st.info(f"👤 **Claimant:**\n\n{clean_answer(c_ans)}")
        with cols[1]:
            st.warning(f"👤 **Respondent:**\n\n{clean_answer(r_ans)}")
        
        with cols[2]:
            if lib_key and lib_key in LIB:
                options_dict = LIB[lib_key]
                options_list = list(options_dict.keys())
                radio_key = f"rad_{var_name}"
                default_idx = 0
                if radio_key not in st.session_state:
                    for i, k in enumerate(options_list):
                        if k.split("(")[0].strip() in c_ans:
                            default_idx = i
                            break
                st.radio(
                    "Select Variation:",
                    options_list,
                    index=default_idx if radio_key not in st.session_state else None,
                    key=radio_key,
                    horizontal=True,
                    label_visibility="collapsed",
                    on_change=update_clause_text,
                    args=(var_name, lib_key)
                )
                text_key = f"in_{var_name}"
                if text_key not in st.session_state:
                    current_radio = st.session_state.get(radio_key, options_list[default_idx])
                    st.session_state[text_key] = options_dict[current_radio]
            elif f"in_{var_name}" not in st.session_state:
                st.session_state[f"in_{var_name}"] = default_text if default_text else clean_answer(c_ans)
            final_val = st.text_area("Final Clause Content", key=f"in_{var_name}", height=100)
        st.divider()
        return final_val

# --- 3. CLAUSE LIBRARY ---
LIB = {
    "bifurcation": {
        "Option A (Single)": "The Tribunal shall hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
        "Option B (Bifurcated)": "Pursuant to LCIA Article 22.1(vii), the proceedings are bifurcated. Phase 1 shall address Liability only."
    },
    "consolidation": {
        "Option A (None)": "This arbitration stands alone; no consolidation or concurrent conduct is anticipated.",
        "Option B (Consolidated)": "The proceedings shall be consolidated with related proceedings."
    },
    "secretary": {
        "Option A (Appointed)": "The Tribunal appoints a Tribunal Secretary with the consent of the Parties.",
        "Option B (None)": "No Tribunal Secretary shall be appointed."
    },
    "sec_fees": {
        "Option A (Hourly)": "The Tribunal Secretary's fees shall be charged at a rate between £75 and £175 per hour, in accordance with the standard LCIA Schedule of Costs.",
        "Option B (No Fee)": "The Tribunal Secretary shall not bill separately for their time."
    },
    "mediation": {
        "Option A (Window)": "The procedural timetable includes a specific window for mediation stay, should the Parties agree to utilise it.",
        "Option B (No Window)": "No specific stay for mediation is included, though the Parties may agree to mediate at any time."
    },
    "style": {
        "Option A (Memorial)": "The Parties shall submit written submissions in the Memorial Style, involving the simultaneous exchange of evidence with pleadings.",
        "Option B (Pleading)": "The Parties shall submit written submissions in the Pleading Style, where evidence is exchanged only after the disclosure phase."
    },
    "platform": {
        "Option A (PROCEED)": 'The Parties and the Arbitral Tribunal shall use the PROCEED platform ("Platform") for all filings and the procedural calendar.',
        "Option B (Email)": "The Parties shall conduct case management via email and file documents in PDF format."
    },
    "page_limits": {
        "Option A (None)": "There are no specific page limits for submissions. The Parties are to exercise reasonable discretion.",
        "Option B (Strict)": "Strict page limits shall apply to all written submissions as directed by the Tribunal.",
        "Option C (Legal Only)": "Page limits shall apply to the legal argument sections only."
    },
    "last_submission": {
        "Option A (Merits)": "The 'Last Submission' triggering the reporting period is defined as the final Post-Hearing Brief on the merits.",
        "Option B (Final Filing)": "The 'Last Submission' is defined as the very last filing in the arbitration, including Submissions on Costs."
    },
    "doc_prod": {
        "Option A (IBA Bound)": "The Tribunal shall be bound by the IBA Rules on the Taking of Evidence (2020).",
        "Option B (IBA Guided)": "The Tribunal shall be guided by the IBA Rules on the Taking of Evidence (2020).",
        "Option C (LCIA General)": "The Tribunal shall apply the general evidentiary powers under the LCIA Rules without specific reference to the IBA Rules."
    },
    "limits": {
        "Option A (Relevance)": "Document requests shall be subject to the standard of relevance and materiality set out in the IBA Rules.",
        "Option B (Capped)": "Document requests shall be capped at a maximum number to strictly control costs.",
        "Option C (None)": "No document production shall take place in these proceedings."
    },
    "privilege_std": {
        "Option A (Seat Law)": "The Tribunal shall determine issues of legal privilege in accordance with the rules of privilege applicable at the Seat of Arbitration.",
        "Option B (Most Favored)": "The Tribunal shall determine issues of legal privilege in accordance with the rules most favorable to maintaining the privilege."
    },
    "privilege_logs": {
        "Option A (Required)": "Parties withholding documents on grounds of privilege must produce a detailed privilege log describing the document and the basis for privilege.",
        "Option B (On Dispute)": "Privilege logs are not required unless specifically ordered by the Tribunal following a dispute."
    },
    "witness_exam": {
        "Option A (Limited)": "Witness statements shall stand as evidence-in-chief, and direct examination at the hearing shall be limited.",
        "Option B (Full)": "Witnesses may be subject to full direct examination at the hearing."
    },
    "expert_meeting": {
        "Option A (Joint Report)": "Expert counterparts shall meet and produce a Joint Report identifying areas of agreement and disagreement prior to the hearing.",
        "Option B (None)": "No formal pre-hearing meeting of experts is required."
    },
    "expert_hot_tub": {
        "Option A (Sequential)": "Experts shall be examined sequentially, one after the other.",
        "Option B (Concurrent)": "Experts shall be examined concurrently ('hot-tubbing') on an issue-by-issue basis."
    },
    "venue": {
        "At Seat": "The Oral Hearing shall be held physically at the Seat of Arbitration.",
        "Neutral Venue": "The Oral Hearing shall be held physically at a neutral venue (IDRC London).",
        "Virtual": "The Oral Hearing shall be held virtually via video conference."
    },
    "chess_clock": {
        "Option A (Strict)": "Time allocation at the hearing shall be managed using the 'Chess Clock' method, with a fixed split of total hearing time allocated to each Party.",
        "Option B (Flexible)": "The Tribunal shall manage time allocation flexibly without a strict Chess Clock."
    },
    "transcription": {
        "Option A (Real-time)": "Live, real-time transcription is required for the hearing.",
        "Option B (Daily)": "Daily transcripts shall be provided at the end of each hearing day."
    },
    "demonstratives": {
        "Option A (24h Notice)": "Demonstrative exhibits must be exchanged in hard copy or email at least 24 hours before use.",
        "Option B (No Notice)": "Demonstrative exhibits may be used without prior exchange provided they contain no new evidence."
    },
    "interpretation": {
        "Option A (English Only)": "The proceedings will be conducted entirely in English; no interpretation is anticipated.",
        "Option B (Required)": "Interpretation services shall be arranged for witnesses testifying in other languages."
    },
    "cost_alloc": {
        "Option A (Loser Pays)": "Costs shall be allocated on the principle that 'costs follow the event' (the loser pays).",
        "Option B (Apportioned)": "Costs shall be apportioned reflecting the relative success of the Parties on individual issues."
    },
    "counsel_fees": {
        "Option A (Reasonable)": "Recoverable counsel fees shall be subject to the principle of reasonableness and assessed by reference to applicable market rates.",
        "Option B (Capped)": "Counsel fees shall be capped at a fixed amount determined by the Tribunal."
    },
    "internal_costs": {
        "Option A (Recoverable)": "Reasonable internal management costs incurred by the Parties are recoverable.",
        "Option B (Not Recoverable)": "Internal management costs are not recoverable."
    },
    "deposits": {
        "Option A (50/50)": "Administrative deposits shall be split 50/50 between Claimant and Respondent from the outset.",
        "Option B (Claimant First)": "The Claimant shall pay the initial deposit, subject to later adjustment."
    },
    "currency": {
        "Option A (Contract)": "The Award shall be expressed in the currency of the contract.",
        "Option B (Incurred)": "The Award shall be expressed in the currency in which costs were incurred."
    },
    "interest": {
        "Option A (Substantive Law)": "The Tribunal shall apply interest rates and methods prescribed by the applicable substantive law.",
        "Option B (Commercial)": "The Tribunal shall apply a commercial interest rate (e.g., LIBOR/SOFR + 2%)."
    },
    "sign_award": {
        "Option A (Electronic)": "The Parties agree that the Tribunal may sign the Award electronically.",
        "Option B (Wet Ink)": "The Parties require the Award to be signed in 'wet ink' (hard copy)."
    },
    "publication": {
        "Option A (Confidential)": "The award shall remain confidential and shall not be published.",
        "Option B (Redacted)": "The award may be published in redacted form."
    },
    "funding": {
        "Option A (None)": "The Parties confirm that no third-party funding is currently in place.",
        "Option B (Disclose)": "The existence and identity of any third-party funder must be disclosed immediately."
    },
    "ai_guidelines": {
        "Option A (CIArb)": "The Tribunal shall adopt the CIArb Guidelines on the Use of Artificial Intelligence as a guiding text for the Parties' use of technology.",
        "Option B (None)": "No specific guidelines on AI are adopted."
    },
    "green_protocols": {
        "Option A (Adopted)": "The Tribunal and Parties shall conduct the arbitration in accordance with the Green Protocols of the Campaign for Greener Arbitrations.",
        "Option B (None)": "No specific sustainability protocols are adopted."
    },
    "disability": {
        "Option A (Included)": "At any point, either Party may advise the Tribunal of a person who requires reasonable accommodation to facilitate their full participation.",
        "Option B (None)": "No specific clause on accommodations is required."
    },
    "gdpr": {
        "Option A (Standard)": "The Parties agree that standard security measures, including the use of encrypted email and the designated Platform, are sufficient for data protection purposes.",
        "Option B (Protocol)": "A specific Data Protection Protocol shall be established."
    }
}

# --- 4. APP UI ---
st.title("📝 Procedural Order No. 1 - Drafting Cockpit")

if "timetable_df" not in st.session_state:
    st.session_state.timetable_df = pd.DataFrame([
        {"Step": 1, "Date": date.today() + timedelta(weeks=4), "Responsible Party": "Claimant", "Procedural Requirements": "Statement of Case", "Notes": "Incl. Witness Statements"},
        {"Step": 2, "Date": date.today() + timedelta(weeks=8), "Responsible Party": "Respondent", "Procedural Requirements": "Statement of Defence", "Notes": "Incl. Witness Statements"},
    ])

t1, t2, t3, t4, t5, t6 = st.tabs(["1. General", "2. Timetable", "3. Evidence", "4. Hearing", "5. Costs", "6. Misc & Logistics"])

ctx = {} 

with t1:
    st.header("General & Constitution")
    c1, c2 = st.columns(2)
    ctx['Case_Number'] = c1.text_input("Case Reference", "ARB/24/001")
    ctx['seat_of_arbitration'] = c2.text_input("Seat", "London")
    ctx['meeting_date'] = str(date.today())
    ctx['date_of_order'] = str(date.today())
    ctx['governing_law_of_contract'] = st.text_input("Governing Law", "English Law")
    
    with st.expander("Edit Party & Tribunal Names", expanded=True):
        c3, c4 = st.columns(2)
        ctx['claimant_rep_1'] = c3.text_input("Claimant Rep 1", "Ms. Jane Doe")
        ctx['claimant_rep_2'] = c3.text_input("Claimant Rep 2", "")
        ctx['respondent_rep_1'] = c4.text_input("Respondent Rep 1", "Mr. John Smith")
        ctx['respondent_rep_2'] = c4.text_input("Respondent Rep 2", "")
        
        ctx['Contact_details_of_Claimant'] = "Claimant Address"
        ctx['Contact_details_of_Respondent'] = "Respondent Address"
        ctx['Contact_details_of_Claimant_Representative'] = "counsel@claimant.com"
        ctx['Contact_details_of_Respondent_Representative'] = "counsel@respondent.com"
        
        t1_col, t2_col, t3_col = st.columns(3)
        ctx['Contact_details_of_Arbitrator_1'] = t1_col.text_input("Co-Arb 1", "Dr. A")
        ctx['Contact_details_of_Arbitrator_2'] = t2_col.text_input("Co-Arb 2", "Ms. B")
        ctx['Contact_details_of_Arbitrator_3_Presiding'] = t3_col.text_input("Presiding", "Prof. C")

    ctx['bifurcation_decision'] = decision_widget("Bifurcation", "bif", "bifurcation", "bifurcation")
    ctx['consolidation_decision'] = decision_widget("Consolidation", "con", "consolidation", "consolidation")
    sec_clause = decision_widget("Secretary Appointment", "sec", "secretary", "secretary")
    ctx['tribunal_secretary_appointment'] = sec_clause
    if sec_clause and "No Tribunal Secretary" not in sec_clause:
        ctx['tribunal_secretary_fees'] = decision_widget("Secretary Fees", "sec_fees", "sec_fees", "sec_fees")
    else:
        ctx['tribunal_secretary_fees'] = ""

with t2:
    st.header("📅 Procedural Timetable")
    st.info("Configure the steps below. Rows will automatically expand in the generated document.")
    col_preset, col_act = st.columns([3, 1])
    preset = col_preset.radio("Load Preset Template:", ["Memorial Style (Front Loaded)", "Pleading Style (Sequential)"], horizontal=True)
    if col_act.button("🔄 Apply Preset"):
        base = date.today()
        if "Memorial" in preset:
            data = [
                {"Step": 1, "Date": base + timedelta(weeks=4), "Responsible Party": "Claimant", "Procedural Requirements": "Statement of Case", "Notes": "Facts, Law, WS, Experts"},
                {"Step": 2, "Date": base + timedelta(weeks=8), "Responsible Party": "Respondent", "Procedural Requirements": "Statement of Defence", "Notes": "Facts, Law, WS, Experts"},
                {"Step": 3, "Date": base + timedelta(weeks=10), "Responsible Party": "Both", "Procedural Requirements": "Redfern Requests", "Notes": "Simultaneous exchange"},
                {"Step": 4, "Date": base + timedelta(weeks=12), "Responsible Party": "Both", "Procedural Requirements": "Production of Docs", "Notes": "Rolling"},
                {"Step": 5, "Date": base + timedelta(weeks=16), "Responsible Party": "Claimant", "Procedural Requirements": "Reply Memorial", "Notes": "Evidence Only"},
                {"Step": 6, "Date": base + timedelta(weeks=20), "Responsible Party": "Respondent", "Procedural Requirements": "Rejoinder Memorial", "Notes": "Evidence Only"},
                {"Step": 7, "Date": base + timedelta(weeks=24), "Responsible Party": "All", "Procedural Requirements": "Pre-Hearing Conf.", "Notes": "Virtual"},
                {"Step": 8, "Date": base + timedelta(weeks=28), "Responsible Party": "All", "Procedural Requirements": "Oral Hearing", "Notes": "10 Days"}
            ]
        else:
            data = [
                {"Step": 1, "Date": base + timedelta(weeks=4), "Responsible Party": "Claimant", "Procedural Requirements": "Statement of Case", "Notes": "Pleadings"},
                {"Step": 2, "Date": base + timedelta(weeks=8), "Responsible Party": "Respondent", "Procedural Requirements": "Statement of Defence", "Notes": "Pleadings"},
                {"Step": 3, "Date": base + timedelta(weeks=12), "Responsible Party": "Both", "Procedural Requirements": "Document Production", "Notes": "Standard"},
                {"Step": 4, "Date": base + timedelta(weeks=16), "Responsible Party": "Both", "Procedural Requirements": "Witness Statements", "Notes": "Exchange"},
                {"Step": 5, "Date": base + timedelta(weeks=24), "Responsible Party": "All", "Procedural Requirements": "Oral Hearing", "Notes": "10 Days"}
            ]
        st.session_state.timetable_df = pd.DataFrame(data)
        st.rerun()

    edited_df = st.data_editor(
        st.session_state.timetable_df,
        key="timetable_editor", 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Step": st.column_config.NumberColumn(width="small"),
            "Date": st.column_config.DateColumn(format="DD MMM YYYY"),
            "Responsible Party": st.column_config.SelectboxColumn(options=["Claimant", "Respondent", "Both", "Tribunal", "All"]),
            "Procedural Requirements": st.column_config.TextColumn(width="large"),
            "Notes": st.column_config.TextColumn(width="medium")
        }
    )
    
    # --- DYNAMIC TABLE POPULATION ---
    # This list is what the SMART template expects
    timetable_rows = []
    for _, row in edited_df.iterrows():
        d_str = row['Date'].strftime("%d %B %Y") if isinstance(row['Date'], date) else str(row['Date'])
        timetable_rows.append({
            "step": row['Step'],
            "date": d_str,
            "party": row['Responsible Party'],       
            "action": row['Procedural Requirements'], 
            "notes": row['Notes']
        })
    ctx['timetable_rows'] = timetable_rows

    ctx['mediation_window_clause'] = decision_widget("Mediation Window", "med", "mediation", "mediation")

with t3:
    st.header("Evidence")
    ctx['platform_usage_clause'] = decision_widget("Platform Usage Protocol", "plat", "platform", "platform")
    ctx['submission_style_decision'] = decision_widget("Submission Style", "style", "style", "style")
    ctx['page_limits_decision'] = decision_widget("Page Limits", "pg", "limits_submission", "page_limits")
    ctx['last_submission_definition'] = decision_widget("Last Submission Def.", "last", "last_submission", "last_submission")
    st.divider()
    ctx['evidence_rules_decision'] = decision_widget("IBA Rules", "iba", "doc_prod", "doc_prod")
    ctx['doc_prod_limits_decision'] = decision_widget("Doc Prod Limits", "lim", "limits", "limits")
    ctx['privilege_standard_decision'] = decision_widget("Privilege Standard", "priv", "privilege_std", "privilege_std")
    ctx['privilege_logs_decision'] = decision_widget("Privilege Logs", "logs", "privilege_logs", "privilege_logs")
    st.subheader("Witnesses & Experts")
    ctx['witness_exam_scope_decision'] = decision_widget("Witness Exam Scope", "wit", "witness_exam", "witness_exam")
    ctx['expert_meeting_decision'] = decision_widget("Expert Meetings", "exp_meet", "expert_meeting", "expert_meeting")
    ctx['expert_hottubing_decision'] = decision_widget("Expert Hot-Tubbing", "exp_tub", "expert_hot_tub", "expert_hot_tub")

with t4:
    st.header("Hearing Logistics")
    c_p1_val = c_p1.get('p1_hearing', '')
    ctx['hearing_venue_decision'] = decision_widget("Hearing Venue", "venue", "physical_venue_preference", "venue", help_note=f"Phase 1 Pref: {c_p1_val}")
    col_a, col_b = st.columns(2)
    ctx['physical_venue_city'] = col_a.text_input("City of Hearing", "London")
    ctx['hearing_hours'] = col_b.text_input("Hearing Hours", "09:30 to 17:30")
    col_c, col_d = st.columns(2)
    ctx['time_notify_oral'] = col_c.text_input("Notice for Oral Witnesses", "45 days")
    ctx['time_appoint_interpreter'] = col_d.text_input("Time to Appoint Interpreter", "14 days")
    col_e, col_f = st.columns(2)
    ctx['time_hearing_bundle'] = col_e.text_input("Hearing Bundle Deadline", "14 days")
    ctx['time_submit_exhibits'] = col_f.text_input("Submit Exhibits Post-Hearing", "48 hours")
    ctx['date_decide_venue'] = st.text_input("Deadline to Decide Venue", "3 months prior")
    ctx['chess_clock_decision'] = decision_widget("Chess Clock", "clock", "chess_clock", "chess_clock")
    ctx['transcription_decision'] = decision_widget("Transcription", "trans", "transcription", "transcription")
    ctx['demonstratives_decision'] = decision_widget("Demonstratives", "demo", "demonstratives", "demonstratives")
    ctx['interpretation_decision'] = decision_widget("Interpretation", "interp", "interpretation", "interpretation")

with t5:
    st.header("Costs & Award")
    ctx['cost_allocation_decision'] = decision_widget("Cost Principle", "cost", "cost_allocation", "cost_alloc")
    ctx['counsel_fee_cap_decision'] = decision_widget("Fee Caps", "fees", "counsel_fees", "counsel_fees")
    ctx['internal_costs_decision'] = decision_widget("Internal Costs", "int_cost", "internal_costs", "internal_costs")
    ctx['deposit_structure_decision'] = decision_widget("Deposits", "dep", "deposits", "deposits")
    st.divider()
    ctx['award_currency_decision'] = decision_widget("Currency", "curr", "currency", "currency")
    ctx['interest_decision'] = decision_widget("Interest", "interest_rate", "interest", "interest")
    ctx['signature_format_decision'] = decision_widget("Signature", "sign", "sign_award", "sign_award")
    ctx['publication_decision'] = decision_widget("Publication", "pub", "publication", "publication")

with t6:
    st.header("Misc & Logistics")
    ctx['funding_disclosure_clause'] = decision_widget("TPF Disclosure", "fund", "funding", "funding")
    ctx['ai_guidelines_clause'] = decision_widget("AI Guidelines", "ai", "ai_guidelines", "ai_guidelines")
    ctx['green_protocols_clause'] = decision_widget("Green Protocols", "green", "sustainability", "green_protocols")
    ctx['disability_clause'] = decision_widget("Accessibility", "dis", "disability", "disability")
    ctx['gdpr_clause'] = decision_widget("GDPR", "gdpr", "gdpr", "gdpr")
    st.subheader("Document Control & Deadlines")
    col_1, col_2 = st.columns(2)
    ctx['deadline_timezone'] = col_1.text_input("Deadline Timezone", "17:00 (Seat of Arbitration)")
    ctx['time_abbreviations'] = col_2.text_input("Time for Abbrev. List", "7 days")
    col_3, col_4 = st.columns(2)
    ctx['time_confirm_contact'] = col_3.text_input("Confirm Contact Details", "7 days")
    ctx['time_notify_counsel'] = col_4.text_input("Notify New Counsel", "immediately")
    col_5, col_6 = st.columns(2)
    ctx['time_shred_docs'] = col_5.text_input("Time to Shred Docs", "6 months")
    ctx['time_produce_docs'] = col_6.text_input("Time to Produce Docs", "28 days")
    ctx['max_filename_len'] = st.text_input("Max Filename Length", "50 characters")
    ctx['prehearing_matters'] = "Logistics, Bundles, and Demonstratives"

# --- GENERATE ---
st.divider()
c_gen, c_sync = st.columns([1, 4])

with c_gen:
    if st.button("🚀 Generate PO1", type="primary"):
        # SAFETY NET: Fill missing keys with placeholders
        default_keys = [
            'claimant_rep_1', 'claimant_rep_2', 'respondent_rep_1', 'respondent_rep_2',
            'bifurcation_decision', 'consolidation_decision', 'tribunal_secretary_appointment',
            'tribunal_secretary_fees', 'platform_usage_clause', 'mediation_window_clause',
            'cost_allocation_decision', 'counsel_fee_cap_decision', 'internal_costs_decision',
            'deposit_structure_decision', 'award_currency_decision', 'interest_decision',
            'signature_format_decision', 'publication_decision', 'evidence_rules_decision',
            'doc_prod_limits_decision', 'hearing_venue_decision', 'chess_clock_decision',
            'transcription_decision', 'deadline_timezone', 'time_abbreviations', 
            'time_confirm_contact', 'time_notify_counsel', 'time_shred_docs', 
            'time_produce_docs', 'max_filename_len', 'time_hearing_bundle', 
            'time_submit_exhibits', 'hearing_hours', 'ai_guidelines_clause',
            'green_protocols_clause', 'disability_clause', 'gdpr_clause', 
            'privilege_standard_decision', 'privilege_logs_decision', 'witness_exam_scope_decision',
            'expert_meeting_decision', 'expert_hottubing_decision', 'demonstratives_decision',
            'interpretation_decision', 'funding_disclosure_clause', 'submission_style_decision',
            'page_limits_decision', 'last_submission_definition'
        ]
        for key in default_keys:
            if key not in ctx or ctx[key] is None:
                ctx[key] = "[Not Selected]"

        try:
            # ONLY use the Smart Template (prevents using old broken ones)
            target_file = "template_po1_SMART.docx"
            
            if not os.path.exists(target_file):
                # Fallback check
                if os.path.exists("template_po1_FINAL.docx"):
                    target_file = "template_po1_FINAL.docx"
                else:
                    st.error(f"❌ Error: 'template_po1_SMART.docx' not found. Please run the fixer script locally and upload it.")
                    st.stop()

            doc = DocxTemplate(target_file)
            doc.render(ctx)
            
            buf = BytesIO()
            doc.save(buf)
            buf.seek(0)
            
            st.download_button(
                label=f"📥 Download PO1 (Using {target_file})", 
                data=buf, 
                file_name="Procedural_Order_1.docx", 
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            st.success("Draft Generated Successfully!")
                
        except Exception as e:
            st.error("An error occurred during generation:")
            st.code(traceback.format_exc())

with c_sync:
    if st.button("🔄 Sync Timetable to Phase 4"):
        events = []
        for _, row in edited_df.iterrows():
            events.append({
                "id": f"evt_{row['Step']}",
                "event": row['Procedural Requirements'],
                "current_date": str(row['Date']),
                "owner": row['Responsible Party'],
                "status": "Upcoming",
                "logistics": row['Notes']
            })
        save_complex_data("timeline", events)
        st.success(f"Synced {len(events)} events to Smart Timeline.")
