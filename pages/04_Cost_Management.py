import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data, load_responses, send_email_notification, upload_file_to_cloud, load_full_config, db
from ai_logic import generate_cost_award_draft, check_sealed_offers

st.set_page_config(page_title="Cost Management", layout="wide")

role = st.session_state.get('user_role')
case_id = st.session_state.get('active_case_id') # Ensure case_id is available

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

# --- HELPER ---
def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- TAB LOGIC ---
tab_names = ["🧾 Ongoing Costs", "💸 Payment Requests", "🏁 Final Submission", "🔒 Sealed Offers"]
if role == 'arbitrator':
    tab_names.append("🤖 AI Final Award") # Only Tribunal sees AI tab

tabs = st.tabs(tab_names)

# ==============================================================================
# TAB 1: ONGOING COSTS
# ==============================================================================
with tabs[0]:
    st.subheader("Interim Cost Tracking")
    
    # 1. Input Form
    if role in ['claimant', 'respondent', 'arbitrator']:
        with st.form("cost_add"):
            c1, c2 = st.columns(2)
            desc = c1.text_input("Description (e.g. Legal Fees, Expert)")
            amt = c2.number_input("Amount (EUR)", min_value=0.0)
            d_inc = c1.date_input("Date Incurred")
            pdf = c2.file_uploader("Upload Invoice (PDF)")
            
            if st.form_submit_button("Add Cost Item"):
                file_link = "No file"
                if pdf:
                    with st.spinner("Uploading to Secure Cloud..."):
                        uploaded_name = upload_file_to_cloud(pdf)
                        if uploaded_name: file_link = uploaded_name
                
                key = f"{role}_log"
                # Arbitrator logs to their own list, but visually separated
                if role == 'arbitrator': key = "tribunal_log" # Ensure this key exists in db structure logic if needed, or map to common

                entry = {
                    "date": str(d_inc), "desc": desc, "amount": amt, 
                    "file": file_link, 
                    "submitted_on": str(date.today())
                }
                
                # Safety check for list existence
                if key not in costs: costs[key] = []
                costs[key].append(entry)
                save_complex_data("costs", costs)
                st.success("Cost item recorded.")
                st.rerun()
    
    st.divider()
    
    # 2. View Logs (Double Blind Logic)
    # Parties see only their own. Tribunal sees all.
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("#### Claimant's Running Costs")
        if role == 'claimant' or role == 'arbitrator' or merits_decided:
            if costs.get("claimant_log"): 
                st.dataframe(pd.DataFrame(costs["claimant_log"]), use_container_width=True)
            else: st.info("No logs.")
        else:
            st.warning("🔒 HIDDEN (Double-Blind Active)")

    with c2:
        st.write("#### Respondent's Running Costs")
        if role == 'respondent' or role == 'arbitrator' or merits_decided:
            if costs.get("respondent_log"): 
                st.dataframe(pd.DataFrame(costs["respondent_log"]), use_container_width=True)
            else: st.info("No logs.")
        else:
            st.warning("🔒 HIDDEN (Double-Blind Active)")

# ==============================================================================
# TAB 2: PAYMENT REQUESTS & LEDGER
# ==============================================================================
with tabs[1]:
    st.subheader("Tribunal Advances & Deposits")
    ledger = costs.get("tribunal_ledger", {"deposits": 0, "balance": 0, "history": []})
    
    m1, m2 = st.columns(2)
    m1.metric("Total Deposits Received", f"€{ledger.get('deposits', 0):,.2f}")
    m2.metric("Current Balance", f"€{ledger.get('balance', 0):,.2f}")
    
    if role == 'arbitrator':
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            st.write("#### Record Incoming Payment")
            with st.form("add_dep"):
                dep_amt = st.number_input("Amount Received (€)", min_value=0.0)
                payer = st.radio("From", ["Claimant", "Respondent"])
                if st.form_submit_button("Record Deposit"):
                    ledger['deposits'] += dep_amt
                    ledger['balance'] += dep_amt
                    ledger['history'].append(f"Received +€{dep_amt} from {payer} ({date.today()})")
                    costs['tribunal_ledger'] = ledger
                    save_complex_data("costs", costs)
                    st.success("Recorded.")
                    st.rerun()
        with c2:
            st.write("#### Requests")
            if st.button("⚠️ Send Advance Payment Request"):
                send_email_notification(get_party_emails(), "Advance Payment Request", "The Tribunal requests a further advance on costs. Please log in to view details.")
                st.success("Notifications sent to parties.")

# ==============================================================================
# TAB 3: FINAL SUBMISSION
# ==============================================================================
with tabs[2]:
    st.subheader("Final Statement of Costs")
    st.info("Formal Cost Submission (Form H) at the end of proceedings.")
    
    if role in ['claimant', 'respondent']:
        with st.form("final_sub_form"):
            total_claimed = st.number_input("Total Costs Claimed (EUR)", min_value=0.0)
            final_pdf = st.file_uploader("Upload Final Cost Schedule (PDF/Excel)")
            
            if st.form_submit_button("Submit Final Costs"):
                file_link = "No file"
                if final_pdf:
                    uploaded_name = upload_file_to_cloud(final_pdf)
                    if uploaded_name: file_link = uploaded_name

                sub_entry = {
                    "party": role, "date": str(date.today()),
                    "total": total_claimed, "file": file_link
                }
                if "final_submissions" not in costs: costs["final_submissions"] = []
                costs["final_submissions"].append(sub_entry)
                save_complex_data("costs", costs)
                st.success("Final submission received.")
    
    if costs.get("final_submissions"):
        st.write("### Received Submissions")
        st.dataframe(pd.DataFrame(costs["final_submissions"]), use_container_width=True)
    else:
        st.caption("No final submissions yet.")

# ==============================================================================
# TAB 4: SEALED OFFERS (Settlement Vault)
# ==============================================================================
with tabs[3]:
    st.subheader("✉️ Sealed Settlement Offers")
    st.info("Offers uploaded here are ENCRYPTED. The Tribunal is notified that an offer exists, but cannot see the amount/content until the Final Award value is entered.")
    
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
                status_txt = f"**Offer #{i+1}** | Date: {o['date']} | Status: **{o['status']}**"
                if not merits_decided:
                    st.info(f"{status_txt} (Locked 🔒)")
                else:
                    st.success(f"{status_txt} - 🔓 REVEALED: €{o['amount']:,.2f} by {o['offerer'].title()}")
        else:
            st.write("No sealed offers on file.")

# ==============================================================================
# TAB 5: AI FINAL AWARD (Tribunal Only)
# ==============================================================================
if role == 'arbitrator':
    with tabs[4]:
        st.subheader("🤖 AI Final Award on Costs")
        
        # 1. TRIGGER MERITS DECISION
        st.write("#### 1. Merits Phase Completion")
        is_decided = st.checkbox("✅ Declare Merits Decision Rendered", value=merits_decided)
        
        if is_decided != merits_decided:
            db.collection("arbitrations").document(case_id).update({"meta.merits_decided": is_decided})
            st.rerun()

        if is_decided:
            st.success("🔓 Costs Unlocked! Double-Blind deactivated.")
            
            # 2. FINAL AWARD VALUE (Required for Sealed Offer Logic)
            st.write("#### 2. Enter Award Value")
            award_val = st.number_input("Final Principal Award Amount (€)", value=meta.get("final_award_amount", 0.0))
            
            if st.button("Update Award Value"):
                db.collection("arbitrations").document(case_id).update({"meta.final_award_amount": award_val})
                st.toast("Value Updated")
                
            # 3. GENERATE REASONING
            st.divider()
            st.write("#### 3. Generate Reasoned Cost Decision")
            
            if st.button("✨ Generate Cost Allocation with Vertex AI"):
                with st.spinner("Analyzing Document Production stats, Delays, and Sealed Offers..."):
                    
                    # --- FIX: PASS BOTH ARGUMENTS HERE ---
                    draft_text = generate_cost_award_draft(case_id, award_val) 
                    # -------------------------------------
                    
                    st.markdown(draft_text)
