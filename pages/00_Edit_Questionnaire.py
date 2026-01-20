import streamlit as st
from db import load_structure, save_structure, reset_database

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
    if st.button("🔄 Restore Default Questions", help="Re-loads the full master list of questions.", use_container_width=True):
        save_structure({"initial_setup": True}) 
        st.toast("Questions restored!")
        st.rerun()

st.title("✏️ Questionnaire Editor")
st.caption("Customize the questions. Uncheck 'Include' to hide a question for this specific case.")

# --- MASTER QUESTION BANK (Corrected & Detailed) ---
DEFAULT_QUESTIONS = [
    # I. WRITTEN SUBMISSIONS
    {
        "id": "style", 
        "question": "1. Style of Written Submissions", 
        "type": "radio", 
        "options": [
            "Option A: Memorial Style. Simultaneous submission of factual allegations, legal arguments, witness statements, and expert reports with the Statement of Case and Defence. (Front-loaded costs; potentially faster resolution).",
            "Option B: Pleading Style. Submission of factual allegations and legal arguments first (with core documents only). Witness statements and expert reports are exchanged only after document production. (Spreads costs over time; traditional English style)."
        ]
    },
    {
        "id": "bifurcation", 
        "question": "2. Bifurcation of Proceedings", 
        "type": "radio", 
        "options": [
            "Option A: Single Phase. The Tribunal should hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
            "Option B: Bifurcation Requested. The Parties request bifurcation (e.g., Liability determined first, Quantum later) pursuant to LCIA Article 22.1(vii)."
        ]
    },
    
    # II. DOCUMENT PRODUCTION & EVIDENCE
    {
        "id": "doc_prod", 
        "question": "3. Applicable Guidelines (Evidence)", 
        "type": "selectbox", 
        "options": [
            "Option A: IBA Rules (Binding). The IBA Rules on the Taking of Evidence (2020) shall apply as binding rules.",
            "Option B: IBA Rules (Guidelines). The Tribunal shall be guided by the IBA Rules (2020) but they shall not be binding.",
            "Option C: None. No specific guidelines; the Tribunal shall apply the general evidentiary powers under the LCIA Rules.",
            "Option D: Other (e.g. Prague Rules). Please specify in next steps."
        ]
    },
    {
        "id": "limits", 
        "question": "4. Limitations on Document Requests", 
        "type": "radio", 
        "options": [
            "Option A: Standard (IBA). No specific numerical limit, subject to relevance and materiality.",
            "Option B: Capped. Requests limited to a specific number (e.g., 20 requests per party) to control costs.",
            "Option C: None. No document production phase (reliance on documents attached to pleadings only)."
        ]
    },
    {
        "id": "witness_exam", 
        "question": "5. Witness Examination", 
        "type": "radio", 
        "options": [
            "Option A: Written Evidence Stands. Witness statements shall stand as evidence-in-chief. Direct examination at the hearing is limited/not permitted.",
            "Option B: Full Direct Exam. Witness statements are summaries; full direct examination is required at the hearing.",
            "Option C: No Hearing. Cross-examination is waived; the Tribunal will decide based on written witness statements only."
        ]
    },

    # III. ELECTRONIC PROTOCOLS
    {
        "id": "platform", 
        "question": "6. Case Management Platform", 
        "type": "radio", 
        "options": [
            "Option A: PROCEED Platform. The Parties agree to use the specific 'PROCEED' platform for all filings, tracking, and the procedural calendar.",
            "Option B: Email Only. Individual case management via email/PDF filings only."
        ]
    },
    {
        "id": "bundling", 
        "question": "7. Electronic Bundling", 
        "type": "radio", 
        "options": [
            "Option A: Joint Bundle. Joint Hearing Bundle (Parties collaborate on a single indexed bundle).",
            "Option B: Individual Bundles. Individual Bundles (Each party prepares its own separate bundle)."
        ]
    },
    {
        "id": "gdpr", 
        "question": "8. Data Protection (GDPR) & Cybersecurity", 
        "type": "radio", 
        "options": [
            "Option A: Standard. Standard security measures (encrypted email/platform) are sufficient.",
            "Option B: Enhanced. The dispute involves highly sensitive data requiring specific information security protocols under LCIA Article 30A."
        ]
    },

    # IV. COSTS & FUNDING
    {
        "id": "cost_allocation", 
        "question": "9. Cost Allocation Methodology", 
        "type": "radio", 
        "options": [
            "Option A: Costs follow the event ('Loser pays').",
            "Option B: Apportionment based on relative success of issues.",
            "Option C: Parties bear their own legal costs; administrative costs split 50/50."
        ]
    },
    {
        "id": "counsel_fees", 
        "question": "10. Counsel Fees (Recoverability)", 
        "type": "radio", 
        "options": [
            "Option A: Market Rates. Market rates apply (recoverable costs must be 'reasonable').",
            "Option B: Capped Rates. Recoverable hourly rates for counsel shall be capped at a pre-agreed amount."
        ]
    },
    {
        "id": "internal_costs", 
        "question": "11. Internal Management Costs", 
        "type": "radio", 
        "options": [
            "Option A: Recoverable. Reasonable internal management time/costs are recoverable.",
            "Option B: Not Recoverable."
        ]
    },
    {
        "id": "deposits", 
        "question": "12. Administrative Deposits", 
        "type": "radio", 
        "options": [
            "Option A: Split 50/50. Split 50/50 between Claimant and Respondent from the outset.",
            "Option B: Claimant Pays Initial. Claimant pays 100% of the initial deposit."
        ]
    },

    # V. TRIBUNAL ASSISTANCE
    {
        "id": "secretary", 
        "question": "13. Tribunal Secretary", 
        "type": "radio", 
        "options": [
            "Option A: Consent. The Parties consent to the appointment of a Tribunal Secretary to assist with administrative tasks.",
            "Option B: Object. The Parties object to the appointment of a Tribunal Secretary."
        ]
    },
    {
        "id": "sec_fees", 
        "question": "14. Tribunal Secretary Fees", 
        "type": "radio", 
        "options": [
            "Option A: Standard LCIA (£75 - £175 / hr). Hourly rate between £75 to £175 (per standard LCIA Schedule of Costs).",
            "Option B: Draft PO1 Template (£100 - £250 / hr). Hourly rate between £100 to £250 (per the specific draft PO1 template)."
        ]
    },
    {
        "id": "extensions", 
        "question": "15. Protocol for Time Extensions", 
        "type": "selectbox", 
        "options": [
            "Option A: Standard. Extensions may be granted by the Tribunal upon a reasoned request showing good cause.",
            "Option B: Strict. Extensions granted only in 'exceptional circumstances'.",
            "Option C: Flexible. Short extensions (e.g., up to 3 days) may be agreed between parties without Tribunal intervention."
        ]
    },

    # VI. HEARING & TIMING
    {
        "id": "funding", 
        "question": "16. Third-Party Funding", 
        "type": "radio", 
        "options": [
            "Option A: None. No third-party funding is currently in place.",
            "Option B: Exists. Third-party funding is in place. (Please disclose the identity of the funder immediately)."
        ]
    },
    {
        "id": "deadline_timezone", 
        "question": "17. Definition of 'Deadline' (Timezone)", 
        "type": "radio", 
        "options": [
            "Option A: Time of the Seat. Time of the Seat of Arbitration (e.g., 17:00 London time).",
            "Option B: Time of Presiding Arbitrator. Time of the Presiding Arbitrator's location.",
            "Option C: Time of Filing Party. Time of the filing party's location."
        ]
    },
    {
        "id": "physical_venue_preference", 
        "question": "18. Physical Hearing Venue Preference", 
        "type": "radio", 
        "options": [
            "Option A: At Seat. The hearings shall take place physically at the Seat of Arbitration.",
            "Option B: Neutral Venue. The hearings shall take place at a different neutral venue (e.g., IDRC London, Maxwell Chambers Singapore)."
        ]
    },
    {
        "id": "interpretation", 
        "question": "19. Interpretation and Translation", 
        "type": "radio", 
        "options": [
            "Option A: English Only. The proceedings will be conducted entirely in English; no interpretation is anticipated.",
            "Option B: Interpretation Required. One or more witnesses will testify in a language other than English; simultaneous interpretation will be required."
        ]
    },

    # VII. SUBMISSION LIMITS
    {
        "id": "limits_submission", 
        "question": "20. Page Limits for Written Submissions", 
        "type": "radio", 
        "options": [
            "Option A: None. No specific page limits; parties will use reasonable discretion.",
            "Option B: Strict. Strict page limits shall apply (e.g., 50 pages for first round, 25 pages for second round).",
            "Option C: Legal Only. Limits shall apply to the legal argument sections only, excluding witness statements and expert reports."
        ]
    },
    {
        "id": "ai_guidelines", 
        "question": "21. Artificial Intelligence Guidelines", 
        "type": "radio", 
        "options": [
            "Option A: Adopt Guidelines. The Tribunal should include the CIArb Guidelines on the Use of AI as a guiding text.",
            "Option B: None. No specific guidelines on AI are necessary at this stage."
        ]
    },

    # VIII. COMPLEXITY
    {
        "id": "consolidation", 
        "question": "22. Consolidation and Concurrent Conduct", 
        "type": "radio", 
        "options": [
            "Option A: Stand-Alone. This arbitration stands alone; no consolidation or concurrent conduct is anticipated.",
            "Option B: Consolidation. There are related arbitrations. The parties request Consolidation into a single legal proceeding.",
            "Option C: Concurrent Conduct. There are related arbitrations. The parties request Concurrent Conduct (separate awards, but synchronized timetables)."
        ]
    },

    # IX. HEARING MANAGEMENT
    {
        "id": "chess_clock", 
        "question": "23. Time Allocation (Chess Clock)", 
        "type": "radio", 
        "options": [
            "Option A: Chess Clock. Fixed time allocation (e.g., 50/50 split of total hearing time) which the parties must manage themselves.",
            "Option B: Tribunal Discretion. The Tribunal controls the length of examination for each witness on a case-by-case basis."
        ]
    },
    {
        "id": "post_hearing", 
        "question": "24. Post-Hearing Briefs", 
        "type": "radio", 
        "options": [
            "Option A: Oral Closings Only. Oral closing arguments only; no post-hearing briefs.",
            "Option B: Written Briefs. Post-hearing written briefs are required (replacing or supplementing oral closings).",
            "Option C: Costs Only. Costs Submissions only (no merits briefing) after the hearing."
        ]
    },

    # X. DATA & EXPERTS
    {
        "id": "time_shred_docs", 
        "question": "25. Destruction of Documents (GDPR)", 
        "type": "radio", 
        "options": [
            "Option A: Immediate. Hard copies should be destroyed/shredded immediately upon issuance of the Final Award.",
            "Option B: Retain. Hard copies should be retained for the applicable limitation period for challenges (e.g., 28 days) and then destroyed."
        ]
    },
    {
        "id": "expert_meeting", 
        "question": "26. Meetings of Experts", 
        "type": "radio", 
        "options": [
            "Option A: Joint Report. Expert counterparts must meet and produce a Joint Report identifying areas of agreement and disagreement before the hearing.",
            "Option B: Independent. Experts shall submit independent reports only; no pre-hearing meetings or joint reports are required."
        ]
    },
    {
        "id": "expert_hot_tub", 
        "question": "27. Mode of Expert Questioning", 
        "type": "radio", 
        "options": [
            "Option A: Sequential. Experts will be cross-examined individually, one after the other.",
            "Option B: Hot-Tubbing. Witness Conferencing. Experts from both sides dealing with the same discipline shall give evidence concurrently."
        ]
    },
    {
        "id": "expert_reply", 
        "question": "28. Reply Expert Reports", 
        "type": "radio", 
        "options": [
            "Option A: Simultaneous. Simultaneous exchange of initial reports, followed by simultaneous exchange of Reply reports.",
            "Option B: Sequential. Sequential exchange (Claimant first, then Respondent), with no Reply reports permitted unless new factual evidence is introduced."
        ]
    },

    # XI. AWARD
    {
        "id": "sign_award", 
        "question": "29. Electronic Signatures on Award", 
        "type": "radio", 
        "options": [
            "Option A: Electronic. The Parties agree that the Tribunal may sign the Award electronically.",
            "Option B: Wet Ink. The Parties require the Award to be signed in 'wet ink' (hard copy) for enforcement purposes in specific jurisdictions."
        ]
    },
    {
        "id": "currency", 
        "question": "30. Currency of the Award", 
        "type": "radio", 
        "options": [
            "Option A: Contract Currency. The Award shall be expressed in the currency of the contract/transaction (e.g., USD).",
            "Option B: Cost Currency. The Award shall be expressed in the currency of the costs incurred (e.g., GBP for legal costs, USD for damages).",
            "Option C: Tribunal Discretion. Left to the Tribunal's discretion based on the applicable law."
        ]
    },
    {
        "id": "interest", 
        "question": "31. Interest Calculation", 
        "type": "radio", 
        "options": [
            "Option A: Applicable Law. The Tribunal shall apply interest rates and methods (simple/compound) prescribed by the applicable substantive law.",
            "Option B: Simple Interest. The Parties agree that any interest awarded shall be simple interest only.",
            "Option C: Compound Interest. The Parties agree that any interest awarded shall be compound interest."
        ]
    },
    {
        "id": "last_submission", 
        "question": "32. Definition of 'Last Submission' (3-Month Deadline)", 
        "type": "radio", 
        "options": [
            "Option A: Merits Brief. The 'Last Submission' triggering the 3-month reporting period is the final Post-Hearing Brief on the merits. (Cost submissions are handled separately/later).",
            "Option B: Final Filing. The 'Last Submission' is the very last filing, including Submissions on Costs."
        ]
    },

    # XII. LOGISTICS & PRIVILEGE
    {
        "id": "transcription", 
        "question": "33. Transcription Services", 
        "type": "selectbox", 
        "options": [
            "Option A: Live / Real-time. Live / Real-time transcription is required (Parties see the text appear instantly on screens).",
            "Option B: Daily Turnaround. Transcripts provided at the end of each hearing day.",
            "Option C: Standard Turnaround. Transcripts provided 1-2 weeks after the hearing.",
            "Option D: None. No transcription; the Tribunal’s recording/notes shall suffice."
        ]
    },
    {
        "id": "demonstratives", 
        "question": "34. Demonstrative Exhibits", 
        "type": "radio", 
        "options": [
            "Option A: 24 Hours. Demonstratives must be exchanged in hard copy/email 24 hours before use.",
            "Option B: Immediate. Demonstratives must be exchanged immediately prior to the start of the examination of the relevant witness.",
            "Option C: No specific rule. Demonstratives may be used freely provided they contain no new evidence."
        ]
    },
    {
        "id": "privilege_std", 
        "question": "35. Standard of Legal Privilege", 
        "type": "radio", 
        "options": [
            "Option A: Seat Rules. The Tribunal shall apply the rules of privilege of the Seat of Arbitration (e.g., English Law).",
            "Option B: Closest Connection. The Tribunal shall apply the rules of privilege of the party claiming the privilege (Most Favored Nation approach).",
            "Option C: Strictest. The Tribunal shall apply the strictest applicable privilege rule among the parties' jurisdictions."
        ]
    },
    {
        "id": "privilege_logs", 
        "question": "36. Privilege Logs", 
        "type": "radio", 
        "options": [
            "Option A: Required. Parties withholding documents on grounds of privilege must produce a detailed privilege log (Index).",
            "Option B: Not Required. Privilege logs are not required unless the Tribunal specifically orders one following a dispute."
        ]
    },

    # XIII. CONTACT INFO (Last)
    {
        "id": "reps_info", 
        "question": "37. Authorised Representatives (Contact Details)", 
        "type": "text_area", 
        "options": ["Enter Name, Firm, and Email..."]
    }
]

# --- LOAD & EDIT LOGIC ---
current_structure = load_structure()
if not current_structure:
    current_structure = DEFAULT_QUESTIONS

with st.form("editor_form"):
    updated_structure = []
    st.markdown("### Questions Configuration")
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 2, 1])
            
            new_q_text = c1.text_input(f"Question #{i+1}", value=q['question'], key=f"q_{i}")
            
            # Type handling
            type_map = {"radio": "List", "selectbox": "Dropdown", "text_area": "Text Input"}
            rev_map = {"List": "radio", "Dropdown": "selectbox", "Text Input": "text_area"}
            curr_type = type_map.get(q['type'], "List")
            new_type_disp = c2.selectbox("Type", ["List", "Dropdown", "Text Input"], index=["List", "Dropdown", "Text Input"].index(curr_type), key=f"t_{i}")
            new_type = rev_map[new_type_disp]
            
            is_included = c3.checkbox("Include", value=True, key=f"inc_{i}")
            
            if new_type != "text_area":
                options_str = ", ".join(q.get('options', []))
                # Taller text area for long descriptions
                new_options_str = st.text_area(f"Options", value=options_str, key=f"o_{i}", height=100)
                new_options = [opt.strip() for opt in new_options_str.split(",")]
            else:
                new_options = ["Text Input"]
            
            if is_included:
                updated_structure.append({
                    "id": q['id'], "question": new_q_text, "type": new_type, "options": new_options
                })
    
    if st.form_submit_button("💾 Publish to Parties", type="primary"):
        save_structure(updated_structure)
        st.success(f"Published {len(updated_structure)} questions.")
