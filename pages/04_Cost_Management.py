import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data, load_responses, send_email_notification

st.set_page_config(page_title="Cost Management", layout="wide")

role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR (Persistent & Complete) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    
    if role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 PO1 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    elif role in ['claimant', 'respondent']:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
        
    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
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

# --- HELPER ---
def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- TAB LOGIC (Role Based) ---
# Create tab list dynamically based on role
tab_names = ["🧾 Ongoing Costs", "🏁 Final Submission", "⚖️ Tribunal Ledger"]
if role == 'arbitrator':
    tab_names.append("🏷️ App Tagging") # Only for Arbitrator

tabs = st.tabs(tab_names)

# --- TAB 1: ONGOING COSTS ---
with tabs[0]:
    st.subheader("Interim Cost Tracking")
    if role in ['claimant', 'respondent']:
        with st.form("cost_add"):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Description (e.g. Legal Fees, Expert)")
            amt = c2.number_input("Amount (EUR)", min_value=0.0)
            d_inc = c1.date_input("Date Incurred")
            pdf = c2.file_uploader("Upload Invoice (PDF)")
            
            if st.form_submit_button("Add Cost Item"):
                key = f"{role}_log"
                entry = {
                    "date": str(d_inc), "desc": desc, "amount": amt, 
                    "file": pdf.name if pdf else "No file", 
                    "submitted_on": str(date.today())
                }
                costs[key].append(entry)
                save_complex_data("costs", costs)
                st.success("Cost item recorded.")
                st.rerun()
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.write("#### Claimant's Running Costs")
        if costs["claimant_log"]: st.dataframe(pd.DataFrame(costs["claimant_log"]), use_container_width=True)
    with c2:
        st.write("#### Respondent's Running Costs")
        if costs["respondent_log"]: st.dataframe(pd.DataFrame(costs["respondent_log"]), use_container_width=True)

# --- TAB 2: FINAL SUBMISSION ---
with tabs[1]:
    st.subheader("Final Statement of Costs")
    st.info("This section is for the formal Cost Submission at the end of proceedings.")
    
    if role in ['claimant', 'respondent']:
        with st.form("final_sub_form"):
            total_claimed = st.number_input("Total Costs Claimed (EUR)", min_value=0.0)
            final_pdf = st.file_uploader("Upload Final Cost Schedule (PDF/Excel)")
            
            if st.form_submit_button("Submit Final Costs"):
                sub_entry = {
                    "party": role,
                    "date": str(date.today()),
                    "total": total_claimed,
                    "file": final_pdf.name if final_pdf else "No file"
                }
                if "final_submissions" not in costs: costs["final_submissions"] = []
                costs["final_submissions"].append(sub_entry)
                save_complex_data("costs", costs)
                
                # Notify
                send_email_notification(get_party_emails(), "Final Costs Submitted", f"{role.title()} has submitted their Final Statement of Costs.")
                st.success("Final submission received.")
    
    # View Final Submissions
    if "final_submissions" in costs and costs["final_submissions"]:
        st.write("### Received Submissions")
        st.dataframe(pd.DataFrame(costs["final_submissions"]), use_container_width=True)
    else:
        st.caption("No final submissions yet.")

# --- TAB 3: TRIBUNAL LEDGER ---
with tabs[2]:
    st.subheader("Tribunal Advances")
    ledger = costs.get("tribunal_ledger", {"deposits": 0, "balance": 0, "history": []})
    
    m1, m2 = st.columns(2)
    m1.metric("Total Deposits", f"€{ledger['deposits']:,.2f}")
    m2.metric("Current Balance", f"€{ledger['balance']:,.2f}")
    
    if role == 'arbitrator':
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            with st.form("add_dep"):
                dep_amt = st.number_input("Record Deposit (€)", min_value=0.0)
                if st.form_submit_button("Add Funds"):
                    ledger['deposits'] += dep_amt
                    ledger['balance'] += dep_amt
                    ledger['history'].append(f"Deposit: +{dep_amt} ({date.today()})")
                    costs['tribunal_ledger'] = ledger
                    save_complex_data("costs", costs)
                    st.rerun()
        with c2:
            st.write("### Actions")
            if st.button("⚠️ Request Advance Top-Up"):
                send_email_notification(get_party_emails(), "Advance Payment Request", "The Tribunal requests a further advance on costs.")
                st.success("Request sent to parties.")

# --- TAB 4: APP TAGGING (ARBITRATOR ONLY) ---
if role == 'arbitrator':
    with tabs[3]:
        st.subheader("Application Tagging & Allocation")
        st.caption("Internal tool for Arbitrator to track time spent on specific applications.")
        
        with st.form("tagging"):
            c1, c2, c3 = st.columns(3)
            task = c1.text_input("Application Name")
            hours = c2.number_input("Hours Spent", min_value=0.1)
            allocation = c3.selectbox("Allocation", ["Reserved", "Claimant to Bear", "Respondent to Bear"])
            
            if st.form_submit_button("Log Application"):
                entry = {"task": task, "hours": hours, "allocation": allocation}
                costs['app_tagging'].append(entry)
                save_complex_data("costs", costs)
                st.success("Logged.")
                st.rerun()
        
        if costs["app_tagging"]:
            st.dataframe(pd.DataFrame(costs["app_tagging"]), use_container_width=True)
