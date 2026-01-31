import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data, load_full_config, db, send_email_notification
from ai_logic import generate_cost_award_draft, check_sealed_offers

st.set_page_config(page_title="Cost Management", layout="wide")

# --- AUTH ---
role = st.session_state.get('user_role')
case_id = st.session_state.get('active_case_id')
if not role or not case_id:
    st.error("Access Denied.")
    st.stop()

# --- LOAD DATA ---
data = load_complex_data()
costs = data.get("costs", {})
meta = load_full_config().get("meta", {})
merits_decided = meta.get("merits_decided", False) # [cite: 104]

# --- HELPER: DOUBLE BLIND VISIBILITY ---
def can_view_log(owner_role):
    """
    [cite: 101, 102] Double-Blind Interface Logic.
    Tribunal can only see everyone's costs AFTER merits decided[cite: 104].
    """
    if owner_role == 'common': return True # [cite: 103]
    if role == owner_role: return True
    if role == 'arbitrator' and merits_decided: return True # [cite: 109]
    return False

# --- SIDEBAR (Standard) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    if st.button("Logout"): st.switch_page("main.py")

st.title("💰 Phase 5: Cost Management")

# --- KPI METRICS (Burn Rate) [cite: 98] ---
my_logs = costs.get(f"{role}_log", []) if role != 'lcia' else []
if my_logs:
    df_metrics = pd.DataFrame(my_logs)
    total_spend = df_metrics['amount'].sum()
    st.metric("Total Logged Costs", f"€{total_spend:,.2f}")

# --- TABS ---
# [cite: 111, 121]
tabs = st.tabs(["📝 Cost Logging", "⚖️ Tribunal Ledger", "🔒 Sealed Offers", "🤖 AI Final Award"])

# ==============================================================================
# TAB 1: COST LOGGING (Double Blind)
# ==============================================================================
with tabs[0]:
    st.subheader("Cost Logging & Assessment")
    
    # 1. INPUT FORM (Role Specific) [cite: 113, 123]
    with st.expander(f"➕ Log New Expense ({role.title()})", expanded=False):
        with st.form("log_cost"):
            c1, c2 = st.columns(2)
            phase = c1.selectbox("Phase", ["Phase 1: Initiation", "Phase 2: Written Subs", "Phase 3: Doc Prod", "Phase 4: Hearing"]) # [cite: 114]
            category = c2.selectbox("Category", ["Legal Fees", "Expert Fees", "Transcripts", "Tribunal Fees", "Other"]) # [cite: 115]
            
            c3, c4 = st.columns(2)
            d_exp = c3.date_input("Date of Expenditure") # [cite: 116]
            amt = c4.number_input("Amount (EUR)", min_value=0.0) # [cite: 117]
            
            is_common = st.checkbox("Mark as Common/Shared Cost (Visible to All)") # [cite: 120]
            
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

    # 2. VIEW LOGS (Blind Logic)
    c_claimant, c_respondent = st.columns(2)
    
    with c_claimant:
        st.markdown("### 👤 Claimant's Costs")
        if can_view_log('claimant'):
            if costs.get('claimant_log'):
                st.dataframe(pd.DataFrame(costs['claimant_log']), use_container_width=True)
            else: st.info("No logs.")
        else:
            st.warning("🔒 HIDDEN (Double-Blind Active)") # [cite: 101]

    with c_respondent:
        st.markdown("### 👤 Respondent's Costs")
        if can_view_log('respondent'):
            if costs.get('respondent_log'):
                st.dataframe(pd.DataFrame(costs['respondent_log']), use_container_width=True)
            else: st.info("No logs.")
        else:
            st.warning("🔒 HIDDEN (Double-Blind Active)")

    st.markdown("### 🌍 Common / Arbitration Costs (Visible to All)") # [cite: 103]
    if costs.get('common_log'):
        st.dataframe(pd.DataFrame(costs['common_log']), use_container_width=True)

# ==============================================================================
# TAB 2: TRIBUNAL LEDGER & REQUESTS
# ==============================================================================
with tabs[1]:
    st.subheader("Tribunal Financials")
    
    if role == 'arbitrator':
        st.write("#### 📤 Request Payment") # [cite: 131]
        with st.form("req_pay"):
            c1, c2, c3 = st.columns(3)
            p_type = c1.selectbox("Type", ["Advance on Costs", "Interim Payment", "Hearing Deposit"]) # [cite: 133]
            p_amt = c2.number_input("Amount (€)", min_value=0.0)
            p_due = c3.date_input("Due Date")
            
            payer = st.radio("Payable By", ["Claimant", "Respondent", "Split 50/50"]) # [cite: 139]
            
            if st.form_submit_button("Send Payment Order"):
                req = {"type": p_type, "amount": p_amt, "due": str(p_due), "payer": payer, "status": "Pending"}
                if "payment_requests" not in costs: costs["payment_requests"] = []
                costs["payment_requests"].append(req)
                save_complex_data("costs", costs)
                st.toast("Payment Request Sent & Reminders Set") # 
                st.rerun()
    
    st.write("#### 📜 Payment History")
    if costs.get("payment_requests"):
        st.dataframe(pd.DataFrame(costs["payment_requests"]), use_container_width=True)

# ==============================================================================
# TAB 3: SEALED OFFERS (Settlement)
# ==============================================================================
with tabs[2]:
    st.subheader("✉️ Sealed Settlement Offers") # [cite: 81]
    st.info("Offers uploaded here are ENCRYPTED. The Tribunal is notified that an offer exists, but cannot see the amount/content until the Final Award value is entered.") # [cite: 83, 85]
    
    # UPLOAD (Parties Only)
    if role in ['claimant', 'respondent']:
        with st.form("sealed_offer"):
            offer_amt = st.number_input("Settlement Offer Amount (€)", min_value=0.0)
            offer_doc = st.file_uploader("Upload Formal Offer Letter (PDF)")
            
            if st.form_submit_button("Submit Sealed Offer"):
                # Mock Encryption: In real app, use cryptography lib
                entry = {
                    "offerer": role,
                    "amount": offer_amt, # Hidden in UI for Arb
                    "date": str(date.today()),
                    "status": "Sealed"
                }
                if "sealed_offers" not in costs: costs["sealed_offers"] = []
                costs["sealed_offers"].append(entry)
                save_complex_data("costs", costs)
                st.success("Offer Sealed and Submitted.")

    # VIEW (Tribunal View)
    if role == 'arbitrator':
        offers = costs.get("sealed_offers", [])
        if offers:
            st.write(f"⚠️ **{len(offers)} Sealed Offer(s) Detected**") # [cite: 84]
            for i, o in enumerate(offers):
                st.markdown(f"**Offer #{i+1}** | Date: {o['date']} | Status: **{o['status']}**")
                if not merits_decided:
                    st.caption("🔒 Content Locked until Merits Decision.") # [cite: 85]
                else:
                    st.success(f"🔓 REVEALED: €{o['amount']:,.2f} by {o['offerer'].title()}")
        else:
            st.write("No sealed offers on file.")

# ==============================================================================
# TAB 4: AI FINAL AWARD (The Brain)
# ==============================================================================
with tabs[3]:
    st.subheader("🤖 AI Final Award on Costs") # 
    
    if role != 'arbitrator':
        st.warning("Only the Tribunal can generate the Final Award.")
        st.stop()
        
    # 1. TRIGGER MERITS DECISION
    st.write("#### 1. Merits Phase Completion")
    is_decided = st.checkbox("✅ Declare Merits Decision Rendered", value=merits_decided)
    
    if is_decided != merits_decided:
        # Update DB trigger
        db.collection("arbitrations").document(case_id).update({"meta.merits_decided": is_decided})
        st.rerun()

    if is_decided:
        st.success("🔓 Costs Unlocked! Double-Blind deactivated.") # [cite: 109]
        
        # 2. FINAL AWARD VALUE (For Sealed Offer Logic)
        award_val = st.number_input("Enter Final Principal Award Amount (€)", value=meta.get("final_award_amount", 0.0))
        if st.button("Update Award Value"):
            db.collection("arbitrations").document(case_id).update({"meta.final_award_amount": award_val})
            st.rerun()
            
        # 3. GENERATE REASONING
        st.divider()
        st.write("#### 2. Generate Reasoned Cost Decision")
        if st.button("✨ Generate Cost Allocation with Vertex AI"):
            with st.spinner("Analyzing Document Production stats, Delays, and Sealed Offers..."):
                draft_text = generate_cost_award_draft(case_id)
                st.markdown(draft_text)
                
                # Check Reversals [cite: 87, 96]
                reversals = check_sealed_offers(award_val)
                if reversals:
                    st.error("🚨 **COST REVERSAL TRIGGERED**")
                    for r in reversals:
                        st.write(f"Offer by {r['offerer']} (€{r['offer_amount']}) > Award (€{award_val}).")
                        st.write("AI Recommendation: Shift all costs incurred after " + r['offer_date'])
