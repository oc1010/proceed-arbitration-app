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

# --- MASTER QUESTION BANK (Detailed) ---
DEFAULT_QUESTIONS = [
    # I. WRITTEN SUBMISSIONS
    {
        "id": "style", 
        "question": "1. Style of Written Submissions", 
        "type": "radio", 
        "options": [
            "Memorial Style. Simultaneous submission of factual allegations, legal arguments, witness statements, and expert reports. (Front-loaded costs; potentially faster resolution).",
            "Pleading Style. Submission of factual allegations and legal arguments first. Witness statements and expert reports are exchanged only after document production. (Spreads costs; traditional English style)."
        ]
    },
    {
        "id": "bifurcation", 
        "question": "2. Bifurcation of Proceedings", 
        "type": "radio", 
        "options": [
            "Single Phase. The Tribunal should hear all issues (Jurisdiction, Liability, and Quantum) together in a single phase.",
            "Bifurcation Requested. The Parties request bifurcation (e.g., Liability determined first, Quantum later) pursuant to LCIA Article 22.1(vii)."
        ]
    },
    
    # II. DOCUMENT PRODUCTION & EVIDENCE
    {
        "id": "doc_prod", 
        "question": "3. Applicable Guidelines (Evidence)", 
        "type": "selectbox", 
        "options": [
            "IBA Rules (Binding). The IBA Rules on the Taking of Evidence (2020) shall apply as binding rules.",
            "IBA Rules (Guidelines). The Tribunal shall be guided by the IBA Rules (2020) but they shall not be binding.",
            "None. No specific guidelines; the Tribunal shall apply general evidentiary powers.",
            "Other (e.g. Prague Rules). Please specify."
        ]
    },
    {
        "id": "limits", 
        "question": "4. Limitations on Document Requests", 
        "type": "radio", 
        "options": [
            "Standard (IBA). No specific numerical limit, subject to relevance and materiality.",
            "Capped. Requests limited to a specific number (e.g., 20 requests per party) to control costs.",
            "None. No document production phase (reliance on documents attached to pleadings only)."
        ]
    },
    {
        "id": "witness_exam", 
        "question": "5. Witness Examination", 
        "type": "radio", 
        "options": [
            "Written Evidence Stands. Witness statements stand as evidence-in-chief. Direct examination limited/not permitted.",
            "Full Direct Exam. Witness statements are summaries; full direct examination is required at the hearing.",
            "No Hearing. Cross-examination waived; Tribunal decides based on written statements only."
        ]
    },

    # III. ELECTRONIC PROTOCOLS
    {
        "id": "platform", 
        "question": "6. Case Management Platform", 
        "type": "radio", 
        "options": [
            "PROCEED Platform. Parties agree to use this specific platform for filings and tracking.",
            "Email Only. Individual case management via email/PDF filings only."
        ]
    },
    {
        "id": "bundling", 
        "question": "7. Electronic Bundling", 
        "type": "radio", 
        "options": [
            "Joint Bundle. Parties collaborate on a single indexed hearing bundle.",
            "Individual Bundles. Each party prepares its own separate bundle."
        ]
    },
    {
        "id": "gdpr", 
        "question": "8. Data Protection (GDPR) & Cybersecurity", 
        "type": "radio", 
        "options": [
            "Standard. Standard security measures (encrypted email/platform) are sufficient.",
            "Enhanced. Dispute involves highly sensitive data requiring specific protocols under LCIA Art 30A."
        ]
    },

    # IV. COSTS & FUNDING
    {
        "id": "cost_allocation", 
        "question": "9. Cost Allocation Methodology", 
        "type": "radio", 
        "options": [
            "Costs follow the event ('Loser pays').",
            "Apportionment based on relative success of issues.",
            "Parties bear own costs; administrative costs split 50/50."
        ]
    },
    {
        "id": "counsel_fees", 
        "question": "10. Counsel Fees (Recoverability)", 
        "type": "radio", 
        "options": [
            "Market Rates. Recoverable costs must be 'reasonable'.",
            "Capped Rates. Recoverable hourly rates capped at a pre-agreed amount."
        ]
    },
    {
        "id": "internal_costs", 
        "question": "11. Internal Management Costs", 
        "type": "radio", 
        "options": [
            "Recoverable. Reasonable internal management time/costs are recoverable.",
            "Not recoverable."
        ]
    },
    {
        "id": "deposits", 
        "question": "12. Administrative Deposits", 
        "type": "radio", 
        "options": [
            "Split 50/50 between Claimant and Respondent.",
            "Claimant pays 100% of the initial deposit."
        ]
    },

    # V. TRIBUNAL ASSISTANCE
    {
        "id": "secretary", 
        "question": "13. Tribunal Secretary", 
        "type": "radio", 
        "options": [
            "Consent. The Parties consent to the appointment of a Tribunal Secretary.",
            "Object. The Parties object to the appointment of a Tribunal Secretary."
        ]
    },
    {
        "id": "sec_fees", 
        "question": "14. Tribunal Secretary Fees", 
        "type": "radio", 
        "options": [
            "£75 - £175 / hr (Standard LCIA).",
            "£100 - £250 / hr (Draft PO1 Template)."
        ]
    },
    {
        "id": "extensions", 
        "question": "15. Protocol for Time Extensions", 
        "type": "selectbox", 
        "options": [
            "Standard. Granted by Tribunal upon reasoned request showing good cause.",
            "Strict. Granted only in 'exceptional circumstances'.",
            "Flexible. Short extensions (e.g. 3 days) agreed between parties without Tribunal intervention."
        ]
    },

    # VI. HEARING & TIMING
    {
        "id": "funding", 
        "question": "16. Third-Party Funding", 
        "type": "radio", 
        "options": [
            "None. No third-party funding is currently in place.",
            "Exists. Third-party funding is in place (Disclose identity immediately)."
        ]
    },
    {
        "id": "deadline_timezone", 
        "question": "17. Definition of 'Deadline' (Timezone)", 
        "type": "radio", 
        "options": [
            "Time of the Seat of Arbitration (e.g., 17:00 London time).",
            "Time of the Presiding Arbitrator's location.",
            "Time of the filing party's location."
        ]
    },
    {
        "id": "physical_venue_preference", 
        "question": "18. Physical Hearing Venue Preference", 
        "type": "radio", 
        "options": [
            "At Seat. Hearings physically at the Seat of Arbitration.",
            "Neutral Venue. Hearings at a different neutral venue (e.g. IDRC London, Maxwell Chambers)."
        ]
    },
    {
        "id": "interpretation", 
        "question": "19. Interpretation and Translation", 
        "type": "radio", 
        "options": [
            "English Only. Proceedings entirely in English; no interpretation.",
            "Interpretation Required. Witnesses will testify in other languages; simultaneous interpretation needed."
        ]
    },

    # VII. SUBMISSION LIMITS
    {
        "id": "limits_submission", 
        "question": "20. Page Limits for Written Submissions", 
        "type": "radio", 
        "options": [
            "None. No specific page limits; reasonable discretion.",
            "Strict. Strict limits apply (e.g., 50 pages first round, 25 pages second).",
            "Legal Only. Limits apply to legal argument sections only (excluding witness/expert)."
        ]
    },
    {
        "id": "ai_guidelines", 
        "question": "21. Artificial Intelligence Guidelines", 
        "type": "radio", 
        "options": [
            "Adopt CIArb Guidelines on AI as a guiding text.",
            "No specific AI guidelines necessary."
        ]
    },

    # VIII. COMPLEXITY
    {
        "id": "consolidation", 
        "question": "22. Consolidation and Concurrent Conduct", 
        "type": "radio", 
        "options": [
            "Stand-Alone. No consolidation anticipated.",
            "Consolidation. Related arbitrations to be consolidated into single proceeding.",
            "Concurrent Conduct. Separate awards, but synchronized timetables."
        ]
    },

    # IX. HEARING MANAGEMENT
    {
        "id": "chess_clock", 
        "question": "23. Time Allocation (Chess Clock)", 
        "type": "radio", 
        "options": [
            "Chess Clock. Fixed time allocation (e.g., 50/50 split) managed by parties.",
            "Tribunal Discretion. Tribunal controls length of examination per witness."
        ]
    },
    {
        "id": "post_hearing", 
        "question": "24. Post-Hearing Briefs", 
        "type": "radio", 
        "options": [
            "Oral Closings Only. No post-hearing briefs.",
            "Written Briefs. Required (replacing or supplementing oral closings).",
            "Costs Only. Only submissions on costs after hearing."
        ]
    },

    # X. DATA & EXPERTS
    {
        "id": "time_shred_docs", 
        "question": "25. Destruction of Documents (GDPR)", 
        "type": "radio", 
        "options": [
            "Immediate. Shred immediately upon Final Award.",
            "Retain. Retain for limitation period (e.g. 28 days) then destroy."
        ]
    },
    {
        "id": "expert_meeting", 
        "question": "26. Meetings of Experts", 
        "type": "radio", 
        "options": [
            "Joint Report. Experts must meet and produce Joint Report before hearing.",
            "Independent. Experts submit independent reports only."
        ]
    },
    {
        "id": "expert_hot_tub", 
        "question": "27. Mode of Expert Questioning", 
        "type": "radio", 
        "options": [
            "Sequential. Cross-examined individually.",
            "Hot-Tubbing. Witness Conferencing (concurrent evidence)."
        ]
    },
    {
        "id": "expert_reply", 
        "question": "28. Reply Expert Reports", 
        "type": "radio", 
        "options": [
            "Simultaneous Exchange of Reply reports.",
            "Sequential Exchange. No reply reports unless new evidence."
        ]
    },

    # XI. AWARD
    {
        "id": "sign_award", 
        "question": "29. Electronic Signatures on Award", 
        "type": "radio", 
        "options": [
            "Electronic. Parties agree Tribunal may sign electronically.",
            "Wet Ink. Parties require hard copy signature."
        ]
    },
    {
        "id": "currency", 
        "question": "30. Currency of the Award", 
        "type": "radio", 
        "options": [
            "Contract Currency (e.g. USD).",
            "Cost Currency (e.g. GBP for legal costs).",
            "Tribunal Discretion."
        ]
    },
    {
        "id": "interest", 
        "question": "31. Interest Calculation", 
        "type": "radio", 
        "options": [
            "Applicable Law. Rates/methods prescribed by law.",
            "Simple Interest only.",
            "Compound Interest."
        ]
    },
    {
        "id": "last_submission", 
        "question": "32. Definition of 'Last Submission' (3-Month Deadline)", 
        "type": "radio", 
        "options": [
            "Merits Brief. Final brief on merits triggers countdown.",
            "Final Filing. Includes submissions on costs."
        ]
    },

    # XII. LOGISTICS & PRIVILEGE
    {
        "id": "transcription", 
        "question": "33. Transcription Services", 
        "type": "selectbox", 
        "options": [
            "Live / Real-time.",
            "Daily Turnaround.",
            "Standard Turnaround (1-2 weeks).",
            "None."
        ]
    },
    {
        "id": "demonstratives", 
        "question": "34. Demonstrative Exhibits", 
        "type": "radio", 
        "options": [
            "24 Hours. Must be exchanged 24h before use.",
            "Immediate. Exchanged immediately prior to use.",
            "No specific rule."
        ]
    },
    {
        "id": "privilege_std", 
        "question": "35. Standard of Legal Privilege", 
        "type": "radio", 
        "options": [
            "Seat Rules (e.g. English Law).",
            "Closest Connection (Party claiming privilege).",
            "Strictest Applicable Rule."
        ]
    },
    {
        "id": "privilege_logs", 
        "question": "36. Privilege Logs", 
        "type": "radio", 
        "options": [
            "Required. Detailed log must be produced.",
            "Not Required unless ordered."
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
