import streamlit as st
from datetime import datetime, timedelta, date
import random
from db import get_active_case_id, save_complex_data, db

st.set_page_config(page_title="Realistic Demo Injector", page_icon="💉", layout="wide")

st.title("💉 Scenario Builder: 'The Construction Dispute'")
st.warning("⚠️ OVERWRITE WARNING: This will reset Case Data to a complex 'Post-Hearing' state.")

# --- AUTH CHECK ---
case_id = get_active_case_id()
if not case_id:
    st.error("No Active Case found. Please login first.")
    st.stop()

st.info(f"Targeting Case: **{case_id}**")

# --- 1. GENERATOR UTILITIES ---
def get_date(base_date, offset_days):
    return base_date + timedelta(days=offset_days)

# --- 2. COST DATA GENERATOR ---
def generate_costs(start_date):
    # Phases
    phases = [
        ("Phase 1: Initiation", 0, 60),
        ("Phase 2: Written Submissions", 60, 200),
        ("Phase 3: Document Production", 200, 260),
        ("Phase 4: Interim Applications", 100, 300), # Sporadic
        ("Phase 5: Hearing Preparation", 300, 400),
        ("Phase 6: Hearing", 400, 415)
    ]
    
    c_log = []
    r_log = []
    
    # Generate random invoices across the timeline
    for phase_name, start_day, end_day in phases:
        # Claimant (High Burn Rate)
        for _ in range(random.randint(3, 6)):
            d = get_date(start_date, random.randint(start_day, end_day))
            amt = random.randint(15000, 85000)
            c_log.append({
                "phase": phase_name, "category": "Legal Fees",
                "date": str(d), "amount": amt, "logged_by": "claimant"
            })
            
        # Respondent (Lower Burn Rate)
        for _ in range(random.randint(2, 5)):
            d = get_date(start_date, random.randint(start_day, end_day))
            amt = random.randint(10000, 65000)
            r_log.append({
                "phase": phase_name, "category": "Legal Fees",
                "date": str(d), "amount": amt, "logged_by": "respondent"
            })

    # Specific Big Ticket Items
    # 1. Failed Interim Application Cost (Respondent defended successfully)
    r_log.append({
        "phase": "Phase 4: Interim Applications", "category": "Legal Fees (Security for Costs)",
        "date": str(get_date(start_date, 150)), "amount": 45000, "logged_by": "respondent",
        "note": "Defense against Security for Costs"
    })

    # 2. Sealed Offer (Respondent offers €3.8M on Day 250)
    offer_date = str(get_date(start_date, 250))
    offers = [
        {"offerer": "respondent", "amount": 3800000.0, "date": offer_date, "status": "Sealed"}
    ]
    
    # Common Costs
    common_log = [
        {"phase": "Phase 1", "category": "Tribunal Advance", "date": str(get_date(start_date, 30)), "amount": 100000, "logged_by": "common"},
        {"phase": "Phase 6", "category": "Hearing Venue", "date": str(get_date(start_date, 405)), "amount": 30000, "logged_by": "common"},
    ]

    return {"claimant_log": c_log, "respondent_log": r_log, "common_log": common_log, "payment_requests": [], "sealed_offers": offers}

# --- 3. DOC PRODUCTION (SKEWED) ---
def generate_doc_prod():
    # Claimant: Fishing Expedition (80% Rejection) -> Triggers Penalty
    c_reqs = []
    for i in range(10):
        status = "Denied" if i < 8 else "Allowed" # 8 Denied, 2 Allowed
        c_reqs.append({"id": i+1, "category": "Internal Emails", "decision": status, "status": status})

    # Respondent: Reasonable (20% Rejection) -> Safe
    r_reqs = []
    for i in range(5):
        status = "Denied" if i < 1 else "Allowed" # 1 Denied, 4 Allowed
        r_reqs.append({"id": i+1, "category": "Payment Records", "decision": status, "status": status})
        
    return {"claimant": c_reqs, "respondent": r_reqs}

# --- 4. TIMELINE & DELAYS (NUANCED) ---
def generate_timeline(start_date):
    timeline = []
    delays = []
    
    milestones = [
        ("Notice of Arbitration", 0, "Completed"),
        ("Answer to Notice", 30, "Completed"),
        ("Procedural Order No. 1", 60, "Completed"),
        ("Statement of Claim", 120, "Completed"),
        ("Statement of Defence", 180, "Completed"), # Extension Granted
        ("Reply Memorial", 240, "Completed"), # DELAY PENALTY HERE
        ("Rejoinder Memorial", 300, "Completed"),
        ("Document Production", 330, "Completed"),
        ("Hearing", 410, "Completed"),
        ("Post-Hearing Briefs", 450, "Pending")
    ]
    
    for m, days, status in milestones:
        timeline.append({
            "milestone": m, "deadline": str(get_date(start_date, days)),
            "compliance_status": status
        })
        
    # Inject Delays
    # 1. Consensual Extension (Respondent SoD) - No Penalty
    delays.append({
        "event": "Statement of Defence", "requestor": "respondent",
        "reason": "Parties agreed to 2-week extension.",
        "status": "Approved", "is_consensual": True, "days": 14
    })
    
    # 2. Non-Consensual Delay (Claimant Reply) - Penalty Trigger
    delays.append({
        "event": "Reply Memorial", "requestor": "claimant",
        "reason": "Expert unavailable.",
        "status": "Denied", # Request was denied
        "is_consensual": False, 
        "days": 5, # Filed 5 days late anyway
        "note": "Filed late despite denial of extension."
    })
    
    return timeline, delays

# --- 5. INTERIM APPLICATIONS ---
def generate_applications(start_date):
    # Claimant filed for Security for Costs -> Denied -> Cost Shifting applies
    apps = [
        {
            "type": "Security for Costs", "filing_party": "claimant",
            "date": str(get_date(start_date, 140)),
            "outcome": "Denied",
            "tribunal_order": "Costs of the Application reserved for Final Award."
        }
    ]
    return apps

# --- INJECTION BUTTON ---
if st.button("🚀 INJECT 'CONSTRUCTION DISPUTE' SCENARIO", type="primary"):
    start_date = date.today() - timedelta(days=460) # Case started 1.5 years ago
    
    with st.spinner("Building procedural history..."):
        costs = generate_costs(start_date)
        save_complex_data("costs", costs)
        
        doc_prod = generate_doc_prod()
        save_complex_data("doc_prod", doc_prod)
        
        timeline, delays = generate_timeline(start_date)
        save_complex_data("timeline", timeline)
        save_complex_data("delays", delays)
        
        apps = generate_applications(start_date)
        save_complex_data("applications", apps)
        
        db.collection("arbitrations").document(case_id).update({"meta.status": "Phase 6: Post-Hearing"})

    st.success("✅ SCENARIO INJECTED: 'The Construction Dispute'")
    st.markdown("""
    **Scenario Details:**
    * **Conduct:** Claimant fishing expedition (80% doc rejection).
    * **Delays:** Claimant filed Reply late (Non-consensual). Respondent got a consensual extension.
    * **Interim Apps:** Claimant lost a 'Security for Costs' application.
    * **Sealed Offer:** Respondent offered €3.8M on Day 250.
    * **Costs:** Respondent costs lower than Claimant.
    """)
