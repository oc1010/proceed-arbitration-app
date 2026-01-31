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
merits_decided = meta.get("merits_decided", False) # [cite: 122]

# --- HELPER: DOUBLE BLIND VISIBILITY ---
def can_view_log(owner_role):
    """
    Double-Blind Interface Logic[cite: 119, 120].
    - Parties see only their own costs.
    - Common costs are visible to all[cite: 121].
    - UNLOCK: After merits decided, unlocks for Arbitrator AND Parties[cite: 127, 128].
    """
    if owner_role == 'common': return True
    if merits_decided: return True # Unlocks for everyone
    if role == owner_role: return True # See own
    return False

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    if st.button("Logout"): st.switch_page("main.py")

st.title("💰 Phase 5: Cost Management")

# --- KPI METRICS ---
my_logs = costs.get(f"{role}_log", []) if role != 'lcia' else []
if my_logs:
    df_metrics = pd.DataFrame(my_logs)
    total_spend = df_metrics['amount'].sum()
    st.metric("My Total Logged Costs", f"€{total_spend:,.2f}")

# --- TABS ---
# Renamed per instructions 
tabs = st.tabs(["📝 Cost Logging", "💸 Payment Requests", "🔒 Sealed Offers", "🤖 AI Final Award"])

# ==============================================================================
# TAB 1: COST LOGGING 
# ==============================================================================
with tabs[0]:
    st.subheader("Cost Logging")
    
    # 1. INPUT FORM (Role Specific)
    with st.expander(f"➕ Log New Expense ({role.title()})", expanded=False):
        with st.form("log_cost"):
            c1, c2 = st.columns(2)
            # [cite: 132] Phase
            phase = c1.selectbox("Phase", ["Phase 1: Initiation", "Phase 2: Written Subs", "Phase 3: Doc Prod", "Phase 4: Hearing"]) 
            
            # [cite: 133, 143] Category
            if role == 'arbitrator':
                # Tribunal categories
                cats = ["Tribunal Fees (Hours)", "Administrative", "Travel", "Drafting"]
                category = c2.selectbox("Category / Hours Spent", cats)
            else:
                # Party categories [cite: 133]
                cats = ["Legal Fees", "Expert Fees", "Transcripts", "e-Bundles", "Tribunal Fees"]
                category = c2.selectbox("Category", cats)
            
            c3, c4 = st.columns(2)
            d_exp = c3.date_input("Date of Expenditure") # [cite: 134, 144]
            amt = c4.number_input("Amount (EUR)", min_value=0.0) # [cite: 135, 145]
            
            # Checkbox to make it a "Common Cost" [cite: 138, 148]
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

    # 2. PRIVATE COST SUMMARY [cite: 136, 146]
    # "Party can see a summary of its own costs"
    st.markdown(f"### 🔐 Private Cost Summary ({role.title()})")
    my_private_data = costs.get(f"{role}_log", [])
    if my_private_data:
        df_p = pd.DataFrame(my_private_data)
        st.dataframe(df_p, use_container_width=True)
    else:
        st.info("No private costs logged yet.")

    # 3. ARBITRATION COST SUMMARY [cite: 137, 138, 147, 148]
    # "Common costs... shall be seen by both parties"
    st.markdown("### 🌍 Arbitration Cost Summary (Common)")
    common_data = costs.get("common_log", [])
    if common_data:
        df_c = pd.DataFrame(common_data)
        st.dataframe(df_c, use_container_width=True)
    else:
        st.caption("No common costs (e.g. e-bundles, venue) logged yet.")

    # 4. OPPOSING PARTY COSTS (BLIND UNTIL MERITS)
    # Only show this section if unlocked or if user is Arb
    if merits_decided or role == 'arbitrator':
        st.divider()
        st.markdown("### 🔓 Opposing Party Costs (Unlocked)")
        
        c_claimant, c_respondent = st.columns(2)
        with c_claimant:
            st.write("**Claimant's Log**")
            if role == 'claimant': 
                st.caption("(Your log above)")
            elif can_view_log('claimant'):
                st.dataframe(pd.DataFrame(costs.get('claimant_log', [])), use_container_width=True)
            else:
                st.warning("🔒 HIDDEN")

        with c_respondent:
            st.write("**Respondent's Log**")
            if role == 'respondent': 
                st.caption("(Your log above)")
            elif can_view_log('respondent'):
                st.dataframe(pd.DataFrame(costs.get('respondent_log', [])), use_container_width=True)
            else:
                st.warning("🔒 HIDDEN")

# ==============================================================================
# TAB 2: PAYMENT REQUESTS [cite: 149]
# ==============================================================================
with tabs[1]:
    st.subheader("Financial Management")
    
    # ARBITRATOR VIEW: REQUEST PAYMENT
    if role == 'arbitrator':
        st.write("#### 📤 Request Payment / Deposit")
        with st.form("req_pay"):
            c1, c2 = st.columns(2)
            #  Specific Deposit Types
            dep_type = c1.selectbox("Deposit Type", [
                "Administrative Fees", 
                "Tribunal Fees", 
                "Hearing Expenses", 
                "Expert / Specialist Fund"
            ])
            p_amt = c2.number_input("Amount Requested (€)", min_value=0.0) # [cite: 150]
            
            c3, c4 = st.columns(2)
            p_due = c3.date_input("Due Date") # [cite: 156]
            payer = c4.radio("Payable By", ["Claimant", "Respondent", "Split 50/50"]) # [cite: 157]
            
            #  Automated Reminders Logic (Checkbox)
            auto_remind = st.checkbox("Set Automated Reminders to Parties", value=True)
            
            if st.form_submit_button("Send Payment Order"):
                req = {
                    "type": dep_type, "amount": p_amt, 
                    "due": str(p_due), "payer": payer, 
                    "status": "Pending", "reminders": auto_remind
                }
                if "payment_requests" not in costs: costs["payment_requests"] = []
                costs["payment_requests"].append(req)
                save_complex_data("costs", costs)
                
                # Trigger Email if reminders on
                if auto_remind:
                    # In real app, this queues a cron job. Here we send immediate notice.
                    msg = f"Payment Order ({dep_type}): €{p_amt} due by {p_due}."
                    send_email_notification(["parties@example.com"], "Payment Order", msg)
                    st.toast("Payment Order Sent & Reminders Active", icon="🔔")
                else:
                    st.success("Payment Order Logged.")
                st.rerun()

    # ALL USERS: VIEW REQUESTS
    st.write("#### 📜 Payment / Deposit Requests")
    reqs = costs.get("payment_requests", [])
    if reqs:
        df_req = pd.DataFrame(reqs)
        st.dataframe(df_req, use_container_width=True)
    else:
        st.info("No active payment requests.")

# ==============================================================================
# TAB 3: SEALED OFFERS (Settlement) [cite: 126]
# ==============================================================================
with tabs[2]:
    st.subheader("✉️ Sealed Settlement Offers")
    st.info("Offers are ENCRYPTED. The Tribunal sees existence but not amount until the Award.")
    
    # UPLOAD (Parties Only)
    if role in ['claimant', 'respondent']:
        with st.form("sealed_offer"):
            offer_amt = st.number_input("Settlement Offer Amount (€)", min_value=0.0)
            offer_doc = st.file_uploader("Upload Formal Offer Letter (PDF)")
            
            if st.form_submit_button("Submit Sealed Offer"):
                entry = {
                    "offerer": role,
                    "amount": offer_amt,
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
            st.write(f"⚠️ **{len(offers)} Sealed Offer(s) Detected**")
            for i, o in enumerate(offers):
                st.markdown(f"**Offer #{i+1}** | Date: {o['date']} | Status: **{o['status']}**")
                if not merits_decided:
                    st.caption("🔒 Content Locked until Merits Decision.")
                else:
                    st.success(f"🔓 REVEALED: €{o['amount']:,.2f} by {o['offerer'].title()}")
        else:
            st.write("No sealed offers on file.")

# ==============================================================================
# TAB 4: AI FINAL AWARD [cite: 123]
# ==============================================================================
with tabs[3]:
    st.subheader("🤖 AI Final Award on Costs")
    
    if role != 'arbitrator':
        st.warning("Only the Tribunal can generate the Final Award.")
        st.stop()
        
    # 1. TRIGGER MERITS DECISION [cite: 127]
    st.write("#### 1. Merits Phase Completion")
    is_decided = st.checkbox("✅ Declare Merits Decision Rendered (Unlocks All Costs)", value=merits_decided)
    
    if is_decided != merits_decided:
        db.collection("arbitrations").document(case_id).update({"meta.merits_decided": is_decided})
        st.rerun()

    if is_decided:
        st.success("🔓 Costs Unlocked! Full visibility enabled.")
        
        # 2. FINAL AWARD VALUE
        award_val = st.number_input("Enter Final Principal Award Amount (€)", value=meta.get("final_award_amount", 0.0))
        if st.button("Update Award Value"):
            db.collection("arbitrations").document(case_id).update({"meta.final_award_amount": award_val})
            st.rerun()
            
        # 3. GENERATE REASONING
        st.divider()
        st.write("#### 2. Generate Cost Allocation Summary")
        st.caption("Combines: Conduct Penalties, Sealed Offers (Reverse Multiplier), and Logs.")
        
        if st.button("✨ Generate with Vertex AI"):
            with st.spinner("Analyzing all logs, offers, and penalties..."):
                draft_text = generate_cost_award_draft(case_id)
                st.markdown(draft_text)
                
                # Check Reversals [cite: 126]
                reversals = check_sealed_offers(award_val)
                if reversals:
                    st.error("🚨 **COST REVERSAL TRIGGERED (Reverse Multiplier)**")
                    for r in reversals:
                        st.write(f"Offer by {r['offerer']} (€{r['offer_amount']}) > Award (€{award_val}).")
                        st.write("AI Recommendation: Shift all costs incurred after " + r['offer_date'])
