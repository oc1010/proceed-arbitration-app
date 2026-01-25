import streamlit as st
from db import load_structure, load_responses, save_responses, get_release_status

st.set_page_config(page_title="Fill Questionnaires", layout="centered")

role = st.session_state.get('user_role')
if role not in ['claimant', 'respondent']:
    st.warning("Access Denied.")
    st.stop()

def logout():
    st.session_state['user_role'] = None
    st.switch_page("main.py")

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    if st.button("Logout", use_container_width=True): logout()
    st.divider()
    st.page_link("main.py", label="Home")
    st.page_link("pages/00_Fill_Questionnaire.py", label="Fill Questionnaires")
    st.page_link("pages/02_Smart_Timeline.py", label="Smart Timeline")

st.title("Procedural Questionnaires")

# --- CHECK RELEASE STATUS ---
status = get_release_status()
p1_live = status.get("phase1", False)
p2_live = status.get("phase2", False)

if not p1_live and not p2_live:
    st.info("No questionnaires are currently active. Please wait for the LCIA or Tribunal.")
    st.stop()

# --- RENDER FORM HELPER ---
def render_form(phase, name):
    structure = load_structure(phase)
    all_resp = load_responses(phase)
    my_resp = all_resp.get(role, {})
    
    if not structure:
        st.error("Error loading form structure.")
        return

    with st.form(f"f_{phase}"):
        st.subheader(name)
        new_r = {}
        for q in structure:
            st.markdown(f"### {q['question']}")
            curr = my_resp.get(q['id'], "")
            
            # Simple renderer
            if q['type'] == 'text_area':
                val = st.text_area("Your Answer:", curr, key=f"{phase}_{q['id']}")
                new_r[q['id']] = val
            else:
                # Radio/List logic
                is_custom = curr not in q['options'] and curr != ""
                if is_custom and "Other" in q['options']: list_index = q['options'].index("Other")
                elif curr in q['options']: list_index = q['options'].index(curr)
                else: list_index = 0

                if q['type'] == "radio":
                    val = st.radio("Select one:", q['options'], index=list_index, key=f"{phase}_{q['id']}")
                else:
                    val = st.selectbox("Select:", q['options'], index=list_index, key=f"{phase}_{q['id']}")
                
                final_val = val
                if val == "Other":
                    final_val = st.text_input("Please specify:", value=curr if is_custom else "", key=f"{phase}_oth_{q['id']}")
                
                new_r[q['id']] = final_val
                
            # Comment Field
            comment_key = f"{q['id']}_comment"
            curr_comment = my_resp.get(comment_key, "")
            st.caption("Optional: Provide reasoning or additional details.")
            comment_val = st.text_area("Comments:", value=curr_comment, key=f"{phase}_com_{q['id']}", height=68, label_visibility="collapsed")
            new_r[comment_key] = comment_val
            
            st.markdown("---")
            
        if st.form_submit_button("Submit Responses"):
            all_resp[role] = new_r
            save_responses(all_resp, phase)
            st.success("Submitted successfully!")

# --- DISPLAY LOGIC ---
if p2_live:
    t1, t2 = st.tabs(["Phase 2: Pre-Hearing", "Phase 1: Pre-Tribunal (Reference)"])
    with t1:
        render_form("phase2", "Phase 2: Pre-Hearing Questionnaire")
    with t2:
        st.info("You have already submitted this. You may update if necessary.")
        render_form("phase1", "Phase 1: Pre-Tribunal Appointment Questionnaire")

elif p1_live:
    render_form("phase1", "Pre-Tribunal Appointment Questionnaire")
