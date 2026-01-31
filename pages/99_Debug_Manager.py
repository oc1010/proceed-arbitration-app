import streamlit as st
import pandas as pd
from db import db

# --- SAFETY WARNING ---
st.set_page_config(page_title="DEBUG TOOL", layout="wide", page_icon="🐞")
st.markdown("""
<style>
    .stApp {border: 5px solid #ff4b4b;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

st.error("⚠️ **DEVELOPER GOD MODE ACTIVE** ⚠️")
st.warning("DELETE this file (`pages/99_Debug_Manager.py`) before releasing the app to judges.")

st.title("🐞 Database Inspector")
st.info("This tool bypasses all security. Use it to view Case IDs and PINs.")

# --- 1. FETCH ALL DATA ---
if st.button("🔄 Refresh Data"):
    st.rerun()

if not db:
    st.error("Database not connected.")
    st.stop()

# Fetch all documents from Firestore
docs = db.collection("arbitrations").stream()

table_data = []
full_data_map = {}

for doc in docs:
    d = doc.to_dict()
    meta = d.get('meta', {})
    
    # safe get
    cid = meta.get('case_id', 'UNKNOWN')
    pin = meta.get('access_pin', 'N/A')
    name = meta.get('case_name', 'Untitled')
    status = meta.get('status', 'Unknown')
    
    parties = meta.get('parties', {})
    claimant = parties.get('claimant', '-')
    respondent = parties.get('respondent', '-')
    
    table_data.append({
        "CASE ID (Login User)": cid,
        "PIN (Login Pass)": pin,
        "Case Name": name,
        "Status": status,
        "Claimant Email": claimant,
        "Respondent Email": respondent
    })
    full_data_map[cid] = d

# --- 2. DISPLAY CREDENTIALS TABLE ---
if table_data:
    df = pd.DataFrame(table_data)
    st.subheader("🔑 All Active Credentials")
    st.dataframe(
        df, 
        use_container_width=True, 
        column_config={
            "CASE ID (Login User)": st.column_config.TextColumn("Case ID", help="Copy this to log in"),
            "PIN (Login Pass)": st.column_config.TextColumn("PIN", help="Password for parties"),
        }
    )
else:
    st.warning("Database is empty. Go to Home -> LCIA Login to create a case.")

st.divider()

# --- 3. DANGER ZONE: DELETE CASES ---
st.subheader("🗑️ Delete/Reset Cases")
col1, col2 = st.columns([3, 1])

with col1:
    to_delete = st.selectbox("Select Case to DELETE permanently:", [d['CASE ID (Login User)'] for d in table_data], key="del_select")

with col2:
    st.write("##") # Spacer
    if st.button("❌ DELETE CASE", type="primary"):
        if to_delete:
            db.collection("arbitrations").document(to_delete).delete()
            st.toast(f"Deleted {to_delete}")
            st.rerun()

# --- 4. RAW DATA INSPECTOR ---
with st.expander("🕵️ View Raw JSON Data"):
    if to_delete and to_delete in full_data_map:
        st.json(full_data_map[to_delete])
