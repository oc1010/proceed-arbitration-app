import streamlit as st
from docxtpl import DocxTemplate
from io import BytesIO
from datetime import date, timedelta
from db import load_responses, save_timeline, reset_database, load_structure
import pandas as pd

# ... (Standard Config & Sidebar) ...
# ... (Same as previous turn until the TABS section) ...

# --- UI TABS ---
tabs = st.tabs(["Preferences", "General", "Parties", "Tribunal", "Timetable", "Evidence", "Hearing", "Logistics", "Award"])

with tabs[0]:
    st.subheader("Questionnaire Responses")
    try:
        c_data = responses.get('claimant', {})
        r_data = responses.get('respondent', {})
        
        # Load the structure to get the ACTUAL QUESTION TEXT
        structure = load_structure()
        # Create a map: ID -> Question Text
        # e.g., {'custom_123': '38. My New Question'}
        dynamic_map = {}
        if structure:
            for q in structure:
                dynamic_map[q['id']] = q['question']
        
        all_keys = list(set(list(c_data.keys()) + list(r_data.keys())))
        
        if not all_keys:
            st.info("No data submitted.")
        else:
            summary_data = []
            for k in sorted(all_keys):
                # 1. Try finding name in the dynamic structure (Best for new questions)
                # 2. Fallback to hardcoded TOPIC_MAP (Legacy)
                # 3. Fallback to ID
                topic = dynamic_map.get(k, TOPIC_MAP.get(k, k))
                
                # Clean up the "38. " prefix if desired
                # topic = topic.split(". ", 1)[-1] if ". " in topic else topic
                
                c_val = c_data.get(k, "Pending")
                r_val = r_data.get(k, "Pending")
                
                # Clean up the "**Option A:**" bolding for the table display
                c_clean = c_val.replace("**", "")
                r_clean = r_val.replace("**", "")
                # Truncate long descriptions for table readability
                if len(c_clean) > 50: c_clean = c_clean.split(".")[0] + "..."
                if len(r_clean) > 50: r_clean = r_clean.split(".")[0] + "..."

                match = "✅" if c_val == r_val and c_val != "Pending" else "❌"
                summary_data.append({"Topic": topic, "Claimant": c_clean, "Respondent": r_clean, "Match": match})
            
            st.dataframe(pd.DataFrame(summary_data), use_container_width=True, hide_index=True)
    except Exception as e:
        st.error(f"Error loading table: {e}")

# ... (Rest of the file remains identical) ...
