import streamlit as st
from db import load_structure, save_structure

st.set_page_config(page_title="Edit Questionnaire", layout="wide")

if st.session_state.get('user_role') != 'arbitrator':
    st.error("Access Denied")
    st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home Dashboard", icon="🏠")
    st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Questionnaire", icon="✏️")
    st.page_link("pages/01_Drafting_Engine.py", label="Drafting Engine", icon="📝")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline", icon="📅")

st.title("✏️ Questionnaire Editor")
st.caption("Customize the questions sent to the parties. Changes are saved to the Cloud instantly.")

DEFAULT_QUESTIONS = [
    {"id": "style", "question": "1. Style of Written Submissions", "type": "radio", "options": ["Memorial Style (Simultaneous)", "Pleading Style (Sequential)"]},
    {"id": "bifurcation", "question": "2. Bifurcation of Proceedings", "type": "radio", "options": ["Single Phase (All issues together)", "Bifurcation requested (Liability first)"]},
    {"id": "doc_prod", "question": "3. Document Production Guidelines", "type": "selectbox", "options": ["IBA Rules (Binding)", "IBA Rules (Guidelines only)", "Prague Rules", "None"]},
    {"id": "limits", "question": "4. Document Request Limits", "type": "selectbox", "options": ["Standard (No specific limit)", "Capped (e.g. 20 requests)", "None"]},
    {"id": "secretary", "question": "5. Tribunal Secretary Appointment", "type": "radio", "options": ["Consent to Appointment", "Object to Appointment"]},
    {"id": "sec_fees", "question": "6. Secretary Fees (if appointed)", "type": "radio", "options": ["£75 - £175 / hr (LCIA Standard)", "£100 - £250 / hr (Draft PO1)"]},
    {"id": "extensions", "question": "7. Protocol for Time Extensions", "type": "selectbox", "options": ["Standard (Good cause)", "Strict (Exceptional only)", "Flexible (Party agreed)"]},
    {"id": "funding", "question": "8. Third-Party Funding Disclosure", "type": "radio", "options": ["No third-party funding", "Funding is in place"]}
]

current_structure = load_structure()
if not current_structure:
    current_structure = DEFAULT_QUESTIONS

with st.form("editor_form"):
    updated_structure = []
    st.write("### Configure Questions")
    
    for i, q in enumerate(current_structure):
        with st.container(border=True):
            c1, c2 = st.columns([3, 1])
            new_q_text = c1.text_input(f"Question #{i+1}", value=q['question'], key=f"q_{i}")
            new_type = c2.selectbox("Type", ["radio", "selectbox"], index=0 if q['type']=="radio" else 1, key=f"t_{i}")
            
            options_str = ", ".join(q['options'])
            new_options_str = st.text_area(f"Options #{i+1}", value=options_str, key=f"o_{i}")
            
            updated_structure.append({
                "id": q['id'], "question": new_q_text, "type": new_type, 
                "options": [opt.strip() for opt in new_options_str.split(",")]
            })
    
    if st.form_submit_button("💾 Publish to Parties", type="primary"):
        save_structure(updated_structure)
        st.success("✅ Updated Questionnaire published!")
