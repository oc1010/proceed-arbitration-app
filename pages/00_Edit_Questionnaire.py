import streamlit as st
from db import load_structure, save_structure

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire")
    st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("✏️ Questionnaire Editor")
st.caption("Customize the questions sent to the parties. Changes are saved to the Cloud instantly.")

# --- LOAD DATA ---
current_structure = load_structure()
if not current_structure:
    st.warning("No questions found. Please reset the database if this is a fresh start.")
    st.stop()

# --- EDITOR UI ---
with st.form("editor_form"):
    updated_structure = []
    st.markdown("### Questions Configuration")
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2, c3 = st.columns([6, 2, 1])
            
            # Question Text
            new_q_text = c1.text_input(f"Question #{i+1}", value=q['question'], key=f"q_{i}")
            
            # Input Type
            type_map = {"radio": "List View", "selectbox": "Dropdown"}
            rev_map = {"List View": "radio", "Dropdown": "selectbox"}
            curr_type = type_map.get(q['type'], "List View")
            new_type_disp = c2.selectbox("Type", ["List View", "Dropdown"], index=0 if curr_type=="List View" else 1, key=f"t_{i}")
            new_type = rev_map[new_type_disp]
            
            # Delete Option
            to_delete = c3.checkbox("🗑️ Delete", key=f"del_{i}", help="Check this and click Publish to remove this question.")
            
            # Options
            options_str = ", ".join(q['options'])
            new_options_str = st.text_area(f"Options (comma separated) #{i+1}", value=options_str, key=f"o_{i}")
            
            # Only add to list if NOT deleted
            if not to_delete:
                updated_structure.append({
                    "id": q['id'], 
                    "question": new_q_text, 
                    "type": new_type, 
                    "options": [opt.strip() for opt in new_options_str.split(",")]
                })
    
    st.divider()
    if st.form_submit_button("💾 Publish Updates", type="primary"):
        save_structure(updated_structure)
        st.success("✅ Questionnaire updated! Deleted questions (if any) have been removed.")
        st.rerun()
