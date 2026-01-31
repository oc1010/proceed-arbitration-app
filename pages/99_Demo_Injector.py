import streamlit as st
from datetime import datetime, timedelta, date
from db import db, get_active_case_id, save_complex_data

st.set_page_config(page_title="Demo Data Injector", page_icon="💉", layout="centered")

st.title("💉 Demo Data Injector")
st.warning("This tool is for DEMO PURPOSES. It will overwrite the Timeline, Doc Production, and Delay data for the active case.")

# --- CHECK AUTH ---
case_id = get_active_case_id()
if not case_id:
    st.error("No Active Case found. Please login to the LCIA/Arbitrator dashboard first.")
    st.stop()

st.info(f"Target Case: **{case_id}**")

# --- DATA GENERATORS ---
def get_demo_timeline():
    # Relative dates to ensure status colors work immediately
    today = date.today()
    
    return [
        {
            "id": "ph_1",
            "milestone": "Notice of Arbitration & Constitution",
            "deadline": str(today - timedelta(days=45)),
            "responsible_party": "Both",
            "requirements": "Filing of Notice, Response, and nomination of arbitrators.",
            "compliance_status": "Completed",
            "days_remaining": -45,
            "amendment_history": []
        },
        {
            "id": "ph_2",
            "milestone": "Procedural Order No. 1",
            "deadline": str(today - timedelta(days=15)),
            "responsible_party": "Tribunal",
            "requirements": "Drafting and finalization of procedural timetable.",
            "compliance_status": "Completed",
            "days_remaining": -15,
            "amendment_history": []
        },
        {
            "id": "ph_3",
            "milestone": "Claimant's Statement of Case",
            # OVERDUE ITEM (Red Flag Test)
            "deadline": str(today - timedelta(days=2)), 
            "responsible_party": "Claimant",
            "requirements": "Full statement of case including witness statements and expert reports (Memorial Style).",
            "compliance_status": "Awaiting Compliance", 
            "days_remaining": -2,
            "amendment_history": ["Extension requested on grounds of witness unavailability."]
        },
        {
            "id": "ph_4",
            "milestone": "Respondent's Statement of Defence",
            "deadline": str(today + timedelta(days=28)),
            "responsible_party": "Respondent",
            "requirements": "Statement of defence and counterclaims (if any).",
            "compliance_status": "Commenced and Pending",
            "days_remaining": 28,
            "amendment_history": []
        },
        {
            "id": "ph_5",
            "milestone": "Document Production (Redfern)",
            "deadline": str(today + timedelta(days=45)),
            "responsible_party": "Both",
            "requirements": "Submission of Redfern Schedules (use Doc Production Module).",
            "compliance_status": "Commenced and Pending",
            "days_remaining": 45,
            "amendment_history": []
        },
        {
            "id": "ph_6",
            "milestone": "Main Evidentiary Hearing",
            "deadline": str(today + timedelta(days=120)),
            "responsible_party": "All",
            "requirements": "Hybrid hearing, London Seat. See Hearing Logistics tab.",
            "compliance_status": "Commenced and Pending",
            "days_remaining": 120,
            "amendment_history": []
        }
    ]

def get_demo_doc_prod():
    # Includes Allowed, Denied (for AI score), and Objected items
    return {
        "claimant": [
            {
                "id": 1, 
                "desc": "Minutes of Board Meeting dated 12 Jan 2023.", 
                "relevance": "Proves knowledge of the breach.", 
                "objection": "Internal confidentiality.", 
                "reply": "Confidentiality is not a bar to production.", 
                "decision": "Tribunal orders production.", 
                "status": "Allowed"
            },
            {
                "id": 2, 
                "desc": "All WhatsApp messages between CEO and CFO regarding 'Project X'.", 
                "relevance": "Context of negotiation.", 
                "objection": "Overly broad and burdensome.", 
                "reply": "Necessary to show intent.", 
                "decision": "Request is fishing expedition.", 
                "status": "Denied" # This triggers the AI Score logic
            },
            {
                "id": 3, 
                "desc": "Q3 2023 Financial Audit Reports.", 
                "relevance": "Quantification of damages.", 
                "objection": "", 
                "reply": "", 
                "decision": "", 
                "status": "Pending"
            }
        ],
        "respondent": [
             {
                "id": 1, 
                "desc": "Original Contract (Wet Ink Copy).", 
                "relevance": "Authenticity verification.", 
                "objection": "Original lost, copy provided.", 
                "reply": "", 
                "decision": "Tribunal accepts copy.", 
                "status": "Allowed"
            },
            {
                "id": 2, 
                "desc": "Email correspondence with Supplier Y.", 
                "relevance": "Supply chain disruption proof.", 
                "objection": "Commercial secrets.", 
                "reply": "", 
                "decision": "", 
                "status": "Objected"
            }
        ]
    }

def get_demo_delays():
    today = date.today()
    return [
        {
            "event": "Claimant's Statement of Case",
            "requestor": "claimant",
            "reason": "Key expert witness was hospitalized unexpectedly.",
            "proposed_date": str(today + timedelta(days=7)),
            "status": "Pending",
            "tribunal_decision": ""
        },
        {
            "event": "Document Production (Redfern)",
            "requestor": "respondent",
            "reason": "Volume of documents requires external vendor processing.",
            "proposed_date": str(today + timedelta(days=50)),
            "status": "Approved",
            "tribunal_decision": "Granted. Schedule adjusted."
        }
    ]

# --- INJECTION BUTTON ---
if st.button("🚀 INJECT DEMO DATA NOW", type="primary"):
    with st.spinner("Injecting complex arbitration scenario..."):
        
        # 1. Update Timeline
        save_complex_data("timeline", get_demo_timeline())
        
        # 2. Update Doc Prod
        save_complex_data("doc_prod", get_demo_doc_prod())
        
        # 3. Update Delays
        save_complex_data("delays", get_demo_delays())
        
        # 4. Optional: Add a cost log to make Phase 5 look busy
        save_complex_data("costs", {
            "claimant_log": [{"phase": "Phase 1", "category": "Legal Fees", "date": "2023-10-01", "amount": 15000, "logged_by": "claimant"}],
            "respondent_log": [{"phase": "Phase 1", "category": "Legal Fees", "date": "2023-10-05", "amount": 12000, "logged_by": "respondent"}],
            "common_log": [{"phase": "Phase 1", "category": "Tribunal Fees", "date": "2023-09-01", "amount": 30000, "logged_by": "arbitrator"}],
            "sealed_offers": [],
            "payment_requests": []
        })

    st.success("✅ Injection Complete!")
    st.balloons()
    st.markdown("""
    **Navigate to:**
    - **Page 03 (Timeline):** See the 'Overdue' red text and the 'Completed' items.
    - **Page 02 (Doc Prod):** See the Allowed/Denied requests and the Scorecard.
    - **Page 03 (Timeline > Extensions Tab):** See the pending delay request.
    """)
