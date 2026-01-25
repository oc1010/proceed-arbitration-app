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
    # HARDCODED MAP TO ENSURE READABILITY
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
    
    if not c_data and not r_data:
        st.warning("No responses submitted yet.")
        return

    table_data = []
    
    # Iterate through known keys to ensure order
    for key, topic in P1_MAP.items():
        c_raw = c_data.get(key, "")
        r_raw = r_data.get(key, "")
        c_com = c_data.get(f"{key}_comment", "")
        r_com = r_data.get(f"{key}_comment", "")
        
        # Clean Text
        def clean(t): return t.split("**")[1].strip() if "**" in t else t
        c_disp = clean(c_raw)
        r_disp = clean(r_raw)
        
        # Status
        status = "⏳"
        if c_raw and r_raw:
            status = "✅" if c_raw == r_raw else "❌"
        
        # Add icons if comments exist
        if c_com: c_disp += " 💬"
        if r_com: r_disp += " 💬"
        
        if c_raw or r_raw: # Only show rows with data
            table_data.append({"Status": status, "Topic": topic, "Claimant": c_disp, "Respondent": r_disp, "_c_com": c_com, "_r_com": r_com})

    if table_data:
        df = pd.DataFrame(table_data)
        st.dataframe(
            df[["Status", "Topic", "Claimant", "Respondent"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "Status": st.column_config.TextColumn("Stat", width="small"),
                "Topic": st.column_config.TextColumn("Question", width="medium"),
                "Claimant": st.column_config.TextColumn("Claimant", width="large"),
                "Respondent": st.column_config.TextColumn("Respondent", width="large")
            }
        )
        
        # COMMENTS SECTION
        comments_found = False
        for row in table_data:
            if row["_c_com"] or row["_r_com"]:
                comments_found = True
                with st.expander(f"💬 Comments: {row['Topic']}"):
                    c1, c2 = st.columns(2)
                    if row["_c_com"]: c1.info(f"**Claimant:** {row['_c_com']}")
                    if row["_r_com"]: c2.warning(f"**Respondent:** {row['_r_com']}")
        
        if not comments_found:
            st.caption("No additional comments provided.")

# --- LOGIN UI ---
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
    if role == 'lcia':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 1 Qs")
    elif role == 'arbitrator':
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    else:
        st.page_link("main.py", label="Home")
        st.page_link("pages/00_Fill_Questionnaire.py", label="Fill Questionnaires")

# --- DASHBOARD CONTENT ---
st.title("PROCEED: Arbitration Dashboard")

if role == 'lcia':
    st.info("Logged in as: LCIA Institution")
    with st.container(border=True):
        st.markdown("### 1. Phase 1: Pre-Tribunal Appointment")
        if st.button("Edit Questionnaire"): st.switch_page("pages/00_Edit_Questionnaire.py")
    st.divider()
    st.markdown("### 2. Monitor Responses")
    with st.expander("🔎 View Phase 1 Responses", expanded=True):
        render_phase1_table()

elif role == 'arbitrator':
    st.info("Logged in as: Arbitral Tribunal")
    with st.expander("📄 Review Pre-Tribunal Questionnaire (Phase 1)", expanded=True):
        render_phase1_table()
    
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        with st.container(border=True):
            st.markdown("### Phase 2: Pre-Hearing")
            if st.button("Edit Phase 2"): st.switch_page("pages/00_Edit_Questionnaire.py")
    with c2:
        with st.container(border=True):
            st.markdown("### Drafting Engine")
            if st.button("Open Engine"): st.switch_page("pages/01_Drafting_Engine.py")

elif role in ['claimant', 'respondent']:
    st.info(f"Welcome, Counsel for {role.title()}.")
    with st.container(border=True):
        st.markdown("#### Procedural Questionnaires")
        if st.button("Go to Questionnaires", type="primary"): st.switch_page("pages/00_Fill_Questionnaire.py")
