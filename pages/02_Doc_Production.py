import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data
import json

st.set_page_config(page_title="Document Production", layout="wide")

role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR (PERSISTENT) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 PO1 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    else:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")

    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
        st.switch_page("main.py")

st.title("📂 Phase 3: Document Production Phase")

# --- LOAD DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})

# --- CONFIGURATION OPTIONS (Matched to Screenshot) ---
CATEGORIES = [
    "(a) General Contractual Documents",
    "(b) Technical & Project-Specific",
    "(c) Financial Documents",
    "(d) Company and Employee Data",
    "(e) Electronic Metadata",
    "(f) Other Documents"
]

URGENCY = ["(a) Low", "(b) Medium", "(c) High [Tribunal Priority]"]
YES_NO = ["(a) Yes", "(b) No"]
DETERMINATION = ["1. Allowed", "2. Allowed in Part", "3. Denied", "4. Reserved"]
COMPLIANCE = ["1. Pending", "2. Documents Produced", "3. Documents Not Produced"]

# --- HELPER: COLUMN CONFIGURATION ---
# This ensures the Data Editor looks exactly like the requirements
COLUMN_CONFIG = {
    "req_no": st.column_config.TextColumn("1.1 Req No.", help="Request Number (Free Text)", width="small"),
    "category": st.column_config.SelectboxColumn("1.2 Category", options=CATEGORIES, width="medium"),
    "date_req": st.column_config.DateColumn("1.3 Date of Request", width="small"),
    "urgency": st.column_config.SelectboxColumn("1.4 Urgency", options=URGENCY, width="small"),
    
    "objection": st.column_config.SelectboxColumn("2.1 Objection", options=YES_NO, width="small"),
    "date_obj": st.column_config.DateColumn("2.2 Date Obj", width="small"),
    "reply_obj": st.column_config.SelectboxColumn("2.3 Reply to Obj", options=YES_NO, width="small"),
    "date_reply": st.column_config.DateColumn("2.4 Date Reply", width="small"),
    
    "tribunal_det": st.column_config.SelectboxColumn("3.1 Determination", options=DETERMINATION, width="medium"),
    "date_det": st.column_config.DateColumn("3.2 Date Det.", width="small"),
    
    "compliance": st.column_config.SelectboxColumn("4. Compliance", options=COMPLIANCE, width="medium")
}

# --- HELPER: RENDER TABLE ---
def render_redfern_tab(party_key, label):
    st.markdown(f"### {label}")
    
    # 1. Prepare Data
    current_data = doc_prod.get(party_key, [])
    
    # define schema order explicitly
    schema = [
        "req_no", "category", "date_req", "urgency", 
        "objection", "date_obj", "reply_obj", "date_reply",
        "tribunal_det", "date_det", "compliance"
    ]
    
    if current_data:
        df = pd.DataFrame(current_data)
        # Ensure all columns exist even if data is partial
        for col in schema:
            if col not in df.columns:
                df[col] = None
        # Reorder
        df = df[schema]
    else:
        df = pd.DataFrame(columns=schema)

    # 2. Instructions based on Role
    if role == party_key:
        st.info(f"📝 **Instruction:** As {role.title()}, please fill columns 1.1 - 1.4. You may also fill 2.3 (Reply to Obj).")
    elif role == 'arbitrator':
        st.warning("⚖️ **Tribunal Instruction:** Review Requests and Objections. Fill columns 3.1 - 3.2 (Determination).")
    else:
        st.info(f"👀 **Instruction:** Review {party_key.title()}'s requests. If you object, fill columns 2.1 - 2.2.")

    # 3. Data Editor
    edited_df = st.data_editor(
        df,
        column_config=COLUMN_CONFIG,
        use_container_width=True,
        num_rows="dynamic",
        key=f"editor_{party_key}",
        hide_index=True
    )

    # 4. Save Logic
    if st.button(f"💾 Save {label}", key=f"save_{party_key}"):
        # Convert date objects to strings for JSON serialization
        cleaned_json = json.loads(edited_df.to_json(orient="records", date_format="iso"))
        doc_prod[party_key] = cleaned_json
        save_complex_data("doc_prod", doc_prod)
        st.success(f"{label} updated successfully.")

# --- MAIN UI ---
# As per screenshot: Main tab "Document Production", Sub-tabs for Requests
st.write("Manage Document Requests, Objections, and Tribunal Determinations.")

# Create the tabs
tab_c, tab_r = st.tabs(["(1) Claimant's Requests", "(2) Respondent's Requests"])

with tab_c:
    render_redfern_tab("claimant", "Claimant's Request Schedule")

with tab_r:
    render_redfern_tab("respondent", "Respondent's Request Schedule")
