import streamlit as st
import pandas as pd
from datetime import date
from db import load_complex_data, save_complex_data
import json

st.set_page_config(page_title="Document Production", layout="wide")
role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

st.title("📂 Phase 3: Document Production Management")

# --- LOAD DATA ---
data = load_complex_data()
doc_prod = data.get("doc_prod", {"claimant": [], "respondent": []})

# --- ROLE: PARTY VIEW ---
if role in ['claimant', 'respondent']:
    st.write(f"### {role.title()}'s Requests Schedule")
    st.info("Input your document requests below. Objections from the other party should be recorded here when received.")
    
    current_list = doc_prod.get(role, [])
    
    # Convert list of dicts to DataFrame for editing
    if current_list:
        df = pd.DataFrame(current_list)
    else:
        df = pd.DataFrame(columns=["Request No.", "Description", "Date Requested", "Objection? (Y/N)", "Objection Reason", "Date of Objection"])

    # Editable Data Table
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
        # Convert back to list of dicts (handle dates serialization)
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
            # Stats
            total = len(df_c)
            # Filter safely
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
