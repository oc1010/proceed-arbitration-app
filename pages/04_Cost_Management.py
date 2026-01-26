import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data, load_responses

st.set_page_config(page_title="Cost Management", layout="wide")
role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

st.title("💰 Phase 5: Cost Management")

# --- LOAD DATA ---
data = load_complex_data()
costs = data.get("costs", {
    "claimant_log": [], "respondent_log": [], 
    "tribunal_ledger": {"deposits": 0, "balance": 0, "history": []}, 
    "app_tagging": []
})

# --- HELPER: NOTIFY ---
def notify_parties(subject, body):
    p2 = load_responses("phase2")
    c_email = p2.get('claimant', {}).get('contact_email', '-')
    r_email = p2.get('respondent', {}).get('contact_email', '-')
    st.toast(f"📧 Notification sent to {c_email}, {r_email}")

# --- TABS ---
tab_sub, tab_led, tab_tag = st.tabs(["🧾 Cost Submissions", "⚖️ Tribunal Ledger", "🏷️ Application Tagging"])

# --- 1. COST SUBMISSIONS (Parties) ---
with tab_sub:
    if role in ['claimant', 'respondent']:
        st.subheader("Submit Costs")
        with st.form("cost_add"):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Description (e.g. Legal Fees, Expert)")
            amt = c2.number_input("Amount (EUR)", min_value=0.0)
            d_inc = c1.date_input("Date Incurred")
            # PDF Upload Simulation
            pdf = c2.file_uploader("Upload Invoice (PDF)")
            final_sub = st.checkbox("This is my FINAL Cost Submission")
            
            if st.form_submit_button("Add Cost Item"):
                key = f"{role}_log"
                entry = {
                    "date": str(d_inc), "desc": desc, "amount": amt, 
                    "file": pdf.name if pdf else "No file", 
                    "submitted_on": str(date.today()),
                    "is_final": final_sub
                }
                costs[key].append(entry)
                data['costs'] = costs
                save_complex_data("costs", costs)
                st.success("Cost item recorded.")
                st.rerun()
    
    # View for Everyone
    st.divider()
    c_log = costs.get("claimant_log", [])
    r_log = costs.get("respondent_log", [])
    
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Claimant's Costs")
        if c_log: 
            st.dataframe(pd.DataFrame(c_log))
            if any(x.get('is_final') for x in c_log): st.warning("⚠️ Final Submission Received")
    with c2:
        st.write("#### Respondent's Costs")
        if r_log: 
            st.dataframe(pd.DataFrame(r_log))
            if any(x.get('is_final') for x in r_log): st.warning("⚠️ Final Submission Received")

# --- 2. TRIBUNAL LEDGER (Advance Balances) ---
with tab_led:
    st.subheader("Tribunal Advances")
    ledger = costs.get("tribunal_ledger", {"deposits": 0, "balance": 0, "history": []})
    
    # Metrics
    m1, m2 = st.columns(2)
    m1.metric("Total Deposits", f"€{ledger['deposits']:,.2f}")
    m2.metric("Current Balance", f"€{ledger['balance']:,.2f}", delta_color="inverse" if ledger['balance'] < 5000 else "normal")
    
    if role == 'arbitrator':
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            with st.form("add_dep"):
                dep_amt = st.number_input("Record New Deposit (€)", min_value=0.0)
                if st.form_submit_button("Add Deposit"):
                    ledger['deposits'] += dep_amt
                    ledger['balance'] += dep_amt
                    ledger['history'].append(f"Deposit: +{dep_amt} ({date.today()})")
                    data['costs']['tribunal_ledger'] = ledger
                    save_complex_data("costs", costs)
                    st.rerun()
        
        with c2:
            if st.button("⚠️ Retrigger Advance (Request Top-Up)"):
                notify_parties("Advance Payment Request", "The Tribunal requests a further advance on costs due to low balance.")
                st.success("Request sent to parties.")

# --- 3. APPLICATION TAGGING (Arbitrator) ---
with tab_tag:
    st.subheader("Application Tagging & Allocation")
    st.caption("Track time/effort on specific applications for final cost allocation.")
    
    if role == 'arbitrator':
        with st.form("tagging"):
            c1, c2, c3 = st.columns(3)
            task = c1.text_input("Task/Application Name")
            hours = c2.number_input("Tribunal Hours Spent", min_value=0.1)
            allocation = c3.selectbox("Tentative Allocation", ["Reserved", "Claimant to Bear", "Respondent to Bear"])
            reason = st.text_area("Reasoning (e.g. Frivolous application)")
            
            if st.form_submit_button("Log Task"):
                entry = {"task": task, "hours": hours, "cost_est": hours * 500, "allocation": allocation, "reason": reason}
                costs['app_tagging'].append(entry)
                data['costs'] = costs
                save_complex_data("costs", costs)
                st.success("Task logged.")
                st.rerun()
                
    # View Log
    tags = costs.get("app_tagging", [])
    if tags:
        df_tags = pd.DataFrame(tags)
        st.dataframe(df_tags, use_container_width=True)
        
        # Summary for Award
        st.markdown("#### Cost Allocation Summary")
        summary = df_tags.groupby("allocation")["cost_est"].sum().reset_index()
        st.bar_chart(summary, x="allocation", y="cost_est")
    else:
        st.info("No tasks logged yet.")
