import streamlit as st
from datetime import datetime, timedelta, date
import random
from db import get_active_case_id, save_complex_data, db

st.set_page_config(page_title="Full Scale Demo Injector", page_icon="💉", layout="wide")

st.title("💉 Complex Arbitration Data Injector")
st.warning("⚠️ WARNING: This will OVERWRITE all case data with a completed, 18-month complex arbitration history.")

# --- AUTH CHECK ---
case_id = get_active_case_id()
if not case_id:
    st.error("No Active Case found. Please login first.")
    st.stop()

st.info(f"Targeting Case: **{case_id}**")

# --- 1. GENERATOR UTILITIES ---
def get_past_date(days_ago):
    return date.today() - timedelta(days=days_ago)

# --- 2. COST DATA GENERATOR (Mixed Spend + Sealed Offer) ---
def generate_costs():
    categories = ["Legal Fees (Partners)", "Legal Fees (Associates)", "Expert Witness Fees", "Administrative Costs", "Travel & Accommodation", "Translation Services", "Hearing Venue Costs"]
    phases = ["Phase 1: Initiation", "Phase 2: Written Submissions", "Phase 3: Doc Production", "Phase 4: Hearing"]
    
    c_log = []
    r_log = []
    
    # Generate 15 distinct costs for Claimant (~€1.8M total)
    for i in range(15):
        amt = random.randint(15000, 250000)
        c_log.append({
            "phase": random.choice(phases),
            "category": random.choice(categories),
            "date": str(get_past_date(random.randint(30, 500))),
            "amount": amt,
            "logged_by": "claimant",
            "desc": f"Inv #{random.randint(1000,9999)}: Services rendered regarding {random.choice(['witness prep', 'memorial drafting', 'site visit', 'expert report analysis'])}."
        })

    # Generate 15 distinct costs for Respondent (~€1.6M total)
    for i in range(15):
        amt = random.randint(12000, 220000)
        r_log.append({
            "phase": random.choice(phases),
            "category": random.choice(categories),
            "date": str(get_past_date(random.randint(30, 500))),
            "amount": amt,
            "logged_by": "respondent",
            "desc": f"Inv #{random.randint(1000,9999)}: {random.choice(['Quantum analysis', 'Delay expert review', 'Counsel fees Q3', 'Bundling vendor fees'])}."
        })
        
    # Tribunal Costs (Common)
    common_log = [
        {"phase": "Phase 1", "category": "Tribunal Advance", "date": str(get_past_date(520)), "amount": 60000, "logged_by": "lcia"},
        {"phase": "Phase 2", "category": "Tribunal Advance", "date": str(get_past_date(300)), "amount": 60000, "logged_by": "lcia"},
        {"phase": "Phase 4", "category": "Hearing Venue Deposit", "date": str(get_past_date(100)), "amount": 25000, "logged_by": "lcia"},
    ]
    
    # Sealed Offers (Critical for AI Logic: Reverse Cost Shifting)
    # Offer made 6 months ago for €4.5M. 
    # Logic: If Final Award < €4.5M, Respondent gets their post-offer costs paid by Claimant.
    offers = [
        {
            "offerer": "respondent",
            "amount": 4500000.0, 
            "date": str(get_past_date(180)), 
            "status": "Sealed"
        }
    ]

    return {"claimant_log": c_log, "respondent_log": r_log, "common_log": common_log, "payment_requests": [], "sealed_offers": offers}

# --- 3. DOCUMENT PRODUCTION GENERATOR (20 Requests, Mixed Outcomes) ---
def generate_doc_prod():
    # Scenario: Construction dispute (Delay & Disruption)
    
    # CLAIMANT REQUESTS (High Rejection Rate -> High Proportionality Score)
    c_reqs = []
    c_data = [
        ("Minutes of Board Meetings Jan-Jun 2022", "Proof of knowledge of delay.", "Denied", "Fishing expedition; no evidence meetings discussed delay."),
        ("Internal emails: CEO & Project Director", "Show intent to withhold payments.", "Allowed", "Relevant to 'bad faith' allegation."),
        ("Site Diary Logs (Daily) for 2022", "Establish weather baseline.", "Allowed", "Standard disclosure."),
        ("Whatsapp messages: Site Foreman", "Informal instructions given.", "Denied", "Overly burdensome and privacy concerns."),
        ("Unredacted Board Minutes 2020", "Financial health checks.", "Denied", "Irrelevant to 2022 breach."),
        ("Invoices from Subcontractor X", "Quantum verification.", "Allowed", "Directly relevant to damages."),
        ("Native P6 Schedules (Baseline)", "Critical path analysis.", "Allowed", "Essential for delay experts."),
        ("Non-conformance reports (NCRs)", "Quality defect proof.", "Allowed", "Material to counter-claim."),
        ("Personal notebooks of Architect", "Contemporaneous notes.", "Denied", "Not in possession/control of party."),
        ("Draft Expert Reports (Previous)", "Inconsistency checking.", "Denied", "Privileged.")
    ]
    
    for i, (desc, rel, stat, dec) in enumerate(c_data):
        c_reqs.append({
            "id": i+1, "desc": desc, "relevance": rel, 
            "objection": "Burdensome / Privileged / Irrelevant.", "reply": "Objection unfounded.", 
            "decision": dec, "status": stat
        })

    # RESPONDENT REQUESTS (Low Rejection Rate -> Low Proportionality Score)
    r_reqs = []
    r_data = [
        ("Proof of payment for materials", "Quantum verification.", "Allowed", "Granted."),
        ("As-built drawings Section B", "Defect analysis.", "Allowed", "Granted."),
        ("Permit correspondence", "Legal compliance.", "Allowed", "Granted."),
        ("Bank Loan Agreements", "Financial capability.", "Denied", "Commercial confidence."),
        ("Labor timesheets (verified)", "Man-hour calculation.", "Allowed", "Granted."),
        ("Weather reports (Claimant's)", "Comparison.", "Denied", "Publicly available."),
        ("Variation Orders 1-15 (Signed)", "Scope change proof.", "Allowed", "Granted."),
        ("Insurance Policy", "Coverage limits.", "Allowed", "Granted."),
        ("Pre-contract notes", "Intent.", "Denied", "Parol evidence rule."),
        ("Notice of Dissatisfaction", "Jurisdictional prerequisite.", "Allowed", "Granted.")
    ]
    
    for i, (desc, rel, stat, dec) in enumerate(r_data):
        r_reqs.append({
            "id": i+1, "desc": desc, "relevance": rel, 
            "objection": "Confidential / Irrelevant.", "reply": "Material to defense.", 
            "decision": dec, "status": stat
        })
        
    return {"claimant": c_reqs, "respondent": r_reqs}

# --- 4. TIMELINE & EXTENSION REQUESTS GENERATOR (18 Months) ---
def generate_timeline_and_requests():
    # Base start date: 550 days ago (approx 18 months)
    start_date = get_past_date(550)
    
    # 1. GENERATE REQUESTS LOG (The "Delays" Tab)
    requests_log = []
    
    # Helper to create requests
    def add_req(event, party, reason, outcome, days_shifted, req_date_offset):
        req_date = start_date + timedelta(days=req_date_offset)
        requests_log.append({
            "event": event,
            "requestor": party,
            "reason": reason,
            "proposed_date": str(req_date + timedelta(days=days_shifted)),
            "status": outcome,
            "tribunal_decision": f"{outcome}. {('Deadline extended by ' + str(days_shifted) + ' days.') if outcome == 'Approved' else 'Original deadline maintained.'}"
        })

    # Generate 10 Requests for Claimant (Some Approved, Some Denied)
    add_req("Statement of Case", "claimant", "Lead Counsel tested positive for Covid-19.", "Approved", 14, 110)
    add_req("Document Production", "claimant", "IT failure in e-discovery platform.", "Approved", 7, 230)
    add_req("Reply Memorial", "claimant", "Expert witness unavailability due to family emergency.", "Approved", 21, 290)
    add_req("Hearing Dates", "claimant", "Conflict with another hearing.", "Denied", 0, 400)
    add_req("Post-Hearing Briefs", "claimant", "Need more time to review transcripts.", "Denied", 0, 480)
    add_req("Cost Submissions", "claimant", "Compilation of complex invoices.", "Approved", 3, 510)
    add_req("Redfern Schedule", "claimant", "Clarification on Tribunal Order needed.", "Denied", 0, 205)
    add_req("Expert Joint Report", "claimant", "Experts need more meeting time.", "Approved", 5, 380)
    add_req("Rejoinder (Respondent)", "claimant", "Requesting Respondent files earlier.", "Denied", 0, 350)
    add_req("Site Visit", "claimant", "Visa issues for client rep.", "Approved", 10, 150)

    # Generate 10 Requests for Respondent
    add_req("Statement of Defence", "respondent", "Need to translate 5,000 pages of exhibits.", "Approved", 28, 170)
    add_req("Document Production", "respondent", "Objections require detailed legal drafting.", "Denied", 0, 235)
    add_req("Rejoinder Memorial", "respondent", "New evidence discovered requiring analysis.", "Approved", 14, 350)
    add_req("Hearing Dates", "respondent", "Witness X cannot travel in June.", "Approved", 30, 410)
    add_req("Post-Hearing Briefs", "respondent", "Illness of junior associate.", "Denied", 0, 485)
    add_req("Cost Submissions", "respondent", "Currency conversion verification.", "Approved", 2, 512)
    add_req("Constitution of Tribunal", "respondent", "Challenge to arbitrator independence.", "Denied", 0, 45)
    add_req("Reply Memorial (Claimant)", "respondent", "Requesting Claimant cuts page count.", "Denied", 0, 280)
    add_req("Expert Joint Report", "respondent", "Disagreement on methodology.", "Denied", 0, 385)
    add_req("Final Award", "respondent", "Request for partial award first.", "Denied", 0, 540)

    # 2. GENERATE COMPLETED TIMELINE (Reflecting the Approved delays)
    # Note: Dates below are "Actuals" after the delays above were applied
    
    timeline = [
        {"m": "Notice of Arbitration", "d": 0, "p": "Claimant", "r": "Filing Notice.", "s": "Completed", "h": []},
        {"m": "Response to Notice", "d": 30, "p": "Respondent", "r": "Filing Response.", "s": "Completed", "h": []},
        {"m": "Constitution of Tribunal", "d": 60, "p": "All", "r": "Arbitrators Appointed.", "s": "Completed", "h": ["Challenge to Arb 2 Denied"]},
        {"m": "Procedural Order No. 1", "d": 90, "p": "Tribunal", "r": "Timetable set.", "s": "Completed", "h": []},
        {"m": "Statement of Case", "d": 134, "p": "Claimant", "r": "Full Memorial.", "s": "Completed", "h": ["Extended 14 days (Covid)"]},
        {"m": "Statement of Defence", "d": 208, "p": "Respondent", "r": "Counter-Memorial.", "s": "Completed", "h": ["Extended 28 days (Translation)"]},
        {"m": "Redfern Schedules Exchange", "d": 240, "p": "Both", "r": "Requests Only.", "s": "Completed", "h": []},
        {"m": "Document Production Order", "d": 270, "p": "Tribunal", "r": "Rulings on Objections.", "s": "Completed", "h": ["Extended 7 days (IT Failure)"]},
        {"m": "Reply Memorial", "d": 330, "p": "Claimant", "r": "Reply on Merits.", "s": "Completed", "h": ["Extended 21 days (Expert issue)"]},
        {"m": "Rejoinder Memorial", "d": 390, "p": "Respondent", "r": "Rejoinder on Merits.", "s": "Completed", "h": ["Extended 14 days (New Evidence)"]},
        {"m": "Expert Joint Reports", "d": 425, "p": "Both", "r": "Areas of Agreement.", "s": "Completed", "h": ["Extended 5 days"]},
        {"m": "Pre-Hearing Conference", "d": 440, "p": "All", "r": "Logistics finalized.", "s": "Completed", "h": []},
        {"m": "Main Evidentiary Hearing", "d": 500, "p": "All", "r": "IDRC London. 10 Days. Hybrid.", "s": "Completed", "h": ["Delayed 30 days (Witness Availability)"]},
        {"m": "Post-Hearing Briefs", "d": 530, "p": "Both", "r": "Closing submissions.", "s": "Completed", "h": []},
        {"m": "Statement of Costs", "d": 545, "p": "Both", "r": "Form H filings.", "s": "Completed", "h": ["Extended 3 days"]},
        {"m": "Final Award", "d": 600, "p": "Tribunal", "r": "Issuance of Award.", "s": "Commenced and Pending", "h": []} # Future date relative to start
    ]
    
    final_timeline = []
    for i, t in enumerate(timeline):
        dead_date = start_date + timedelta(days=t['d'])
        final_timeline.append({
            "id": f"ph_{i}",
            "milestone": t['m'],
            "deadline": str(dead_date),
            "responsible_party": t['p'],
            "requirements": t['r'],
            "compliance_status": t['s'],
            "days_remaining": (dead_date - date.today()).days,
            "amendment_history": t['h']
        })
        
    return final_timeline, requests_log

# --- INJECTION BUTTON ---
if st.button("🚀 INJECT FULL-SCALE DATASET", type="primary"):
    with st.spinner("Simulating 18 months of legal proceedings..."):
        
        # 1. Generate & Save Costs
        costs_data = generate_costs()
        save_complex_data("costs", costs_data)
        
        # 2. Generate & Save Doc Prod
        doc_data = generate_doc_prod()
        save_complex_data("doc_prod", doc_data)
        
        # 3. Generate & Save Timeline + Delays
        timeline_data, delay_log = generate_timeline_and_requests()
        save_complex_data("timeline", timeline_data)
        save_complex_data("delays", delay_log)
        
        # 4. Update Meta Status
        db.collection("arbitrations").document(case_id).update({"meta.status": "Phase 5: Award Deliberation"})

    st.success("✅ INJECTION COMPLETE.")
    st.balloons()
    st.markdown("### 🔍 Data Verification Checklist:")
    st.markdown("""
    1. **Timeline:** 18-month history loaded. Status is 'Awaiting Award'.
    2. **Doc Prod:** 20 requests loaded with mixed 'Allowed/Denied' outcomes.
    3. **Delays:** 20 extension requests loaded (check Timeline > Amendments tab).
    4. **Costs:** High-value entries loaded for C & R + A **Sealed Offer** of €4.5M.
    """)
    st.info("👉 You can now go to **Cost Management** and test the AI Award Generation.")
