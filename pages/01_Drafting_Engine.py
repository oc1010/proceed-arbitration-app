import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date
from db import load_responses, save_timeline, reset_database, load_structure
import pandas as pd
import os

st.set_page_config(page_title="Drafting Engine", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied.")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    st.divider()
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("Procedural Order No. 1 | Drafting Engine")

# --- LOAD DATA ---
resp_p1 = load_responses("phase1") # Pre-Tribunal
resp_p2 = load_responses("phase2") # Pre-Hearing

# --- TABS ---
tabs = st.tabs(["Phase 1 Review", "Phase 2 Analysis", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])

# --- TAB 1: PHASE 1 REVIEW ---
with tabs[0]:
    st.subheader("Review: Pre-Tribunal Appointment Responses")
    st.caption("Responses collected by the LCIA prior to your appointment.")
    
    c_data = resp_p1.get('claimant', {})
    r_data = resp_p1.get('respondent', {})
    
    if not c_data and not r_data:
        st.info("No Phase 1 data found.")
    else:
        structure_p1 = load_structure("phase1")
        # Map ID to Question
        q_map = {q['id']: q['question'] for q in structure_p1} if structure_p1 else {}
        
        # Get all keys except comments
        all_keys = list(set(list(c_data.keys()) + list(r_data.keys())))
        q_keys = [k for k in all_keys if not k.endswith("_comment")]
        
        data = []
        for k in q_keys:
            q_text = q_map.get(k, k)
            c_ans = c_data.get(k, "-")
            r_ans = r_data.get(k, "-")
            
            # Clean markdown for table
            def clean(txt):
                if "**" in txt: return txt.split("**")[1]
                return txt
            
            data.append({
                "Topic": q_text,
                "Claimant": clean(c_ans),
                "Respondent": clean(r_ans)
            })
            
        st.dataframe(pd.DataFrame(data), use_container_width=True, hide_index=True)

# --- TAB 2: PHASE 2 ANALYSIS (Summary Table) ---
with tabs[1]:
    st.subheader("Analysis: Pre-Hearing Questionnaire")
    c_data = resp_p2.get('claimant', {})
    r_data = resp_p2.get('respondent', {})
    
    structure_p2 = load_structure("phase2")
    q_map_2 = {q['id']: q['question'] for q in structure_p2} if structure_p2 else {}
    
    all_keys = [k for k in list(set(list(c_data.keys()) + list(r_data.keys()))) if not k.endswith("_comment")]
    
    if not all_keys:
        st.info("No Phase 2 data submitted yet.")
    else:
        summary_data = []
        
        # Sort by numeric prefix
        def sort_key(k):
            text = q_map_2.get(k, k)
            try: return int(text.split(".")[0])
            except: return 999
            
        for k in sorted(all_keys, key=sort_key):
            topic = q_map_2.get(k, k)
            c_val = c_data.get(k, "Pending")
            r_val = r_data.get(k, "Pending")
            
            # Comments
            c_comm = c_data.get(f"{k}_comment", "")
            r_comm = r_data.get(f"{k}_comment", "")
            
            def clean_val(v):
                if "**" in v: return v.split("**")[1].strip()
                return v.split(".")[0] if v and "." in v else v
            
            c_clean = clean_val(c_val)
            r_clean = clean_val(r_val)
            
            if c_comm: c_clean += " 💬"
            if r_comm: r_clean += " 💬"
            
            match = "✅" if c_val == r_val and c_val != "Pending" else "❌"
            
            summary_data.append({
                "Question": topic, 
                "Claimant": c_clean, 
                "Respondent": r_clean, 
                "Match": match
            })
        
        st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
        
        st.markdown("### 💬 Party Comments")
        with st.expander("View Detailed Comments"):
            for k in sorted(all_keys, key=sort_key):
                c_comm = c_data.get(f"{k}_comment", "")
                r_comm = r_data.get(f"{k}_comment", "")
                if c_comm or r_comm:
                    st.markdown(f"**{q_map_2.get(k, k)}**")
                    if c_comm: st.info(f"Claimant: {c_comm}")
                    if r_comm: st.warning(f"Respondent: {r_comm}")
                    st.divider()

# ... (Rest of the Drafting Engine logic - General, Parties, etc - remains identical) ...
# Ensure context variables are set up as in previous versions.
