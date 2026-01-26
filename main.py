import streamlit as st
import pandas as pd
from db import load_responses

st.set_page_config(page_title="PROCEED Dashboard", layout="wide")

# --- AUTHENTICATION ---
USERS = {"lcia": "lcia123", "arbitrator": "arbitrator123", "claimant": "party123", "respondent": "party123"}

if 'user_role' not in st.session_state: st.session_state['user_role'] = None

def login():
    u = st.session_state.get("username", "").strip().lower()
    p = st.session_state.get("password", "").strip()
    if USERS.get(u) == p: st.session_state['user_role'] = u
    else: st.error("Invalid Credentials")

def logout():
    st.session_state['user_role'] = None
    st.rerun()

# --- HELPER: PRETTY TABLE GENERATOR ---
def render_phase1_table():
    P1_MAP = {
        "p1_duration": "1. Target Procedural Timetable",
        "p1_qual": "2. Arbitrator Availability",
        "p1_early": "3. Early Determination Application",
        "p1_days": "4. Est. Hearing Days",
        "p1_block": "5. Hearing Block Reservation",
        "p1_dates": "6. Blackout Dates",
        "p1_format": "7. Admin Conference Format",
        "p1_hearing": "8. Main Hearing Format",
        "p1_data": "9. Data Protocol"
    }
    
    resp = load_responses("phase1")
    c_data = resp.get('claimant', {})
    r_data = resp.get('respondent', {})
    
    if not c_data and not r_data: st.warning("No responses submitted yet."); return

    table_data = []
    
    for key, topic in P1_MAP.items():
        c_raw, r_raw = c_data.get(key, ""), r_data.get(key, "")
        c_com, r_com = c_data.get(f"{key}_comment", ""), r_data.get(f"{k}_comment", "") # Typo fix in get
        
        def clean(t): 
            if "**" in t: 
                extracted = t.split("**")[1].strip()
                if extracted.endswith(":"): extracted = extracted[:-1]
                return extracted
            return t

        c_disp = clean(c_raw)
        r_disp = clean(r_raw)
        
        status = "⏳"
        if c_raw and r_raw: stat = "✅" if c_raw == r_raw else "❌"
        else: stat = "⏳"
        
        if c_com: c_disp += " 💬"
        if r_com: r_disp += " 💬"
        
        if c_raw or r_raw:
            table_data.append({"Match?": stat, "Question": topic, "Claimant": c_disp, "Respondent": r_disp, "_c_com": c_com, "_r_com": r_com})

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(
            df[["Match?", "Question", "Claimant", "Respondent"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Match?": st.column_config.TextColumn("Match?", width="small"),
                "Question": st.column_config.TextColumn("Question", width="medium"),
                "Claimant": st.column_config.TextColumn("Claimant", width="large"),
                "Respondent": st.column_config.TextColumn("Respondent", width="large")
            }
        )
        for row in table_data:
            if row.get("_c_com") or row.get("_r_com"):
                with st.expander(f"💬 Comments: {row['Question']}"):
                    c1, c2 = st.columns(2)
                    if row.get("_c_com"): c1.info(f"**Claimant:** {row['_c_com']}")
                    if row.get("_r_com"): c2.warning(f"**Respondent:** {row['_r_com']}")

# --- LOGIN SCREEN ---
if st.session_state['user_role'] is None:
    st.title("PROCEED | Secure Gateway")
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        with st.container(border=True):
            st.subheader("System Access")
            st.text_input("Username", key="username")
            st.text_input("Password", type="password", key="password")
            if st.button("Log In", type="primary", use_container_width=True): login(); st.rerun()
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    role = st.session_state['user_role']
    st.write(f"User: **{role.upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    
    st.divider()
    st.caption("NAVIGATION")
    
    if role == 'lcia':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 1 Qs")
    elif role == 'arbitrator':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
        st.page_link("pages/02_Doc_Production.py", label="Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="Timeline & Logistics")
        st.page_link("pages/04_Cost_Management.py", label="Cost Management")
    else:
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Fill_Questionnaire.py", label="Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="Timeline & Logistics")
        st.page_link("pages/04_Cost_Management.py", label="Cost Management")

st.title("PROCEED: Arbitration Dashboard")

if role == 'lcia':
    st.info("Logged in as: LCIA Institution")
    with st.container(border=True):
        st.markdown("### 1. Phase 1: Pre-Tribunal Appointment")
        if st.button("Edit Questionnaire"): st.switch_page("pages/00_Edit_Questionnaire.py")
    st.divider()
    st.markdown("### 2. Monitor Responses")
    with st.expander("🔎 View Phase 1 Responses", expanded=True): render_phase1_table()

elif role == 'arbitrator':
    st.info("Logged in as: Arbitral Tribunal")
    with st.expander("📄 Review Pre-Tribunal Questionnaire (Phase 1)", expanded=True):
        render_phase1_table()
    c1, c2, c3 = st.columns(3)
    with c1:
        with st.container(border=True):
            st.markdown("### PO1 Config"); st.write("Configure Qs")
            if st.button("Edit"): st.switch_page("pages/00_Edit_Questionnaire.py")
    with c2:
        with st.container(border=True):
            st.markdown("### PO1 Draft"); st.write("Generate Order")
            if st.button("Open"): st.switch_page("pages/01_Drafting_Engine.py")
    with c3:
        with st.container(border=True):
            st.markdown("### Management"); st.write("Docs, Timeline, Costs")
            if st.button("View Timeline"): st.switch_page("pages/03_Smart_Timeline.py")

elif role in ['claimant', 'respondent']:
    st.info(f"Welcome, Counsel for {role.title()}.")
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### Forms"); st.write("Procedural Questionnaires")
            if st.button("Go"): st.switch_page("pages/00_Fill_Questionnaire.py")
    with c2:
        with st.container(border=True):
            st.markdown("### Case Management"); st.write("Documents, Timeline, Costs")
            if st.button("Open Case File"): st.switch_page("pages/03_Smart_Timeline.py")
