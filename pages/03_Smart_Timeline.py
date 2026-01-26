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

# --- SIDEBAR ---
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
        # --- DATA NORMALIZATION (Prevents KeyError) ---
        df = pd.DataFrame(timeline)
        
        # 1. Backwards Compatibility: Handle old 'date' field if 'current_date' missing
        if 'current_date' not in df.columns and 'date' in df.columns:
            df['current_date'] = df['date']
            df['original_date'] = df['date']
            
        # 2. Safety: Ensure required columns exist
        if 'current_date' in df.columns:
            df['Start'] = pd.to_datetime(df['current_date'])
            df['End'] = df['Start'] + timedelta(days=2) # Small width
            
            today = pd.to_datetime(date.today())
            def get_status(row):
                if row['Start'] < today: return "Completed"
                return "Upcoming"
            df['Status'] = df.apply(get_status, axis=1)

            # 3. VISUAL LINE (Altair)
            chart = alt.Chart(df).mark_bar(cornerRadius=10, height=20).encode(
                x=alt.X('Start', title='Timeline', axis=alt.Axis(format='%d %b %Y')),
                x2='End',
                y=alt.Y('event', title=None, sort='x'),
                color=alt.Color('Status', scale=alt.Scale(domain=['Completed', 'Upcoming'], range=['#28a745', '#007bff'])),
                tooltip=['event', 'current_date', 'owner', 'logistics']
            ).properties(title="Case Timeline", height=400)
            
            st.altair_chart(chart, use_container_width=True)

            # 4. DETAILED TABLE
            st.markdown("### Schedule Details")
            display_cols = ['event', 'current_date', 'owner', 'logistics', 'Status']
            # Ensure columns exist before selecting
            valid_cols = [c for c in display_cols if c in df.columns]
            
            st.dataframe(
                df[valid_cols], 
                use_container_width=True,
                hide_index=True
            )

            # 5. ARBITRATOR MODIFICATION
            if role == 'arbitrator':
                st.divider()
                with st.expander("Modify Schedule (Arbitrator Only)"):
                    with st.form("mod_schedule"):
                        event_to_mod = st.selectbox("Select Event to Move", df['event'].unique())
                        new_date = st.date_input("New Date")
                        reason = st.text_input("Reason for Change")
                        
                        if st.form_submit_button("Update Schedule"):
                            # Update logic in list of dicts
                            for e in timeline:
                                if e.get('event') == event_to_mod:
                                    # Handle old data keys if needed
                                    if 'current_date' not in e: e['current_date'] = e.get('date')
                                    
                                    old_date = e['current_date']
                                    e['current_date'] = str(new_date)
                                    if 'history' not in e: e['history'] = []
                                    e['history'].append(f"Moved from {old_date} to {new_date} by Tribunal. Reason: {reason}")
                            
                            save_complex_data("timeline", timeline)
                            send_email_notification(get_party_emails(), "Timetable Updated", f"The Tribunal has moved '{event_to_mod}' to {new_date}.\nReason: {reason}")
                            st.success("Schedule updated and parties notified.")
                            st.rerun()
        else:
            st.error("Timeline data format is invalid. Please regenerate PO1 in Drafting Engine to fix.")

# --- TAB 2: EXTENSION OF TIME (EoT) ---
with tab2:
    st.subheader("Requests for Extension of Time")
    
    # Request Form (Parties)
    if role in ['claimant', 'respondent']:
        with st.form("eot_form"):
            # Filter safe list
            events = [e['event'] for e in timeline if 'event' in e]
            target_event = st.selectbox("Request Delay For", events)
            reason_text = st.text_area("Reason for Request (e.g., Unforeseen circumstances)")
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
                        # Update Timeline
                        for e in timeline:
                            if e.get('event') == req['event']:
                                e['current_date'] = req['proposed_date']
                                if 'history' not in e: e['history'] = []
                                e['history'].append(f"EoT Approved for {req['requestor']}. New Date: {req['proposed_date']}")
                        
                        save_complex_data("delays", delays)
                        save_complex_data("timeline", timeline)
                        send_email_notification(get_party_emails(), f"EoT Approved: {req['event']}", f"The Tribunal has approved the delay to {req['proposed_date']}.\nReason: {decision_reason}")
                        st.rerun()
                        
                    if c3.button("Deny", key=f"den_{i}"):
                        req['status'] = "Denied"
                        req['tribunal_decision'] = decision_reason
                        save_complex_data("delays", delays)
                        send_email_notification(get_party_emails(), f"EoT Denied: {req['event']}", f"The Tribunal has denied the delay.\nReason: {decision_reason}")
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
