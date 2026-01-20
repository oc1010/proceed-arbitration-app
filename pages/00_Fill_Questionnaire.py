import streamlit as st
from db import load_structure, load_responses, save_responses

st.set_page_config(page_title="Questionnaire", layout="centered")

# --- SECURITY ---
role = st.session_state.get('user_role')
if role not in ['claimant', 'respondent']:
    st.warning("Access Denied. Please log in.")
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
    st.page_link("pages/00_Fill_Questionnaire.py", label="Procedural Questionnaire")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("Pre-Hearing Questionnaire")
st.write("Please indicate your preferences below.")

# --- DATA ---
structure = load_structure()
if not structure:
    st.warning("The Tribunal has not published the questionnaire yet.")
    st.stop()

all_responses = load_responses()
my_responses = all_responses.get(role, {})

# --- FORM ---
with st.form("party_form"):
    new_responses = {}
    
    for q in structure:
        st.markdown(f"**{q['question']}**")
        
        # Get previous answer
        curr_val = my_responses.get(q['id'], "")
        
        # Check if the previous answer was a custom "Other" value (not in the list)
        is_custom = curr_val not in q['options'] and curr_val != ""
        
        # Decide the index for the widget
        if is_custom and "Other" in q['options']:
            # If they typed something custom before, set widget to "Other"
            list_index = q['options'].index("Other")
        elif curr_val in q['options']:
            list_index = q['options'].index(curr_val)
        else:
            list_index = 0

        # Render Widget
        if q['type'] == "radio":
            selection = st.radio("Select:", q['options'], index=list_index, key=f"rad_{q['id']}", label_visibility="collapsed")
        else:
            selection = st.selectbox("Select:", q['options'], index=list_index, key=f"sel_{q['id']}", label_visibility="collapsed")
        
        # Logic for "Other" - Allow custom input
        final_answer = selection
        if selection == "Other":
            # If they previously typed a custom value, show it as default
            default_text = curr_val if is_custom else ""
            custom_input = st.text_input("Please specify your rules:", value=default_text, key=f"other_{q['id']}")
            if custom_input:
                final_answer = custom_input
        
        new_responses[q['id']] = final_answer
        st.divider()
        
    if st.form_submit_button("Submit Responses", type="primary"):
        all_responses[role] = new_responses
        save_responses(all_responses)
        st.success("Responses transmitted to Tribunal.")
