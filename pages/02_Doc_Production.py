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

st.title("📂 Phase 3: Document Production Management")

# --- LOAD DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})

# --- ROLE: PARTY VIEW ---
if role in ['claimant', 'respondent']:
    st.write(f"### {role.title()}'s Requests Schedule")
    st.info("Input your document requests below. Objections from the other party should be recorded here when received.")
    
    current_list = doc_prod.get(role, [])
    
    if current_list:
        df = pd.DataFrame(current_list)
    else:
        df = pd.DataFrame(columns=["Request No.", "Description", "Date Requested", "Objection? (Y/N)", "Objection Reason", "Date of Objection"])

    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        column_config={
            "Request No.": st.column_config.NumberColumn(min_value=1, step=1),
            "Date Requested": st.column_config.DateColumn(default=date.today()),
            "Objection? (Y/N)": st.column_config.CheckboxColumn(default=False),
            "Date of Objection": st.column_config.DateColumn()
        },
        use_container_width=True
    )

    if st.button("💾 Save Schedule"):
        cleaned_list = json.loads(edited_df.to_json(orient="records", date_format="iso"))
        doc_prod[role] = cleaned_list
        save_complex_data("doc_prod", doc_prod)
        st.success("Schedule Updated Successfully")

# --- ROLE: ARBITRATOR VIEW ---
elif role == 'arbitrator':
    st.write("### Tribunal Overview")
    
    tab_c, tab_r = st.tabs(["Claimant's Requests", "Respondent's Requests"])
    
    with tab_c:
        c_list = doc_prod.get("claimant", [])
        if c_list:
            df_c = pd.DataFrame(c_list)
            st.dataframe(df_c, use_container_width=True)
            total = len(df_c)
            # Safe access to column
            if "Objection? (Y/N)" in df_c.columns:
                objs = len(df_c[df_c["Objection? (Y/N)"] == True])
                st.metric("Conflict Rate", f"{objs}/{total}", delta=f"{objs/total:.0%} Objected" if total else "0%")
        else:
            st.info("Claimant has not submitted requests yet.")

    with tab_r:
        r_list = doc_prod.get("respondent", [])
        if r_list:
            df_r = pd.DataFrame(r_list)
            st.dataframe(df_r, use_container_width=True)
            total = len(df_r)
            if "Objection? (Y/N)" in df_r.columns:
                objs = len(df_r[df_r["Objection? (Y/N)"] == True])
                st.metric("Conflict Rate", f"{objs}/{total}", delta=f"{objs/total:.0%} Objected" if total else "0%")
        else:
            st.info("Respondent has not submitted requests yet.")
