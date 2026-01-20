import streamlit as st
from db import load_structure, save_structure, reset_database
import time

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")
    
    st.divider()
    st.caption("ADMIN ACTIONS")
    if st.button("🔄 Restore Defaults", help="Re-loads the full master list from the template.", use_container_width=True):
        save_structure({"initial_setup": True}) 
        st.toast("Questions restored!")
        st.rerun()

st.title("✏️ Questionnaire Editor")
st.caption("Edit the questions below. Each option is in a separate box for easier editing.")

# --- MASTER QUESTION BANK (MATCHING YOUR DOCX) ---
DEFAULT_QUESTIONS = [
    # I. WRITTEN SUBMISSIONS
    {
        "id": "style", 
        "question": "1. Style of Written Submissions", 
        "type": "radio", 
        "options": [
            "**Option A: Memorial Style.** Simultaneous submission of factual allegations, legal arguments, witness statements, and expert reports with the Statement of Case and Defence. (Front-loaded costs; potentially faster resolution).",
            "**Option B: Pleading Style.** Submission of factual allegations and legal arguments first (with core documents only). Witness statements and expert reports are exchanged only after document production. (Spreads costs over time; traditional English style)."
        ]
    },
    {
        "id": "bifurcation", 
        "question": "2. Bifurcation of Proceedings", 
        "type": "radio", 
        "options": [
            "**Option A: Single Phase.** The Tribunal should hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
            "**Option B: Bifurcation Requested.** The Parties request bifurcation (e.g., Liability determined first, Quantum later) pursuant to LCIA Article 22.1(vii)."
        ]
    },
    
    # II. DOCUMENT PRODUCTION & EVIDENCE
    {
        "id": "doc_prod", 
        "question": "3. Applicable Guidelines (Evidence)", 
        "type": "selectbox", 
        "options": [
            "**Option A: IBA Rules (Binding).** The IBA Rules on the Taking of Evidence (2020) shall apply as binding rules.",
            "**Option B: IBA Rules (Guidelines).** The Tribunal shall be guided by the IBA Rules (2020) but they shall not be binding.",
            "**Option C: None.** No specific guidelines; the Tribunal shall apply the general evidentiary powers under the LCIA Rules.",
            "**Option D: Other.** (e.g. Prague Rules). Please specify in next steps."
        ]
    },
    {
        "id": "limits", 
        "question": "4. Limitations on Document Requests", 
        "type": "radio", 
        "options": [
            "**Option A: Standard (IBA).** No specific numerical limit, subject to relevance and materiality.",
            "**Option B: Capped.** Requests limited to a specific number (e.g., 20 requests per party) to control costs.",
            "**Option C: None.** No document production phase (reliance on documents attached to pleadings only)."
        ]
    },
    {
        "id": "witness_exam", 
        "question": "5. Witness Examination", 
        "type": "radio", 
        "options": [
            "**Option A: Written Evidence Stands.** Witness statements shall stand as evidence-in-chief. Direct examination at the hearing is limited/not permitted.",
            "**Option B: Full Direct Exam.** Witness statements are summaries; full direct examination is required at the hearing.",
            "**Option C: No Hearing.** Cross-examination is waived; the Tribunal will decide based on written witness statements only."
        ]
    },

    # III. ELECTRONIC PROTOCOLS
    {
        "id": "platform", 
        "question": "6. Case Management Platform", 
        "type": "radio", 
        "options": [
            "**Option A: PROCEED Platform.** The Parties agree to use the specific 'PROCEED' platform for all filings, tracking, and the procedural calendar.",
            "**Option B: Email Only.** Individual case management via email/PDF filings only."
        ]
    },
    {
        "id": "bundling", 
        "question": "7. Electronic Bundling", 
        "type": "radio", 
        "options": [
            "**Option A: Joint Bundle.** Joint Hearing Bundle (Parties collaborate on a single indexed bundle).",
            "**Option B: Individual Bundles.** Individual Bundles (Each party prepares its own separate bundle)."
        ]
    },
    {
        "id": "gdpr", 
        "question": "8. Data Protection (GDPR) & Cybersecurity", 
        "type": "radio", 
        "options": [
            "**Option A: Standard.** Standard security measures (encrypted email/platform) are sufficient.",
            "**Option B: Enhanced.** The dispute involves highly sensitive data requiring specific information security protocols under LCIA Article 30A."
        ]
    },

    # IV. COSTS & FUNDING
    {
        "id": "cost_allocation", 
        "question": "9. Cost Allocation Methodology", 
        "type": "radio", 
        "options": [
            "**Option A: Costs follow the event.** ('Loser pays').",
            "**Option B: Apportionment.** Based on relative success of issues.",
            "**Option C: Split Costs.** Parties bear their own legal costs; administrative costs split 50/50."
        ]
    },
    {
        "id": "counsel_fees", 
        "question": "10. Counsel Fees (Recoverability)", 
        "type": "radio", 
        "options": [
            "**Option A: Market Rates.** Market rates apply (recoverable costs must be 'reasonable').",
            "**Option B: Capped Rates.** Recoverable hourly rates for counsel shall be capped at a pre-agreed amount."
        ]
    },
    {
        "id": "internal_costs", 
        "question": "11. Internal Management Costs", 
        "type": "radio", 
        "options": [
            "**Option A: Recoverable.** Reasonable internal management time/costs are recoverable.",
            "**Option B: Not Recoverable.**"
        ]
    },
    {
        "id": "deposits", 
        "question": "12. Administrative Deposits", 
        "type": "radio", 
        "options": [
            "**Option A: Split 50/50.** Split 50/50 between Claimant and Respondent from the outset.",
            "**Option B: Claimant Pays Initial.** Claimant pays 100% of the initial deposit."
        ]
    },

    # V. TRIBUNAL ASSISTANCE
    {
        "id": "secretary", 
        "question": "13. Tribunal Secretary", 
        "type": "radio", 
        "options": [
            "**Option A: Consent.** The Parties consent to the appointment of a Tribunal Secretary to assist with administrative tasks.",
            "**Option B: Object.** The Parties object to the appointment of a Tribunal Secretary."
        ]
    },
    {
        "id": "sec_fees", 
        "question": "14. Tribunal Secretary Fees", 
        "type": "radio", 
        "options": [
            "**Option A: Standard LCIA (£75 - £175 / hr).** Hourly rate between £75 to £175 (per standard LCIA Schedule of Costs).",
            "**Option B: Draft PO1 Template (£100 - £250 / hr).** Hourly rate between £100 to £250 (per the specific draft PO1 template)."
        ]
    },
    {
        "id": "extensions", 
        "question": "15. Protocol for Time Extensions", 
        "type": "selectbox", 
        "options": [
            "**Option A: Standard.** Extensions may be granted by the Tribunal upon a reasoned request showing good cause.",
            "**Option B: Strict.** Extensions granted only in 'exceptional circumstances'.",
            "**Option C: Flexible.** Short extensions (e.g., up to 3 days) may be agreed between parties without Tribunal intervention."
        ]
    },

    # VI. HEARING & TIMING
    {
        "id": "funding", 
        "question": "16. Third-Party Funding", 
        "type": "radio", 
        "options": [
            "**Option A: None.** No third-party funding is currently in place.",
            "**Option B: Exists.** Third-party funding is in place. (Please disclose the identity of the funder immediately)."
        ]
    },
    {
        "id": "deadline_timezone", 
        "question": "17. Definition of 'Deadline' (Timezone)", 
        "type": "radio", 
        "options": [
            "**Option A: Time of the Seat.** Time of the Seat of Arbitration (e.g., 17:00 London time).",
            "**Option B: Time of Presiding Arbitrator.** Time of the Presiding Arbitrator's location.",
            "**Option C: Time of Filing Party.** Time of the filing party's location."
        ]
    },
    {
        "id": "physical_venue_preference", 
        "question": "18. Physical Hearing Venue Preference", 
        "type": "radio", 
        "options": [
            "**Option A: At Seat.** The hearings shall take place physically at the Seat of Arbitration.",
            "**Option B: Neutral Venue.** The hearings shall take place at a different neutral venue (e.g., IDRC London, Maxwell Chambers Singapore)."
        ]
    },
    {
        "id": "interpretation", 
        "question": "19. Interpretation and Translation", 
        "type": "radio", 
        "options": [
            "**Option A: English Only.** The proceedings will be conducted entirely in English; no interpretation is anticipated.",
            "**Option B: Interpretation Required.** One or more witnesses will testify in a language other than English; simultaneous interpretation will be required."
        ]
    },

    # VII. SUBMISSION LIMITS
    {
        "id": "limits_submission", 
        "question": "
