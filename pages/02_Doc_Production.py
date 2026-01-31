import streamlit as st
from db import load_complex_data, save_complex_data, load_full_config

st.set_page_config(page_title="Document Production", layout="wide")

role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    if role == 'arbitrator':
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    st.divider()
    if st.button("Logout"): 
        st.session_state['user_role'] = None
        st.switch_page("main.py")

st.title("📂 Phase 3: Document Production")
st.info("Digital Redfern Schedule: Decisions made here directly impact the Final Cost Allocation (Proportionality Score).")

# --- LOAD DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})
meta = load_full_config().get("meta", {})
threshold = meta.get("cost_settings", {}).get("doc_prod_threshold", 75.0)

# --- SCORECARD METRICS ---
def display_scorecard(target_role):
    reqs = doc_prod.get(target_role, [])
    if not reqs: return
    
    total = len(reqs)
    denied = sum(1 for r in reqs if r.get('status') == 'Denied')
    allowed = sum(1 for r in reqs if r.get('status') == 'Allowed')
    
    ratio = (denied / total) * 100 if total > 0 else 0
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Requests", total)
    c2.metric("✅ Allowed", allowed)
    c3.metric("❌ Denied", denied)
    
    # Visual warning if penalty threshold exceeded [cite: 120]
    color = "inverse" if ratio > threshold else "normal"
    c4.metric("Rejection Rate", f"{ratio:.1f}%", delta_color=color, help=f"Threshold: {threshold}%. If exceeded, cost penalties apply.")

# --- RENDERER ---
def render_redfern(requesting_role, obeying_role):
    st.markdown(f"### 📊 {requesting_role.title()}'s Requests")
    display_scorecard(requesting_role)
    st.divider()
    
    requests = doc_prod.get(requesting_role, [])

    # 1. ADD REQUEST (Requesting Party Only)
    if role == requesting_role:
        with st.expander(f"➕ Add New Request"):
            with st.form(f"add_{requesting_role}"):
                desc = st.text_area("Description")
                rel = st.text_area("Relevance")
                if st.form_submit_button("Submit"):
                    new_id = len(requests) + 1
                    requests.append({
                        "id": new_id, "desc": desc, "relevance": rel,
                        "objection": "", "reply": "", "decision": "", 
                        "status": "Pending"
                    })
                    save_complex_data("doc_prod", doc_prod)
                    st.rerun()

    # 2. LIST REQUESTS
    for i, r in enumerate(requests):
        # Status Color Coding
        status_map = {"Allowed": "green", "Denied": "red", "Pending": "grey", "Objected": "orange"}
        s_color = status_map.get(r.get('status', 'Pending'), "grey")
        
        with st.container(border=True):
            c_head, c_stat = st.columns([5, 1])
            c_head.markdown(f"**Request #{r['id']}**")
            c_stat.markdown(f":{s_color}[**{r.get('status', 'Pending')}**]")
            
            c1, c2 = st.columns(2)
            c1.info(f"**Request:**\n{r['desc']}")
            c2.caption(f"**Relevance:**\n{r['relevance']}")
            
            # OBJECTION (Obeying Party)
            if r['objection']:
                st.warning(f"**🛡️ Objection:** {r['objection']}")
            elif role == obeying_role and r.get('status') == 'Pending':
                with st.form(f"obj_{requesting_role}_{i}"):
                    obj_txt = st.text_area("Raise Objection")
                    if st.form_submit_button("Submit Objection"):
                        r['objection'] = obj_txt; r['status'] = "Objected"
                        save_complex_data("doc_prod", doc_prod); st.rerun()

            # REPLY (Requesting Party)
            if r['reply']:
                st.info(f"**↩️ Reply:** {r['reply']}")
            elif role == requesting_role and r.get('status') == 'Objected':
                 with st.form(f"rep_{requesting_role}_{i}"):
                    rep_txt = st.text_area("Reply to Objection")
                    if st.form_submit_button("Submit Reply"):
                        r['reply'] = rep_txt; r['status'] = "Responded"
                        save_complex_data("doc_prod", doc_prod); st.rerun()

            # DECISION (Arbitrator) [cite: 117]
            if r.get('decision'):
                st.markdown(f"**⚖️ Ruling:** {r['decision']}")
            
            if role == 'arbitrator':
                st.divider()
                st.write("**Tribunal Decision**")
                c_a, c_d = st.columns(2)
                if c_a.button("✅ Allow", key=f"al_{requesting_role}_{i}"):
                    r['status'] = "Allowed"; r['decision'] = "Allowed."
                    save_complex_data("doc_prod", doc_prod); st.rerun()
                    
                if c_d.button("❌ Deny", key=f"de_{requesting_role}_{i}"):
                    r['status'] = "Denied"; r['decision'] = "Denied." # AI counts this
                    save_complex_data("doc_prod", doc_prod); st.rerun()

# --- TABS ---
tab_c, tab_r = st.tabs(["Claimant Requests", "Respondent Requests"])
with tab_c: render_redfern("claimant", "respondent")
with tab_r: render_redfern("respondent", "claimant")
