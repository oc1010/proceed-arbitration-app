import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from db import load_complex_data, save_complex_data, load_responses, send_notification
import json

st.set_page_config(page_title="Smart Timeline", layout="wide")

# --- AUTHENTICATION ---
role = st.session_state.get('user_role')
if not role:
    st.error("Access Denied.")
    if st.button("Log in"): st.switch_page("main.py")
    st.stop()

# --- SIDEBAR (PERSISTENT) ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    
    # Navigation Links
    if role == 'lcia':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
    elif role == 'arbitrator':
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    else:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Qs")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")

    st.divider()
    if st.button("Logout"): 
        st.session_state['user_role'] = None
        st.switch_page("main.py")

st.title("📅 Phase 4: Procedural Timetable")

# --- DATA LOADING & AUTO-REPAIR ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

# Auto-repair logic: Fixes old data missing 'current_date' or 'logistics'
# This prevents the KeyError crash you experienced.
repaired = False
for idx, e in enumerate(timeline):
    if not isinstance(e, dict): continue
    
    # Fix Date Fields
    if 'current_date' not in e:
        e['current_date'] = e.get('date', str(date.today()))
        repaired = True
    if 'original_date' not in e:
        e['original_date'] = e.get('date', str(date.today()))
        repaired = True
        
    # Fix Logistics Field (Rename logic if needed)
    if 'logistics' not in e:
        e['logistics'] = "To Be Determined"
        repaired = True
        
    # Ensure ID exists
    if 'id' not in e:
        e['id'] = f"evt_{idx}_{int(datetime.now().timestamp())}"
        repaired = True

if repaired:
    save_complex_data("timeline", timeline)
    # Silent save to fix data structure

# --- EMAIL HELPER ---
def get_party_emails():
    """Fetches emails for Claimant and Respondent from Phase 2 responses."""
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- TAB 1: VISUAL SCHEDULE & TABLE ---
tab1, tab2, tab3 = st.tabs(["📊 Visual Schedule", "⏳ Extension of Time Requests", "📝 Change Log"])

with tab1:
    if not timeline:
        st.warning("No procedural timetable found. Arbitrator must generate PO1 first.")
    else:
        # Prepare Data for Visualization
        df = pd.DataFrame(timeline)
        
        # Parse Dates safely
        df['Date'] = pd.to_datetime(df['current_date'], errors='coerce')
        df = df.dropna(subset=['Date']) # Remove invalid dates
        df = df.sort_values(by='Date')
        
        # Create Staggered Heights for Chart (1, -1, 2, -2...) to avoid bunching
        heights = []
        for i in range(len(df)):
            val = (i % 3) + 1
            if i % 2 == 0: val = val * 1
            else: val = val * -1
            heights.append(val)
        df['Height'] = heights
        df['Zero'] = 0 # Baseline for the horizontal line

        # Determine Status
        today = pd.to_datetime(date.today())
        df['Status'] = df.apply(lambda x: "Completed" if x['Date'] < today else "Upcoming", axis=1)

        # --- ALTAIR STAGGERED CHART ---
        # 1. Main Line
        rule = alt.Chart(df).mark_rule(color="gray", strokeWidth=2).encode(
            x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
            y=alt.Y('Zero', axis=None)
        )
        # 2. Vertical Stems
        stems = alt.Chart(df).mark_rule(color="lightgray").encode(
            x='Date',
            y='Zero',
            y2='Height'
        )
        # 3. Event Points
        points = alt.Chart(df).mark_circle(size=100).encode(
            x='Date',
            y='Height',
            color=alt.Color('Status', scale=alt.Scale(domain=['Completed', 'Upcoming'], range=['#28a745', '#007bff'])),
            tooltip=['event', 'current_date', 'owner', 'logistics']
        )
        # 4. Text Labels
        text = alt.Chart(df).mark_text(align='center', baseline='middle', dy=-15).encode(
            x='Date',
            y='Height',
            text='event'
        )

        final_chart = (rule + stems + points + text).properties(height=350).interactive()
        st.altair_chart(final_chart, use_container_width=True)

        # --- DETAILED TABLE (Editable for Arbitrator) ---
        st.markdown("### Schedule Details")
        
        # Prepare display dataframe
        display_df = df[['event', 'current_date', 'owner', 'logistics', 'Status']].copy()
        display_df.columns = ['Event', 'Date', 'Obligated Party', 'To-Do', 'Status']
        
        if role == 'arbitrator':
            st.info("💡 You can edit the 'To-Do' column directly in the table below.")
            edited = st.data_editor(
                display_df,
                disabled=["Event", "Date", "Obligated Party", "Status"],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "To-Do": st.column_config.TextColumn("To-Do (Logistics)", width="large"),
                    "Status": st.column_config.TextColumn("Status", width="small")
                }
            )
            
            if st.button("💾 Save Logistics / To-Do"):
                # Map edits back to original timeline list
                for index, row in edited.iterrows():
                    evt_name = row['Event']
                    new_todo = row['To-Do']
                    # Find matching event in original timeline list
                    for t in timeline:
                        if t['event'] == evt_name:
                            t['logistics'] = new_todo
                
                save_complex_data("timeline", timeline)
                st.success("Logistics updated successfully.")
                st.rerun()
        else:
            # Read-only for parties
            st.dataframe(
                display_df, 
                use_container_width=True, 
                hide_index=True,
                column_config={"To-Do": st.column_config.TextColumn("To-Do (Logistics)", width="large")}
            )

        # --- ARBITRATOR ACTIONS (Add/Modify) ---
        if role == 'arbitrator':
            st.divider()
            c_mod, c_add = st.columns(2)
            
            # 1. Modify Existing Event (Date Move)
            with c_mod:
                with st.container(border=True):
                    st.write("**Modify Existing Event**")
                    event_to_mod = st.selectbox("Select Event", df['event'].unique(), key="mod_sel")
                    new_date = st.date_input("New Date", key="mod_date")
                    reason = st.text_area("Reason for Change", height=100, key="mod_reason")
                    
                    if st.button("Update Event Date"):
                        for e in timeline:
                            if e.get('event') == event_to_mod:
                                e['current_date'] = str(new_date)
                                if 'history' not in e: e['history'] = []
                                e['history'].append(f"Moved to {new_date}. Reason: {reason}")
                        
                        save_complex_data("timeline", timeline)
                        send_notification(get_party_emails(), "Timetable Updated", f"The Tribunal has moved '{event_to_mod}' to {new_date}.\nReason: {reason}")
                        st.success("Updated & Notified.")
                        st.rerun()

            # 2. Add New Event
            with c_add:
                with st.container(border=True):
                    st.write("**Add New Event**")
                    new_evt_name = st.text_input("Event Name", key="add_name")
                    new_evt_date = st.date_input("Event Date", key="add_date")
                    new_evt_owner = st.selectbox("Obligated Party", ["Claimant", "Respondent", "Tribunal", "Both"], key="add_owner")
                    new_evt_log = st.text_area("Logistics / To-Do", key="add_log", height=100)
                    
                    if st.button("Add to Timeline"):
                        new_entry = {
                            "id": f"evt_{int(datetime.now().timestamp())}",
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
                        send_notification(get_party_emails(), "New Event Added", f"The Tribunal has added a new event: '{new_evt_name}' on {new_evt_date}.")
                        st.success("Event Added & Notified.")
                        st.rerun()

# --- TAB 2: EXTENSION OF TIME (EoT) ---
with tab2:
    st.subheader("Requests for Extension of Time")
    
    # Request Form (Parties)
    if role in ['claimant', 'respondent']:
        with st.form("eot_form"):
            evts = [e['event'] for e in timeline]
            target = st.selectbox("Select Event", evts) if evts else st.text_input("Event Name")
            reason = st.text_area("Reason for Request (Expandable)", height=150)
            prop_date = st.date_input("Proposed New Date")
            
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": target, "requestor": role, "reason": reason, 
                    "proposed_date": str(prop_date), "status": "Pending", "tribunal_decision": ""
                })
                save_complex_data("delays", delays)
                send_notification(['arbitrator'], f"EoT Request: {target}", f"{role.title()} requests delay until {prop_date}.\nReason: {reason}")
                st.success("Request submitted to Tribunal.")
                st.rerun()

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
                    c2.info(f"Decision Note: {req['tribunal_decision']}")

                # Arbitrator Action
                if role == 'arbitrator' and req['status'] == "Pending":
                    decision_reason = c3.text_area("Reasoning (Expandable)", key=f"dec_{i}", height=100)
                    
                    col_app, col_den = c3.columns(2)
                    
                    if col_app.button("Approve", key=f"app_{i}"):
                        # 1. Update Request Status
                        req['status'] = "Approved"
                        req['tribunal_decision'] = decision_reason
                        
                        # 2. Update Actual Timeline
                        for e in timeline:
                            if e.get('event') == req['event']:
                                e['current_date'] = req['proposed_date']
                                if 'history' not in e: e['history'] = []
                                e['history'].append(f"EoT Approved for {req['requestor']}. New Date: {req['proposed_date']}")
                        
                        # 3. Save Everything
                        save_complex_data("delays", delays)
                        save_complex_data("timeline", timeline)
                        
                        # 4. Notify
                        send_notification(get_party_emails(), f"EoT Approved: {req['event']}", f"The Tribunal has approved the delay to {req['proposed_date']}.\nReason: {decision_reason}")
                        st.success("Approved & Updated.")
                        st.rerun()
                        
                    if col_den.button("Deny", key=f"den_{i}"):
                        req['status'] = "Denied"
                        req['tribunal_decision'] = decision_reason
                        save_complex_data("delays", delays)
                        send_notification(get_party_emails(), f"EoT Denied: {req['event']}", f"The Tribunal has denied the delay.\nReason: {decision_reason}")
                        st.warning("Denied.")
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
