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
    st.page_link("main.py", label="Home")
    
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 1 Qs")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="Edit Phase 2 Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="Procedural Order No. 1")
        st.page_link("pages/02_Doc_Production.py", label="Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="Timeline & Logistics")
        st.page_link("pages/04_Cost_Management.py", label="Cost Management")
    else:
        st.page_link("pages/00_Fill_Questionnaire.py", label="Fill Questionnaires")
        st.page_link("pages/02_Doc_Production.py", label="Doc Production")
        st.page_link("pages/03_Smart_Timeline.py", label="Timeline & Logistics")
        st.page_link("pages/04_Cost_Management.py", label="Cost Management")

    st.divider()
    def logout():
        st.session_state['user_role'] = None
        st.switch_page("main.py")
    st.button("Logout", on_click=logout)

st.title("📅 Phase 4: Procedural Timetable")

# --- LOAD DATA ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

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
        # --- DATA PREP ---
        df = pd.DataFrame(timeline)
        
        # Safety Check for keys
        if 'current_date' not in df.columns and 'date' in df.columns:
            df['current_date'] = df['date']
        
        df['Date'] = pd.to_datetime(df['current_date'])
        
        # Sort by date for proper display
        df = df.sort_values(by='Date')
        
        # Create Staggered Heights to avoid bunching (1, -1, 2, -2...)
        # This makes the "pretty" horizontal timeline you requested
        heights = []
        for i in range(len(df)):
            val = (i % 3) + 1
            if i % 2 == 0: val = val * 1
            else: val = val * -1
            heights.append(val)
        df['Height'] = heights
        df['Zero'] = 0 # Baseline for the horizontal line

        today = pd.to_datetime(date.today())
        def get_status(row):
            if row['Date'] < today: return "Completed"
            return "Upcoming"
        df['Status'] = df.apply(get_status, axis=1)

        # --- ALTAIR VISUALIZATION (Staggered Timeline) ---
        # 1. The Main Horizontal Line
        rule = alt.Chart(df).mark_rule(color="gray", strokeWidth=2).encode(
            x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
            y=alt.Y('Zero', axis=None) # Hide Y axis values
        )

        # 2. The Vertical "Stems" connecting points to the line
        stems = alt.Chart(df).mark_rule(color="lightgray").encode(
            x='Date',
            y='Zero',
            y2='Height'
        )

        # 3. The Circles (Events)
        points = alt.Chart(df).mark_circle(size=100).encode(
            x='Date',
            y='Height',
            color=alt.Color('Status', scale=alt.Scale(domain=['Completed', 'Upcoming'], range=['#28a745', '#007bff'])),
            tooltip=['event', 'current_date', 'owner', 'logistics']
        )

        # 4. The Text Labels (Event Names)
        text = alt.Chart(df).mark_text(align='center', baseline='middle', dy=-15).encode(
            x='Date',
            y='Height',
            text='event'
        )

        final_chart = (rule + stems + points + text).properties(height=300).interactive()
        
        st.altair_chart(final_chart, use_container_width=True)

        # --- DETAILED TABLE ---
        st.markdown("### Detailed Schedule")
        display_cols = ['event', 'current_date', 'owner', 'logistics', 'Status']
        valid_cols = [c for c in display_cols if c in df.columns]
        
        st.dataframe(
            df[valid_cols], 
            use_container_width=True,
            column_config={
                "event": "Event Name",
                "current_date": "Date",
                "owner": "Responsible Party",
                "logistics": "Logistics / Instructions",
                "Status": st.column_config.TextColumn("Status", width="small"),
            },
            hide_index=True
        )

        # --- ARBITRATOR CONTROLS (Add & Modify) ---
        if role == 'arbitrator':
            st.divider()
            st.subheader("Manage Timetable")
            
            c_mod, c_add = st.columns(2)
            
            # 1. MODIFY EXISTING
            with c_mod:
                with st.container(border=True):
                    st.write("**Modify Existing Event**")
                    event_to_mod = st.selectbox("Select Event", df['event'].unique(), key="mod_sel")
                    new_date = st.date_input("New Date", key="mod_date")
                    reason = st.text_input("Reason for Change", key="mod_reason")
                    
                    if st.button("Update Event"):
                        for e in timeline:
                            if e.get('event') == event_to_mod:
                                e['current_date'] = str(new_date)
                                if 'history' not in e: e['history'] = []
                                e['history'].append(f"Moved to {new_date}. Reason: {reason}")
                        
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), "Timetable Updated", f"The Tribunal has moved '{event_to_mod}' to {new_date}.\nReason: {reason}")
                        st.success("Updated & Notified.")
                        st.rerun()

            # 2. ADD NEW EVENT
            with c_add:
                with st.container(border=True):
                    st.write("**Add New Event**")
                    new_evt_name = st.text_input("Event Name", key="add_name")
                    new_evt_date = st.date_input("Event Date", key="add_date")
                    new_evt_owner = st.selectbox("Responsible Party", ["Claimant", "Respondent", "Both", "Tribunal"], key="add_owner")
                    new_evt_log = st.text_input("Logistics (Venue/Instructions)", key="add_log")
                    
                    if st.button("Add to Timeline"):
                        new_entry = {
                            "id": f"custom_{int(datetime.now().timestamp())}",
                            "event": new_evt_name,
                            "original_date": str(new_evt_date),
                            "current_date": str(new_evt_date),
                            "owner": new_evt_owner,
                            "status": "Upcoming",
                            "logistics": new_evt_log,
                            "history": ["Created manually by Tribunal"]
                        }
                        timeline.append(new_entry)
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), "New Event Added", f"The Tribunal has added a new event: '{new_evt_name}' on {new_evt_date}.")
                        st.success("Event Added & Notified.")
                        st.rerun()

# --- TAB 2: EXTENSION OF TIME (EoT) ---
with tab2:
    st.subheader("Requests for Extension of Time")
    
    # Request Form (Parties)
    if role in ['claimant', 'respondent']:
        with st.form("eot_form"):
            events = [e['event'] for e in timeline if 'event' in e]
            target_event = st.selectbox("Request Delay For", events)
            reason_text = st.text_area("Reason for Request")
            requested_date = st.date_input("Proposed New Date")
            
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": target_event,
                    "requestor": role,
                    "reason": reason_text,
                    "proposed_date": str(requested_date),
                    "status": "Pending",
                    "tribunal_decision": ""
                })
                save_complex_data("delays", delays)
                send_email_notification([], f"EoT Request: {target_event}", f"{role.title()} requests delay until {requested_date}.\nReason: {reason_text}")
                st.success("Request submitted to Tribunal.")

    # Review List (All)
    if delays:
        for i, req in enumerate(delays):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{req['event']}**")
                c1.caption(f"Requestor: {req['requestor'].title()} | Proposed: {req['proposed_date']}")
                c1.write(f"*Reason:* {req['reason']}")
                
                c2.markdown(f"**Status:** `{req['status']}`")
                if req.get('tribunal_decision'):
                    c2.info(f"Decision: {req['tribunal_decision']}")

                # Arbitrator Action
                if role == 'arbitrator' and req['status'] == "Pending":
                    decision_reason = c3.text_input("Reasoning", key=f"dec_{i}")
                    if c3.button("Approve", key=f"app_{i}"):
                        req['status'] = "Approved"
                        req['tribunal_decision'] = decision_reason
                        for e in timeline:
                            if e.get('event') == req['event']:
                                e['current_date'] = req['proposed_date']
                                if 'history' not in e: e['history'] = []
                                e['history'].append(f"EoT Approved for {req['requestor']}. New Date: {req['proposed_date']}")
                        
                        save_complex_data("delays", delays)
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), f"EoT Approved: {req['event']}", f"Delay approved to {req['proposed_date']}.\nReason: {decision_reason}")
                        st.rerun()
                        
                    if c3.button("Deny", key=f"den_{i}"):
                        req['status'] = "Denied"
                        req['tribunal_decision'] = decision_reason
                        save_complex_data("delays", delays)
                        send_email_notification(get_party_emails(), f"EoT Denied: {req['event']}", f"Delay denied.\nReason: {decision_reason}")
                        st.rerun()
    else:
        st.info("No extension requests pending.")

# --- TAB 3: HISTORY ---
with tab3:
    st.subheader("Procedural History & Changes")
    history_log = []
    for e in timeline:
        for h in e.get('history', []):
            history_log.append({"Event": e.get('event', '?'), "Change Log": h})
            
    if history_log:
        st.dataframe(pd.DataFrame(history_log), use_container_width=True)
    else:
        st.caption("No changes have been made to the original schedule yet.")
