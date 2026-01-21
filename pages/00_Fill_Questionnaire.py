import streamlit as st
from db import load_structure, load_responses, save_responses

st.set_page_config(page_title="Questionnaire", layout="centered")

role = st.session_state.get('user_role')
if role not in ['claimant', 'respondent']:
    st.warning("Access Denied. Please log in.")
    st.stop()

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

with st.sidebar:
    st.write(f"User: **{st.session_state['user_role'].upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.caption("NAVIGATION")
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Fill_Questionnaire.py", label="Procedural Questionnaire")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("Pre-Hearing Questionnaire")

structure = load_structure()
if not structure:
    st.warning("The Tribunal has not published the questionnaire yet.")
    st.stop()

all_responses = load_responses()
my_responses = all_responses.get(role, {})

with st.form("party_form"):
    new_responses = {}
    
    for q in structure:
        st.markdown(f"### {q['question']}")
        
        # 1. Main Answer
        curr_val = my_responses.get(q['id'], "")
        
        if q['type'] == "text_area":
            # Text Input Handling
            val = st.text_area("Your Answer:", value=curr_val, key=q['id'])
            new_responses[q['id']] = val
        else:
            # List/Radio Handling
            # Determine previous index if exists
            is_custom = curr_val not in q['options'] and curr_val != ""
            if is_custom and "Other" in q['options']: list_index = q['options'].index("Other")
            elif curr_val in q['options']: list_index = q['options'].index(curr_val)
            else: list_index = 0

            if q['type'] == "radio":
                selection = st.radio(
                    "Select one:", 
                    q['options'], 
                    index=list_index, 
                    key=f"rad_{q['id']}"
                )
            else:
                selection = st.selectbox("Select:", q['options'], index=list_index, key=f"sel_{q['id']}")
            
            final_answer = selection
            if selection == "Other":
                default_text = curr_val if is_custom else ""
                custom_input = st.text_input("Please specify:", value=default_text, key=f"other_{q['id']}")
                if custom_input: final_answer = custom_input
            
            new_responses[q['id']] = final_answer
        
        # 2. Additional Comment (Crucial Addition)
        comment_key = f"{q['id']}_comment"
        curr_comment = my_responses.get(comment_key, "")
        comment = st.text_area("Additional Comments (Optional):", value=curr_comment, key=f"comment_{q['id']}", height=68)
        new_responses[comment_key] = comment
        
        st.markdown("---")
        
    if st.form_submit_button("Submit Responses", type="primary"):
        all_responses[role] = new_responses
        save_responses(all_responses)
        st.success("Responses transmitted.")
