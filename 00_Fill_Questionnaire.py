import streamlit as st
from db import load_structure, load_responses, save_responses

st.set_page_config(page_title="Fill Questionnaire", layout="centered")

role = st.session_state.get('user_role')
if role not in ['claimant', 'respondent']:
    st.error("Access Denied")
    st.stop()

st.title("📋 Pre-Hearing Questionnaire")

structure = load_structure()
if not structure:
    st.warning("The Tribunal has not published the questionnaire yet.")
    st.stop()

all_responses = load_responses()
my_responses = all_responses.get(role, {})

with st.form("party_form"):
    new_responses = {}
    for q in structure:
        st.markdown(f"**{q['question']}**")
        curr = my_responses.get(q['id'])
        idx = q['options'].index(curr) if curr in q['options'] else 0
        
        if q['type'] == "radio":
            val = st.radio("Select:", q['options'], index=idx, key=q['id'], label_visibility="collapsed")
        else:
            val = st.selectbox("Select:", q['options'], index=idx, key=q['id'], label_visibility="collapsed")
        new_responses[q['id']] = val
        st.caption("---")
        
    if st.form_submit_button("Submit Responses", type="primary"):
        all_responses[role] = new_responses
        save_responses(all_responses)
        st.success("✅ Responses transmitted to Tribunal.")