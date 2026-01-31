import streamlit as st
from datetime import datetime, timedelta, date
import random
from db import get_active_case_id, save_complex_data, db

st.set_page_config(page_title="Realistic Demo Injector", page_icon="💉", layout="wide")

st.title("💉 Realistic Arbitration Data Injector")
st.warning("⚠️ OVERWRITE WARNING: This will reset the case to a realistic 'End of Hearing' state.")

# --- AUTH CHECK ---
case_id = get_active_case_id()
if not case_id:
    st.error("No Active Case found. Please login first.")
    st.stop()

st.info(f"Targeting Case: **{case_id}**")

# --- 1. GENERATOR UTILITIES ---
def get_past_date(days_ago):
    return date.today() - timedelta(days=days_ago)

# --- 2. COST DATA GENERATOR ---
def generate_costs():
    categories = ["Legal Fees (Partners)", "Legal Fees (Associates)", "Expert Witness Fees", "Administrative Costs", "Travel & Accommodation", "Translation Services", "Hearing Venue Costs"]
    phases = ["Phase 1: Initiation", "Phase 2: Written Submissions", "Phase 3: Doc Production", "Phase 4: Hearing"]
    
    c_log = []
    r_log = []
    
    # Claimant: ~€1.8M total
    for i in range(12):
        amt = random.randint(15000, 250000)
        c_log.append({
            "phase": random.choice(phases),
            "category": random.choice(categories),
            "date": str(get_past_date(random.randint(30, 500))),
            "amount": amt,
            "logged_by": "claimant",
            "desc": f"Inv #{random.randint(1000,9999)}: Services rendered."
        })

    # Respondent: ~€1.6M total
    for i in range(14):
        amt = random.randint(12000, 220000)
        r_log.append({
            "phase": random.choice(phases),
            "category": random.choice(categories),
            "date": str(get_past_date(random.randint(30, 500))),
            "amount": amt,
            "logged_by": "respondent",
            "desc": f"Inv #{random.randint(1000,9999)}: Professional services."
        })
        
    common_log = [
        {"phase": "Phase 1", "category": "Tribunal Advance", "date": str(get_past_date(520)), "amount": 60000, "logged_by": "lcia"},
        {"phase": "Phase 4", "category": "Hearing Venue Deposit", "date": str(get_past_date(100)), "amount": 25000, "logged_by": "lcia"},
    ]
    
    # Sealed Offer: €4.5M (If Award < 4.5M, Respondent wins costs)
    offers = [
        {"offerer": "respondent", "amount": 4500000.0, "date": str(get_past_date(180)), "status": "Sealed"}
    ]

    return {"claimant_log": c_log, "respondent_log": r_log, "common_log": common_log, "payment_requests": [], "sealed_offers": offers}

# --- 3. DOC PRODUCTION GENERATOR ---
def generate_doc_prod():
    # Mixed outcomes, but realistic (most denied/allowed in chunks)
    c_reqs = []
    c_data = [
        ("Minutes of Board Meetings Jan-Jun 2022", "Proof of delay knowledge.", "Allowed"),
        ("Internal emails: CEO & Project Director", "Bad faith evidence.", "Allowed"),
        ("All WhatsApp messages from site", "Informal instructions.", "Denied"), # Frivolous
        ("Unredacted Board Minutes 2010-2023", "Financial health.", "Denied"), # Fishing
        ("Invoices from Subcontractor X", "Quantum verification.", "Allowed"),
    ]
    for i, (desc, rel, stat) in enumerate(c_data):
        c_reqs.append({"id": i+1, "desc": desc, "relevance": rel, "objection": "Standard objection.", "reply": "Maintained.", "decision": stat, "status": stat})

    r_reqs = []
    r_data = [
        ("Proof of payment for materials", "Quantum verification.", "Allowed"),
        ("As-built drawings Section B", "Defect analysis.", "Allowed"),
        ("Personal notes of Architect", "Contemporaneous record.", "Denied"), # Personal property
    ]
    for i, (desc, rel, stat) in enumerate(r_data):
        r_reqs.append({"id": i+1, "desc": desc, "relevance": rel, "objection": "Standard objection.", "reply": "Maintained.", "decision": stat, "status": stat})
        
    return {"claimant": c_reqs, "respondent": r_reqs}

# --- 4. REALISTIC TIMELINE (Mostly Compliant) ---
def generate_timeline_and_requests():
    # Start date ~18 months ago
    start = get_past_date(550)
    
    # 1. EXTENSION REQUESTS (Only 3 realistic ones)
    # R requests extension for Defence (Granted)
    # C requests extension for Reply (Denied)
    # Both request hearing shift (Granted)
    
    req_log = []
    
    # Approved Delay: Respondent Defence (+14 Days)
    req_log.append({
        "event": "Statement of Defence", "requestor": "respondent",
        "reason": "Lead Counsel medical emergency.",
        "proposed_date": str(start + timedelta(days=120 + 14)),
        "status": "Approved", "tribunal_decision": "Granted due to medical certification."
    })
    
    # Denied Delay: Claimant Reply
    req_log.append({
        "event": "Reply Memorial", "requestor": "claimant",
        "reason": "Expert witness schedule conflict.",
        "proposed_date": str(start + timedelta(days=200 + 7)),
        "status": "Denied", "tribunal_decision": "Denied. Schedule must be maintained."
    })

    # 2. TIMELINE (Reflecting the 14-day shift from Step 2 onwards)
    # Note: 'd' is days from start. We bake in the 14-day delay for Respondent and subsequent steps.
    
    timeline = [
        {"m": "Notice of Arbitration", "d": 0, "p": "Claimant", "s": "Completed", "h": []},
        {"m": "Constitution", "d": 60, "p": "All", "s": "Completed", "h": []},
        {"m": "Procedural Order No. 1", "d": 90, "p": "Tribunal", "s": "Completed", "h": []},
        {"m": "Statement of Case", "d": 120, "p": "Claimant", "s": "Completed", "h": []},
        
        # DELAY HAPPENED HERE (Original 150 -> Actual 164)
        {"m": "Statement of Defence", "d": 164, "p": "Respondent", "s": "Completed", "h": ["Extended by 14 days (Medical)"]},
        
        # Subsequent steps shifted by 14 days to accommodate
        {"m": "Redfern Schedules", "d": 194, "p": "Both", "s": "Completed", "h": []},
        {"m": "Document Production Order", "d": 224, "p": "Tribunal", "s": "Completed", "h": []},
        {"m": "Reply Memorial", "d": 284, "p": "Claimant", "s": "Completed", "h": ["Extension Denied"]},
        {"m": "Rejoinder Memorial", "d": 344, "p": "Respondent", "s": "Completed", "h": []},
        {"m": "Pre-Hearing Conference", "d": 400, "p": "All", "s": "Completed", "h": []},
        {"m": "Main Evidentiary Hearing", "d": 450, "p": "All", "s": "Completed", "h": []},
        {"m": "Post-Hearing Briefs", "d": 500, "p": "Both", "s": "Completed", "h": []},
        {"m": "Statement of Costs", "d": 520, "p": "Both", "s": "Completed", "h": []},
        
        # FUTURE STEP
        {"m": "Final Award", "d": 580, "p": "Tribunal", "s": "Commenced and Pending", "h": []} 
    ]
    
    final_timeline = []
    for i, t in enumerate(timeline):
        dead_date = start + timedelta(days=t['d'])
        final_timeline.append({
            "id": f"ph_{i}", "milestone": t['m'], "deadline": str(dead_date),
            "responsible_party": t['p'], "requirements": "Standard submission.",
            "compliance_status": t['s'], "days_remaining": (dead_date - date.today()).days,
            "amendment_history": t['h']
        })
        
    return final_timeline, req_log

# --- INJECTION BUTTON ---
if st.button("🚀 INJECT REALISTIC DATA", type="primary"):
    with st.spinner("Simulating controlled arbitration proceedings..."):
        costs = generate_costs()
        save_complex_data("costs", costs)
        
        doc_prod = generate_doc_prod()
        save_complex_data("doc_prod", doc_prod)
        
        timeline, delays = generate_timeline_and_requests()
        save_complex_data("timeline", timeline)
        save_complex_data("delays", delays)
        
        db.collection("arbitrations").document(case_id).update({"meta.status": "Phase 5: Award Deliberation"})

    st.success("✅ REALISTIC DATA INJECTED.")
    st.balloons()
    st.markdown("""
    **Scenario Created:**
    - **Delays:** Only 1 major approved delay (Statement of Defence).
    - **Doc Prod:** 5 requests per side (realistic volume), mixed outcomes.
    - **Costs:** High value, sealed offer of €4.5M present.
    """)
