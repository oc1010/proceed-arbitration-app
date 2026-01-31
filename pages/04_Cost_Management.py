import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data, load_responses, send_email_notification, upload_file_to_cloud, load_full_config, db
# Import from the cleaned ai_logic file
from ai_logic import generate_cost_award_draft, generate_word_document

st.set_page_config(page_title="Cost Management", layout="wide")

role = st.session_state.get('user_role')
case_id = st.session_state.get('active_case_id')

if not role or not case_id:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    
    if role == 'arbitrator':
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    elif role in ['claimant', 'respondent']:
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
        
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state['active_case_id'] = None
        st.switch_page("main.py")

st.title("💰 Phase 5: Cost Management")

# --- LOAD DATA ---
data = load_complex_data()
costs = data.get("costs", {
    "claimant_log": [], "respondent_log": [], 
    "final_submissions": [],
    "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, 
    "app_tagging": []
})
meta = load_full_config().get("meta", {})
merits_decided = meta.get("merits_decided", False)

# --- HELPER: DOUBLE BLIND VISIBILITY ---
def can_view_log(owner_role):
    """
    Double-Blind Interface Logic.
    - Parties see only their own costs.
    - Common costs are visible to all.
    - UNLOCK: After merits decided, unlocks for Arbitrator AND Parties.
    """
    if owner_role == 'common': return True
    if merits_decided: return True # Unlocks for everyone
    if role == owner_role: return True # See own
    if role == 'arbitrator': return True # Tribunal sees all logs (private view)
    return False

# --- TABS ---
tabs = st.tabs(["📝 Cost Logging", "💸 Payment Requests", "🏁 Final Submission", "🔒 Sealed Offers", "🤖 AI Final Award"])

# ==============================================================================
# TAB 1: COST LOGGING
# ==============================================================================
with tabs[0]:
    st.subheader("Cost Logging")
    
    # 1. INPUT FORM
    with st.expander(f"➕ Log New Expense ({role.title()})", expanded=False):
        with st.form("log_cost"):
            c1, c2 = st.columns(2)
            phase = c1.selectbox("Phase", ["Phase 1: Initiation", "Phase 2: Written Subs", "Phase 3: Doc Prod", "Phase 4: Hearing"]) 
            
            if role == 'arbitrator':
                cats = ["Tribunal Fees (Hours)", "Administrative", "Travel", "Drafting"]
                category = c2.selectbox("Category / Hours Spent", cats)
            else:
                cats = ["Legal Fees", "Expert Fees", "Transcripts", "e-Bundles", "Tribunal Fees"]
                category = c2.selectbox("Category", cats)
            
            c3, c4 = st.columns(2)
            d_exp = c3.date_input("Date of Expenditure")
            amt = c4.number_input("Amount (EUR)", min_value=0.0)
            
            is_common = st.checkbox("Mark as Common/Arbitration Cost (Visible to All)") 
            
            if st.form_submit_button("Log Expense"):
                entry = {
                    "phase": phase, "category": category, 
                    "date": str(d_exp), "amount": amt, 
                    "logged_by": role
                }
                target_list = "common_log" if is_common else f"{role}_log"
                
                if target_list not in costs: costs[target_list] = []
                costs[target_list].append(entry)
                save_complex_data("costs", costs)
                st.success("Expense Logged.")
                st.rerun()

    st.divider()

    # 2. PRIVATE COST SUMMARY
    st.markdown(f"### 🔐 Private Cost Summary ({role.title()})")
    my_private_data = costs.get(f"{role}_log", [])
    if my_private_data:
        st.dataframe(pd.DataFrame(my_private_data), use_container_width=True)
    else:
        st.info("No private costs logged yet.")

    # 3. ARBITRATION COST SUMMARY (COMMON)
    st.markdown("### 🌍 Arbitration Cost Summary (Common)")
    common_data = costs.get("common_log", [])
    if common_data:
        st.dataframe(pd.DataFrame(common_data), use_container_width=True)
    else:
        st.caption("No common costs logged yet.")

# ==============================================================================
# TAB 2: PAYMENT REQUESTS
# ==============================================================================
with tabs[1]:
    st.subheader("Financial Management")
    
    # ARBITRATOR: REQUEST PAYMENT
    if role == 'arbitrator':
        st.write("#### 📤 Request Payment / Deposit")
        with st.form("req_pay"):
            c1, c2 = st.columns(2)
            dep_type = c1.selectbox("Deposit Type", ["Administrative Fees", "Tribunal Fees", "Hearing Expenses", "Expert / Specialist Fund"])
            p_amt = c2.number_input("Amount Requested (€)", min_value=0.0)
            
            c3, c4 = st.columns(2)
            p_due = c3.date_input("Due Date")
            payer = c4.radio("Payable By", ["Claimant", "Respondent", "Split 50/50"])
            
            if st.form_submit_button("Send Payment Order"):
                req = {
                    "type": dep_type, "amount": p_amt, 
                    "due": str(p_due), "payer": payer, 
                    "status": "Pending"
                }
                if "payment_requests" not in costs: costs["payment_requests"] = []
                costs["payment_requests"].append(req)
                save_complex_data("costs", costs)
                st.success("Payment Order Logged.")
                st.rerun()

    # ALL: VIEW REQUESTS
    st.write("#### 📜 Payment / Deposit Requests")
    reqs = costs.get("payment_requests", [])
    if reqs:
        st.dataframe(pd.DataFrame(reqs), use_container_width=True)
    else:
        st.info("No active payment requests.")

# ==============================================================================
# TAB 3: FINAL SUBMISSION
# ==============================================================================
with tabs[2]:
    st.subheader("Final Statement of Costs")
    if role in ['claimant', 'respondent']:
        with st.form("final_sub"):
            total = st.number_input("Total Claimed (€)", min_value=0.0)
            if st.form_submit_button("Submit Final Statement"):
                costs['final_submissions'].append({"party": role, "amount": total, "date": str(date.today())})
                save_complex_data("costs", costs)
                st.success("Submitted.")

# ==============================================================================
# TAB 4: SEALED OFFERS
# ==============================================================================
with tabs[3]:
    st.subheader("✉️ Settlement Offer Vault")
    st.info("Offers are ENCRYPTED. The Tribunal sees existence but not amount until the Award.")
    
    if role in ['claimant', 'respondent']:
        with st.form("sealed_offer"):
            offer_amt = st.number_input("Settlement Offer Amount (€)", min_value=0.0)
            if st.form_submit_button("Submit Sealed Offer"):
                entry = {
                    "offerer": role, "amount": offer_amt,
                    "date": str(date.today()), "status": "Sealed"
                }
                if "sealed_offers" not in costs: costs["sealed_offers"] = []
                costs["sealed_offers"].append(entry)
                save_complex_data("costs", costs)
                st.success("Offer Sealed and Submitted.")

    if role == 'arbitrator':
        offers = costs.get("sealed_offers", [])
        if offers:
            st.write(f"⚠️ **{len(offers)} Sealed Offer(s) Detected**")
            for i, o in enumerate(offers):
                # Reveal logic based on merits_decided
                status_txt = f"**Offer #{i+1}** | Date: {o['date']} | Status: **{o['status']}**"
                if not merits_decided:
                    st.info(f"{status_txt} (Locked 🔒)")
                else:
                    st.success(f"{status_txt} - 🔓 REVEALED: €{o['amount']:,.2f} by {o['offerer'].title()}")

# ==============================================================================
# TAB 5: AI FINAL AWARD (Tribunal Only)
# ==============================================================================
if role == 'arbitrator':
    with tabs[4]:
        st.subheader("🤖 AI Cost Allocation Recommendation")
        st.info("This tool acts as a 'Tribunal Secretary', analyzing the hard data to propose a logical cost split.")
        
        # 1. TRIGGER MERITS DECISION
        st.write("#### 1. Merits Phase Completion")
        is_decided = st.checkbox("✅ Declare Merits Decision Rendered", value=merits_decided)
        if is_decided != merits_decided:
            db.collection("arbitrations").document(case_id).update({"meta.merits_decided": is_decided})
            st.rerun()

        if is_decided:
            # 2. INPUT AWARD VALUE
            award_val = st.number_input("Final Principal Award Amount (€)", value=meta.get("final_award_amount", 0.0))
            if st.button("Save Award Value"):
                 db.collection("arbitrations").document(case_id).update({"meta.final_award_amount": award_val})
                 st.toast("Value Saved")

            st.divider()
            
            # 3. GENERATE & DOWNLOAD
            col1, col2 = st.columns(2)
            
            if "ai_draft" not in st.session_state:
                st.session_state["ai_draft"] = ""

            with col1:
                st.write("#### 1. Generate Analysis")
                if st.button("✨ Draft Recommendation (Vertex AI)", type="primary"):
                    with st.spinner("Reviewing conduct, delays, and sealed offers..."):
                        # Calls the function from ai_logic.py
                        st.session_state["ai_draft"] = generate_cost_award_draft(case_id, award_val)
            
            if st.session_state["ai_draft"]:
                st.markdown("---")
                st.markdown("### 📝 Draft Recommendation")
                st.write(st.session_state["ai_draft"])
                
                with col2:
                    st.write("#### 2. Export")
                    # Uses the doc generator from ai_logic.py
                    docx = generate_word_document(case_id, st.session_state["ai_draft"], award_val)
                    
                    st.download_button(
                        label="📄 Download Formal Word Doc (.docx)",
                        data=docx,
                        file_name=f"Cost_Recommendation_{case_id}.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )
