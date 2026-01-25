import streamlit as st
from db import load_structure, save_structure, set_release_status, get_release_status
import time

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

role = st.session_state.get('user_role')
if role not in ['lcia', 'arbitrator']:
    st.error("Access Denied")
    st.stop()

# --- DETERMINE PHASE ---
if role == 'lcia':
    CURRENT_PHASE = "phase1"
    PAGE_TITLE = "Phase 1: Pre-Tribunal Appointment Questionnaire"
else:
    CURRENT_PHASE = "phase2"
    PAGE_TITLE = "Phase 2: Pre-Hearing Questionnaire"

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.page_link("main.py", label="Home")
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 1 Qs")
    else:
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
        st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title(f"✏️ {PAGE_TITLE}")

# --- RELEASE STATUS ---
status = get_release_status()
is_released = status.get(CURRENT_PHASE, False)

# --- MASTER LIST: PHASE 1 (LCIA) ---
DEFAULTS_PHASE_1 = [
    {
        "id": "p1_duration", 
        "question": "1. Target Procedural Timetable (Objective for Final Award)", 
        "type": "radio", 
        "options": [
            "**Accelerated:** 6-9 months (requires strict deadlines and limited document production).", 
            "**Standard efficiency:** 12-15 months.", 
            "**Extended / Complex:** 18-24+ months (anticipating extensive evidence or multiple phases).",
            "**Statutory / contractual Limit:** Date required under contract."
        ]
    },
    {
        "id": "p1_qual", 
        "question": "2. Arbitrator Availability (Mandatory Qualification)", 
        "type": "radio", 
        "options": [
            "**Yes:** The timeline selected above is a mandatory qualification for the appointment of the arbitrator.", 
            "**No:** The timeline is an objective only."
        ]
    },
    {
        "id": "p1_early", 
        "question": "3. Application for Early Determination (Summary Dismissal)", 
        "type": "radio", 
        "options": [
            "**Yes:** We anticipate filing an application for early determination of any claims or defenses.", 
            "**No:** We do not anticipate filing an application.", 
            "**Possible:** Rights reserved."
        ]
    },
    {
        "id": "p1_days", 
        "question": "4. Estimated Hearing Days (Merits)", 
        "type": "radio", 
        "options": [
            "**None:** Documents-only arbitration (no oral hearing).", 
            "**Short:** 1-3 days.", 
            "**Medium:** 1 week (4-5 days).", 
            "**Long:** 2 weeks or more (10+ days)."
        ]
    },
    {
        "id": "p1_block", 
        "question": "5. Hearing Block Reservation", 
        "type": "radio", 
        "options": [
            "**Strictly consecutive:** The hearing must be concluded in one continuous block.", 
            "**Flexible / Split:** We accept split weeks to accommodate arbitrator availability."
        ]
    },
    {
        "id": "p1_dates", 
        "question": "6. Blackout Dates / Preferred Windows (Next 18 Months)", 
        "type": "text_area", 
        "options": ["Enter specific dates or months here..."]
    },
    {
        "id": "p1_format", 
        "question": "7. Default Format for Administrative / Procedural Conferences", 
        "type": "radio", 
        "options": ["Audio only", "Video Conference", "In-Person"]
    },
    {
        "id": "p1_hearing", 
        "question": "8. Preference for Main Evidentiary Hearing", 
        "type": "radio", 
        "options": [
            "**Fully Virtual:** All participants attend remotely.", 
            "**Hybrid (Split Location):** Tribunal and counsel in one physical room and witness joins remotely.", 
            "**Fully In-Person:** Standard physical hearing."
        ]
    },
    {
        "id": "p1_data", 
        "question": "9. Data Protocol (E-Hearing Platform)", 
        "type": "radio", 
        "options": [
            "**Yes:** We prefer a dedicated third-party platform.", 
            "**No:** Email and standard file transfer service (Dropbox / ShareFile) is sufficient."
        ]
    }
]

# --- MASTER LIST: PHASE 2 (ARBITRATOR) ---
DEFAULTS_PHASE_2 = [
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
    
    # II. EVIDENCE
    {
        "id": "doc_prod", 
        "question": "3. Applicable Guidelines (Evidence)", 
        "type": "selectbox", 
        "options": [
            "**Option A: IBA Rules (Binding).** The IBA Rules on the Taking of Evidence (2020) shall apply as binding rules.",
            "**Option B: IBA Rules (Guidelines).** The Tribunal shall be guided by the IBA Rules (2020) but they shall not be binding.",
            "**Option C: No specific guidelines.** The Tribunal shall apply the general evidentiary powers under the LCIA Rules.",
            "**Option D: Other.** (e.g., The Prague Rules, CIArb Guidelines). Please specify in the comments."
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

    # IV. COSTS
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
            "**Option C: Flexible.** Short extensions (e.g., up to 3 days) may be agreed between parties without Tribunal intervention, provided the hearing date is not jeopardized."
        ]
    },

    # VI. PARTY DETAILS
    {
        "id": "reps_info", 
        "question": "16. Authorised Representatives (LCIA Art. 18)", 
        "type": "text_area", 
        "options": ["Enter Lead Counsel Name, Email, Firm..."]
    },
    {
        "id": "funding", 
        "question": "17. Third-Party Funding", 
        "type": "radio", 
        "options": [
            "**Option A: None.** No third-party funding is currently in place.",
            "**Option B: Exists.** Third-party funding is in place. (Please disclose the identity of the funder immediately to comply with conflict check requirements)."
        ]
    },

    # VII. HEARING LOGISTICS
    {
        "id": "deadline_timezone", 
        "question": "18. Definition of 'Deadline' (Timezone)", 
        "type": "radio", 
        "options": [
            "**Option A: Time of the Seat.** Time of the Seat of Arbitration (e.g., 17:00 London time).",
            "**Option B: Time of Presiding Arbitrator.** Time of the Presiding Arbitrator's location.",
            "**Option C: Time of Filing Party.** Time of the filing party's location."
        ]
    },
    {
        "id": "physical_venue_preference", 
        "question": "19. Physical Hearing Venue", 
        "type": "radio", 
        "options": [
            "**Option A: At Seat.** The hearings shall take place physically at the Seat of Arbitration.",
            "**Option B: Neutral Venue.** The hearings shall take place at a different neutral venue (e.g., IDRC London, Maxwell Chambers Singapore)."
        ]
    },
    {
        "id": "interpretation", 
        "question": "20. Interpretation and Translation", 
        "type": "radio", 
        "options": [
            "**Option A: English Only.** The proceedings will be conducted entirely in English; no interpretation is anticipated.",
            "**Option B: Interpretation Required.** One or more witnesses will testify in a language other than English; simultaneous interpretation will be required."
        ]
    },

    # VIII. LIMITS
    {
        "id": "limits_submission", 
        "question": "21. Page Limits for Written Submissions", 
        "type": "radio", 
        "options": [
            "**Option A: None.** No specific page limits; parties will use reasonable discretion.",
            "**Option B: Strict.** Strict page limits shall apply (e.g., 50 pages for first round, 25 pages for second round).",
            "**Option C: Legal Only.** Limits shall apply to the legal argument sections only, excluding witness statements and expert reports."
        ]
    },
    {
        "id": "ai_guidelines", 
        "question": "22. Artificial Intelligence Guidelines", 
        "type": "radio", 
        "options": [
            "**Option A: Adopt Guidelines.** The Tribunal should include the CIArb Guidelines on the Use of AI as a guiding text for the Parties' use of technology.",
            "**Option B: None.** No specific guidelines on AI are necessary at this stage."
        ]
    },

    # IX. CONSOLIDATION
    {
        "id": "consolidation", 
        "question": "23. Consolidation and Concurrent Conduct", 
        "type": "radio", 
        "options": [
            "**Option A: Stand-Alone.** This arbitration stands alone; no consolidation or concurrent conduct is anticipated.",
            "**Option B: Consolidation.** There are related arbitrations between the parties. The parties request Consolidation into a single legal proceeding.",
            "**Option C: Concurrent Conduct.** There are related arbitrations. The parties request Concurrent Conduct (separate awards, but synchronized timetables and hearings) pursuant to Article 22.7(iii)."
        ]
    },

    # X. HEARING MANAGEMENT
    {
        "id": "chess_clock", 
        "question": "24. Time Allocation at Hearing", 
        "type": "radio", 
        "options": [
            "**Option A: Chess Clock.** Fixed time allocation (e.g., 50/50 split of total hearing time) which the parties must manage themselves.",
            "**Option B: Tribunal Discretion.** The Tribunal controls the length of examination for each witness on a case-by-case basis."
        ]
    },
    {
        "id": "post_hearing", 
        "question": "25. Post-Hearing Briefs", 
        "type": "radio", 
        "options": [
            "**Option A: Oral Closings Only.** Oral closing arguments only; no post-hearing briefs.",
            "**Option B: Written Briefs.** Post-hearing written briefs are required (replacing or supplementing oral closings).",
            "**Option C: Costs Only.** Costs Submissions only (no merits briefing) after the hearing."
        ]
    },

    # XI. DATA RETENTION
    {
        "id": "time_shred_docs", 
        "question": "26. Destruction of Documents", 
        "type": "radio", 
        "options": [
            "**Option A: Immediate.** Hard copies should be destroyed/shredded immediately upon issuance of the Final Award.",
            "**Option B: Retain.** Hard copies should be retained for the applicable limitation period for challenges (e.g., 28 days under LCIA Art 27) and then destroyed."
        ]
    },

    # XII. EXPERTS
    {
        "id": "expert_meeting", 
        "question": "27. Meetings of Experts", 
        "type": "radio", 
        "options": [
            "**Option A: Joint Report.** Expert counterparts must meet and produce a Joint Report identifying areas of agreement and disagreement before the hearing.",
            "**Option B: Independent.** Experts shall submit independent reports only; no pre-hearing meetings or joint reports are required."
        ]
    },
    {
        "id": "expert_hot_tub", 
        "question": "28. Mode of Expert Questioning ('Hot-Tubbing')", 
        "type": "radio", 
        "options": [
            "**Option A: Sequential.** Sequential Examination. Experts will be cross-examined individually, one after the other.",
            "**Option B: Hot-Tubbing.** Witness Conferencing. Experts from both sides dealing with the same discipline shall give evidence concurrently and may debate issues directly with each other and the Tribunal."
        ]
    },
    {
        "id": "expert_reply", 
        "question": "29. Reply Expert Reports", 
        "type": "radio", 
        "options": [
            "**Option A: Simultaneous.** Simultaneous exchange of initial reports, followed by simultaneous exchange of Reply reports.",
            "**Option B: Sequential.** Sequential exchange (Claimant first, then Respondent), with no Reply reports permitted unless new factual evidence is introduced."
        ]
    },

    # XIII. AWARD
    {
        "id": "sign_award", 
        "question": "30. Electronic Signatures on the Award", 
        "type": "radio", 
        "options": [
            "**Option A: Electronic.** The Parties agree that the Tribunal may sign the Award electronically.",
            "**Option B: Wet Ink.** The Parties require the Award to be signed in 'wet ink' (hard copy) for enforcement purposes in specific jurisdictions."
        ]
    },
    {
        "id": "currency", 
        "question": "31. Currency of the Award", 
        "type": "radio", 
        "options": [
            "**Option A: Contract Currency.** The Award shall be expressed in the currency of the contract/transaction (e.g., USD).",
            "**Option B: Cost Currency.** The Award shall be expressed in the currency of the costs incurred (e.g., GBP for legal costs, USD for damages).",
            "**Option C: Tribunal Discretion.** Left to the Tribunal's discretion based on the applicable law."
        ]
    },
    {
        "id": "interest", 
        "question": "32. Interest Calculation", 
        "type": "radio", 
        "options": [
            "**Option A: Applicable Law.** The Tribunal shall apply interest rates and methods (simple/compound) prescribed by the applicable substantive law.",
            "**Option B: Simple Interest.** The Parties agree that any interest awarded shall be simple interest only.",
            "**Option C: Compound Interest.** The Parties agree that any interest awarded shall be compound interest."
        ]
    },
    {
        "id": "last_submission", 
        "question": "33. Definition of 'Last Submission'", 
        "type": "radio", 
        "options": [
            "**Option A: Merits Brief.** The 'Last Submission' triggering the 3-month reporting period is the final Post-Hearing Brief on the merits. (Cost submissions are handled separately/later).",
            "**Option B: Final Filing.** The 'Last Submission' is the very last filing, including Submissions on Costs."
        ]
    },

    # XIV. TRANSCRIPTS
    {
        "id": "transcription", 
        "question": "34. Transcription Services", 
        "type": "selectbox", 
        "options": [
            "**Option A: Live / Real-time.** Live / Real-time transcription is required (Parties see the text appear instantly on screens).",
            "**Option B: Daily Turnaround.** Transcripts provided at the end of each hearing day.",
            "**Option C: Standard Turnaround.** Transcripts provided 1-2 weeks after the hearing.",
            "**Option D: None.** No transcription; the Tribunal’s recording/notes shall suffice."
        ]
    },
    {
        "id": "demonstratives", 
        "question": "35. Demonstrative Exhibits", 
        "type": "radio", 
        "options": [
            "**Option A: 24 Hours.** Demonstratives must be exchanged in hard copy/email 24 hours before use.",
            "**Option B: Immediate.** Demonstratives must be exchanged immediately prior to the start of the examination of the relevant witness.",
            "**Option C: No specific rule.** Demonstratives may be used freely provided they contain no new evidence."
        ]
    },

    # XV. PRIVILEGE
    {
        "id": "privilege_std", 
        "question": "36. Standard of Legal Privilege", 
        "type": "radio", 
        "options": [
            "**Option A: Seat Rules.** The Tribunal shall apply the rules of privilege of the Seat of Arbitration (e.g., English Law).",
            "**Option B: Closest Connection.** The Tribunal shall apply the rules of privilege of the party claiming the privilege (Most Favored Nation approach).",
            "**Option C: Strictest.** The Tribunal shall apply the strictest applicable privilege rule among the parties' jurisdictions."
        ]
    },
    {
        "id": "privilege_logs", 
        "question": "37. Privilege Logs", 
        "type": "radio", 
        "options": [
            "**Option A: Required.** Parties withholding documents on grounds of privilege must produce a detailed privilege log (Index) describing the document and the basis for privilege.",
            "**Option B: Not Required.** Privilege logs are not required unless the Tribunal specifically orders one following a dispute."
        ]
    },

    # XVI. CONFIDENTIALITY
    {
        "id": "publication", 
        "question": "38. Publication of the Award (Sourcebook Topic 46)", 
        "type": "radio", 
        "options": [
            "**Option A (Default LCIA):** Strict Confidentiality. The award shall remain confidential and shall not be published.",
            "**Option B (Redacted Publication):** The party consents to the publication of the award in a redacted format to protect names and sensitive commercial data. Redactions shall be agreed upon by the parties.",
            "**Option C (Sanitized Summary):** The party consents to the publication of a summary of the legal reasoning of the award only, with no identifying facts."
        ]
    },

    # XVII. DISABILITY
    {
        "id": "disability", 
        "question": "39. Accommodations for Participants", 
        "type": "radio", 
        "options": [
            "**Option A (General Clause):** The PO1 shall include a standard liberty to apply, stating: \"At any point, either party may advise the Tribunal of a person who requires reasonable accommodation to facilitate their full participation.\"",
            "**Option B (Specific Needs Now):** A participant already requires specific accommodations (e.g., document formatting for screen readers, specific break schedules, wheelchair access for physical venues).",
            "**Option C:** No specific clause is required in PO1; parties will raise ad hoc if necessary."
        ]
    },

    # XVIII. SUSTAINABILITY
    {
        "id": "sustainability", 
        "question": "40. Green Protocols", 
        "type": "radio", 
        "options": [
            "**Option A (Campaign for Greener Arbitrations):** The Tribunal and parties shall conduct the arbitration in accordance with the Green Protocols of the Campaign for Greener Arbitrations (e.g., avoiding unnecessary travel, electronic-only bundles).",
            "**Option B (Tribunal Discretion):** The Tribunal shall consider sustainability/environmental impact when making procedural rulings but no formal protocol is adopted.",
            "**Option C:** No specific sustainability measures beyond the LCIA's default electronic filing rules."
        ]
    },

    # XIX. ETHICS
    {
        "id": "ethics", 
        "question": "41. Guidelines on Party Representation", 
        "type": "radio", 
        "options": [
            "**Option A (LCIA Only):** Conduct shall be governed exclusively by the mandatory Annex to the LCIA Rules 2020.",
            "**Option B (LCIA + IBA):** The Tribunal shall also be guided by the IBA Guidelines on Party Representation in International Arbitration (2013). In the event of conflict, the LCIA Rules/Annex shall prevail."
        ]
    },

    # XX. MEDIATION
    {
        "id": "mediation", 
        "question": "42. Mediation Window / Settlement Facilitation", 
        "type": "radio", 
        "options": [
            "**Option A (Standard):** The arbitration proceeds on a linear timetable. Parties may settle at any time, but no specific \"pause\" is built into the schedule.",
            "**Option B (Mediation Window):** The Procedural Timetable shall include a specific stay of proceedings (e.g., 30 days) after the first round of written submissions to allow parties to attempt mediation.",
            "**Option C (Tribunal Facilitation):** The parties authorize the Tribunal to facilitate settlement discussions (e.g., giving a preliminary non-binding view), understanding this may limit their ability to challenge the Tribunal later for lack of impartiality."
        ]
    }
]

# --- LOAD CORRECT DATA ---
current_structure = load_structure(phase=CURRENT_PHASE)
if not current_structure:
    current_structure = DEFAULTS_PHASE_1 if role == 'lcia' else DEFAULTS_PHASE_2

# --- ADD CUSTOM QUESTION ---
if st.button("➕ Add New Question", type="primary"):
    new_id = f"custom_{CURRENT_PHASE}_{int(time.time())}"
    # Next number logic
    try:
        last_q_text = current_structure[-1]['question']
        last_num = int(last_q_text.split(".")[0])
        next_num = last_num + 1
    except:
        next_num = len(current_structure) + 1
        
    new_q = {"id": new_id, "question": f"{next_num}. New Question", "type": "radio", "options": ["**Option A:** Yes", "**Option B:** No"]}
    current_structure.append(new_q)
    save_structure(current_structure, phase=CURRENT_PHASE)
    st.rerun()

# --- EDITOR FORM ---
with st.form("editor_form"):
    updated_structure = []
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            new_q_text = c1.text_input(f"Q{i+1}", value=q['question'], key=f"q_{i}")
            
            type_map = {"radio": "List (Radio)", "selectbox": "Dropdown", "text_area": "Text Input"}
            rev_map = {"List (Radio)": "radio", "Dropdown": "selectbox", "Text Input": "text_area"}
            curr_type = type_map.get(q['type'], "List (Radio)")
            new_type_disp = c2.selectbox("Type", list(type_map.values()), index=list(type_map.values()).index(curr_type), key=f"t_{i}")
            new_type = rev_map[new_type_disp]
            
            new_options = []
            if new_type != "text_area":
                st.write("**Options:**")
                existing_opts = q.get('options', [])
                for idx, o in enumerate(existing_opts):
                    val = st.text_input(f"Option {idx+1}", value=o, key=f"o_{i}_{idx}")
                    new_options.append(val)
                if len(new_options) < 2:
                    for j in range(len(new_options), 2):
                        val = st.text_input(f"Option {j+1}", value=f"Option {j+1}", key=f"o_{i}_{j}")
                        new_options.append(val)
            else:
                new_options = ["Text Input"]
            
            updated_structure.append({
                "id": q['id'], "question": new_q_text, "type": new_type, "options": new_options
            })
    
    c_save, c_release = st.columns([1, 1])
    with c_save:
        if st.form_submit_button("💾 Save Draft"):
            save_structure(updated_structure, phase=CURRENT_PHASE)
            st.success("Draft saved.")
            
    with c_release:
        btn_label = "🚀 Release to Parties" if not is_released else "🚀 Update Released Version"
        if st.form_submit_button(btn_label, type="primary"):
            save_structure(updated_structure, phase=CURRENT_PHASE)
            set_release_status(CURRENT_PHASE, True)
            st.success(f"✅ {PAGE_TITLE} is now LIVE for the parties!")
            time.sleep(1)
            st.rerun()

if is_released:
    st.success("🟢 Status: RELEASED to Parties")
else:
    st.warning("🔴 Status: HIDDEN from Parties (Draft Mode)")
