import streamlit as st
import pandas as pd
from db import load_complex_data, save_complex_data, upload_file_to_cloud, load_full_config

st.set_page_config(page_title="Document Production", layout="wide")

# --- AUTHENTICATION ---
role = st.session_state.get('user_role')
if not role: 
    st.error("Access Denied"); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    if role == 'arbitrator':
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Procedural Timetable")
        st.page_link("pages/02_Doc_Production.py", label="📂 Document Production")

# --- LOAD SETTINGS & DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})
meta = load_full_config().get('meta', {})
threshold = meta.get('cost_settings', {}).get('doc_prod_threshold', 75.0) # 

st.title("📂 Phase 3: Document Production (Digital Redfern)")
st.info("This module replaces the Redfern Schedule. Requests, Objections, and Tribunal Decisions are tracked here to calculate Cost Allocation scores.")

# --- HELPER: METRICS DASHBOARD [cite: 26, 59] ---
def display_metrics(target_role):
    """
    Displays the 'Proportionality Score' (Rejection Rate) for the target party.
    """
    requests = doc_prod.get(target_role, [])
    if not requests:
        return
    
    total = len(requests)
    # Count decisions
    allowed = sum(1 for r in requests if r.get('status') == 'Allowed')
    denied = sum(1 for r in requests if r.get('status') == 'Denied')
    pending = total - allowed - denied
    
    # Calculate Rejection Ratio 
    # Denied / (Allowed + Denied) or Denied / Total? Usually Total resolved requests.
    resolved = allowed + denied
    if resolved > 0:
        ratio = (denied / total) * 100
    else:
        ratio = 0.0
        
    # Display Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", total)
    c2.metric("✅ Allowed", allowed)
    c3.metric("❌ Rejected", denied)
    
    # Color logic for Threshold 
    ratio_color = "normal"
    if ratio > threshold: ratio_color = "inverse" # Red alert if high
    
    c4.metric("Rejection Rate", f"{ratio:.1f}%", help=f"Threshold: {threshold}%. If exceeded, 100% costs borne by requester.", delta_color=ratio_color)
    
    if ratio > threshold:
        st.error(f"⚠️ Warning: {target_role.title()}'s rejection rate ({ratio:.1f}%) exceeds the {threshold}% threshold. Cost penalties may apply.")

# --- MAIN RENDERER ---
def render_redfern_schedule(requesting_role, obeying_role):
    """
    Renders the full Request -> Objection -> Reply -> Decision workflow.
    """
    # 1. SHOW SCORECARD
    st.markdown(f"### 📊 {requesting_role.title()}'s Proportionality Score")
    display_metrics(requesting_role)
    st.divider()

    requests = doc_prod.get(requesting_role, [])
    
    # 2. ADD NEW REQUEST (Only Requesting Party)
    if role == requesting_role:
        with st.expander(f"➕ Draft New Request (No. {len(requests) + 1})", expanded=False):
            with st.form(f"add_req_{requesting_role}"):
                c_desc, c_rel = st.columns(2)
                desc = c_desc.text_area("1. Description of Documents", height=100, help="Be specific and narrow.")
                rel = c_rel.text_area("2. Relevance & Materiality", height=100, help="Reference specific paragraphs in Pleadings.")
                
                if st.form_submit_button("Submit Request"):
                    new_id = len(requests) + 1
                    requests.append({
                        "id": new_id,
                        "desc": desc,
                        "relevance": rel,
                        "objection": "",
                        "reply": "",
                        "decision": "",
                        "status": "Pending", # Pending, Objected, Responded, Allowed, Denied
                        "produced": False
                    })
                    save_complex_data("doc_prod", doc_prod)
                    st.success("Request Submitted.")
                    st.rerun()
    
    # 3. RENDER THE LIST (The "Redfern" Rows)
    if not requests:
        st.info(f"No requests submitted by {requesting_role.title()} yet.")
        return

    for i, r in enumerate(requests):
        # VISUAL CONTAINER FOR EACH REQUEST
        # Color border based on Status
        status_colors = {
            "Pending": "grey", "Objected": "orange", "Responded": "blue", 
            "Allowed": "green", "Denied": "red"
        }
        curr_color = status_colors.get(r['status'], "grey")
        
        with st.container(border=True):
            # HEADER: ID - Status
            c_head_1, c_head_2 = st.columns([4, 1])
            c_head_1.markdown(f"**Request No. {r['id']}**")
            c_head_2.caption(f"Status: :{curr_color}[**{r['status']}**]")
            
            # COLUMNS: Description | Relevance
            c1, c2 = st.columns(2)
            c1.info(f"**Description:**\n{r['desc']}")
            c2.info(f"**Relevance:**\n{r['relevance']}")
            
            # --- OBJECTION WORKFLOW (Obeying Party) ---
            if r['objection']:
                st.warning(f"**🛡️ Objection ({obeying_role.title()}):**\n{r['objection']}")
            
            if role == obeying_role and not r['objection'] and r['status'] == "Pending":
                with st.form(f"obj_form_{requesting_role}_{i}"):
                    obj_text = st.text_area("Raise Objection (Reasons)", height=100)
                    cols = st.columns([1, 1])
                    if cols[0].form_submit_button("Submit Objection"):
                        r['objection'] = obj_text
                        r['status'] = "Objected"
                        save_complex_data("doc_prod", doc_prod)
                        st.rerun()
                    if cols[1].form_submit_button("No Objection (Agree to Produce)"):
                        r['status'] = "Allowed" # Treat as allowed if agreed
                        r['decision'] = "Voluntary Production"
                        save_complex_data("doc_prod", doc_prod)
                        st.rerun()

            # --- REPLY WORKFLOW (Requesting Party) ---
            if r['objection'] and r['reply']:
                st.markdown(f"**↩️ Reply to Objection ({requesting_role.title()}):**\n{r['reply']}")

            if role == requesting_role and r['status'] == "Objected":
                with st.form(f"reply_form_{requesting_role}_{i}"):
                    rep_text = st.text_area("Reply to Objection", height=100)
                    if st.form_submit_button("Submit Reply"):
                        r['reply'] = rep_text
                        r['status'] = "Responded" # Ready for Tribunal
                        save_complex_data("doc_prod", doc_prod)
                        st.rerun()

            # --- DECISION WORKFLOW (Arbitrator) ---
            # Visible if status is Responded (Dispute) OR Arbitrator wants to intervene
            if r['decision']:
                icon = "✅" if r['status'] == "Allowed" else "❌"
                st.success(f"**⚖️ Tribunal Decision:** {icon} {r['status']}\n\n{r['decision']}")
            
            if role == 'arbitrator' and r['status'] in ["Objected", "Responded", "Pending"]:
                st.divider()
                st.write(" **Tribunal Ruling:**")
                with st.form(f"ruling_form_{i}"):
                    reason = st.text_area("Reasoning for Decision")
                    c_a, c_d = st.columns(2)
                    
                    # Buttons
                    allow = c_a.form_submit_button("✅ ALLOW Request")
                    deny = c_d.form_submit_button("❌ DENY Request")
                    
                    if allow:
                        r['status'] = "Allowed"
                        r['decision'] = reason if reason else "Allowed."
                        save_complex_data("doc_prod", doc_prod)
                        st.rerun()
                        
                    if deny:
                        r['status'] = "Denied"
                        r['decision'] = reason if reason else "Denied."
                        save_complex_data("doc_prod", doc_prod)
                        st.rerun()

# --- TABS FOR CLAIMANT / RESPONDENT LISTS ---
tab_c, tab_r = st.tabs(["📄 Requests by Claimant", "📄 Requests by Respondent"])

with tab_c:
    render_redfern_schedule("claimant", "respondent")

with tab_r:
    render_redfern_schedule("respondent", "claimant")
