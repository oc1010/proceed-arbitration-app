import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from db import load_complex_data, save_complex_data, load_responses, send_email_notification
import json

st.set_page_config(page_title="Smart Timeline", layout="wide")

role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR (PERSISTENT) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home Dashboard")
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Questionnaires")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 PO1 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    else:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="📂 Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")

    st.divider()
    if st.button("Logout", use_container_width=True):
        st.session_state['user_role'] = None
        st.switch_page("main.py")

st.title("📅 Phase 4: Procedural Timetable")

# --- LOAD & REPAIR DATA ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

# Auto-repair logic for old data format
cleaned_timeline = []
for idx, e in enumerate(timeline):
    if not isinstance(e, dict): continue # Skip bad entries
    
    # Ensure required keys exist to prevent crashes
    if 'current_date' not in e:
        e['current_date'] = e.get('date', str(date.today()))
    if 'original_date' not in e:
        e['original_date'] = e.get('date', str(date.today()))
    if 'history' not in e:
        e['history'] = []
    if 'id' not in e:
        e['id'] = f"evt_{idx}_{int(datetime.now().timestamp())}"
    
    cleaned_timeline.append(e)

if cleaned_timeline != timeline:
    timeline = cleaned_timeline
    save_complex_data("timeline", timeline)

# --- EMAIL HELPERS ---
def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- TAB 1: VISUAL SCHEDULE ---
tab1, tab2, tab3 = st.tabs(["📊 Visual Schedule", "⏳ Extension of Time Requests", "📝 Change Log"])

with tab1:
    if not timeline:
        st.warning("No procedural timetable found. Arbitrator must generate PO1 first.")
    else:
        # Data Prep
        df = pd.DataFrame(timeline)
        
        # Ensure we have valid dates
        try:
            df['Date'] = pd.to_datetime(df['current_date'], errors='coerce')
            df = df.dropna(subset=['Date']) # Drop rows with invalid dates
            
            df = df.sort_values(by='Date')
            
            # Staggered Heights
            heights = []
            for i in range(len(df)):
                val = (i % 3) + 1
                if i % 2 == 0: val = val * 1
                else: val = val * -1
                heights.append(val)
            df['Height'] = heights
            df['Zero'] = 0

            today = pd.to_datetime(date.today())
            def get_status(row):
                if row['Date'] < today: return "Completed"
                return "Upcoming"
            df['Status'] = df.apply(get_status, axis=1)

            # Chart
            rule = alt.Chart(df).mark_rule(color="gray", strokeWidth=2).encode(
                x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
                y=alt.Y('Zero', axis=None)
            )
            stems = alt.Chart(df).mark_rule(color="lightgray").encode(x='Date', y='Zero', y2='Height')
            points = alt.Chart(df).mark_circle(size=100).encode(
                x='Date', y='Height',
                color=alt.Color('Status', scale=alt.Scale(domain=['Completed', 'Upcoming'], range=['#28a745', '#007bff'])),
                tooltip=['event', 'current_date', 'owner', 'logistics']
            )
            text = alt.Chart(df).mark_text(align='center', baseline='middle', dy=-15).encode(
                x='Date', y='Height', text='event'
            )
            st.altair_chart((rule + stems + points + text).properties(height=300).interactive(), use_container_width=True)

            # Table
            st.markdown("### Schedule Details")
            cols_to_show = ['event', 'current_date', 'owner', 'logistics', 'Status']
            valid_cols = [c for c in cols_to_show if c in df.columns]
            st.dataframe(df[valid_cols], use_container_width=True, hide_index=True)

        except Exception as e:
            st.error(f"Error visualizing timeline: {e}")
            st.write("Raw Data:", timeline)

        # ARBITRATOR CONTROLS
        if role == 'arbitrator':
            st.divider()
            st.subheader("Manage Timetable")
            c_mod, c_add = st.columns(2)
            
            with c_mod:
                with st.container(border=True):
                    st.write("**Modify Existing Event**")
                    event_options = [e['event'] for e in timeline]
                    if event_options:
                        event_to_mod = st.selectbox("Select Event", event_options, key="mod_sel")
                        new_date = st.date_input("New Date", key="mod_date")
                        reason = st.text_input("Reason for Change", key="mod_reason")
                        
                        if st.button("Update Event"):
                            for e in timeline:
                                if e.get('event') == event_to_mod:
                                    e['current_date'] = str(new_date)
                                    e['history'].append(f"Moved to {new_date}. Reason: {reason}")
                            save_complex_data("timeline", timeline)
                            send_email_notification(get_party_emails(), "Timetable Updated", f"Moved '{event_to_mod}' to {new_date}.")
                            st.success("Updated."); st.rerun()
            
            with c_add:
                with st.container(border=True):
                    st.write("**Add New Event**")
                    new_evt_name = st.text_input("Event Name", key="add_name")
                    new_evt_date = st.date_input("Event Date", key="add_date")
                    new_evt_owner = st.selectbox("Owner", ["Claimant", "Respondent", "Tribunal"], key="add_owner")
                    
                    if st.button("Add Event"):
                        new_entry = {
                            "id": f"evt_{int(datetime.now().timestamp())}",
                            "event": new_evt_name,
                            "original_date": str(new_evt_date),
                            "current_date": str(new_evt_date),
                            "owner": new_evt_owner,
                            "status": "Upcoming",
                            "history": ["Created manually"],
                            "logistics": "Manual Entry"
                        }
                        timeline.append(new_entry)
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), "New Event", f"Added '{new_evt_name}' on {new_evt_date}.")
                        st.success("Added."); st.rerun()

# --- TAB 2: EXTENSION REQUESTS ---
with tab2:
    st.subheader("Requests for Extension of Time")
    
    if role in ['claimant', 'respondent']:
        with st.form("eot_form"):
            evts = [e['event'] for e in timeline]
            target = st.selectbox("Event", evts) if evts else st.text_input("Event Name")
            reason = st.text_area("Reason")
            prop_date = st.date_input("Proposed Date")
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": target, "requestor": role, "reason": reason, 
                    "proposed_date": str(prop_date), "status": "Pending", "tribunal_decision": ""
                })
                save_complex_data("delays", delays)
                send_email_notification([], "EoT Request", f"{role} requests delay for {target}.")
                st.success("Submitted.")

    if delays:
        for i, req in enumerate(delays):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{req['event']}** (Req: {req['requestor']})")
                c1.caption(f"Reason: {req['reason']}")
                c2.write(f"Status: **{req['status']}**")
                if req.get('tribunal_decision'): c2.info(f"Note: {req['tribunal_decision']}")
                
                if role == 'arbitrator' and req['status'] == "Pending":
                    dec_reason = c3.text_input("Decision Note", key=f"dnote_{i}")
                    if c3.button("Approve", key=f"app_{i}"):
                        req['status'] = "Approved"
                        req['tribunal_decision'] = dec_reason
                        # Update actual timeline
                        for e in timeline:
                            if e.get('event') == req['event']:
                                e['current_date'] = req['proposed_date']
                                e['history'].append(f"EoT Approved. New: {req['proposed_date']}")
                        save_complex_data("delays", delays)
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), "EoT Approved", f"Delay approved for {req['event']}.")
                        st.rerun()
                        
                    if c3.button("Deny", key=f"den_{i}"):
                        req['status'] = "Denied"
                        req['tribunal_decision'] = dec_reason
                        save_complex_data("delays", delays)
                        send_email_notification(get_party_emails(), "EoT Denied", f"Delay denied for {req['event']}.")
                        st.rerun()
    else:
        st.info("No requests pending.")

# --- TAB 3: HISTORY ---
with tab3:
    st.write("### Change Log")
    log = []
    for e in timeline:
        for h in e.get('history', []):
            log.append({"Event": e.get('event'), "Log": h})
    if log: st.dataframe(pd.DataFrame(log), use_container_width=True)
    else: st.caption("No changes recorded.")
