import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from db import load_complex_data, save_complex_data, load_responses
import json

st.set_page_config(page_title="Smart Timeline", layout="wide")
role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

st.title("📅 Phase 4: Timeline & Logistics")

# --- LOAD DATA ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", []) # List of {event, requestor, reason, status, tribunal_reason}

# --- EMAIL NOTIFICATION SIMULATION ---
def notify_parties(subject, body):
    # Fetch emails from Phase 2 responses
    p2 = load_responses("phase2")
    c_email = p2.get('claimant', {}).get('contact_email', 'claimant@example.com')
    r_email = p2.get('respondent', {}).get('contact_email', 'respondent@example.com')
    
    st.toast(f"📧 Sending Email to: {c_email}, {r_email}", icon="📨")
    st.info(f"**Email Sent:**\n\n**Subject:** {subject}\n\n{body}")

# --- TAB STRUCTURE ---
tab_vis, tab_log, tab_delay = st.tabs(["📊 Visual Timetable", "📍 Logistics & Reminders", "⏳ Delay Requests"])

# --- 1. HORIZONTAL TIMELINE ---
with tab_vis:
    if not timeline:
        st.warning("No timeline data found. Generate PO1 to sync dates.")
    else:
        # Prepare Data
        df = pd.DataFrame(timeline)
        df['start'] = pd.to_datetime(df['date'])
        df['end'] = df['start'] + timedelta(days=1) # Width for chart
        
        # Determine Status
        today = pd.to_datetime(date.today())
        def get_status(row):
            if row.get('status') == 'Completed': return "Completed"
            if row['start'] < today: return "Overdue"
            return "Upcoming"
        
        df['calc_status'] = df.apply(get_status, axis=1)
        
        # Horizontal Chart using Altair (Gantt style)
        chart = alt.Chart(df).mark_bar().encode(
            x='start',
            x2='end',
            y='event',
            color=alt.Color('calc_status', scale=alt.Scale(domain=['Completed', 'Upcoming', 'Overdue'], range=['green', 'blue', 'red'])),
            tooltip=['date', 'event', 'owner', 'logistics']
        ).properties(height=300)
        
        st.altair_chart(chart, use_container_width=True)
        
        # Detailed Table Below
        st.markdown("### Detailed Schedule")
        
        # Arbitrator Editing
        if role == 'arbitrator':
            edited_tl = st.data_editor(df, num_rows="dynamic", use_container_width=True)
            if st.button("Update Timetable"):
                # Save logic (simplified conversion back to json)
                new_tl = json.loads(edited_tl.to_json(orient="records", date_format="iso"))
                # Clean up altair columns before saving
                cleaned_tl = []
                for i in new_tl:
                    clean_item = {k: v for k, v in i.items() if k not in ['start', 'end', 'calc_status']}
                    cleaned_tl.append(clean_item)
                
                save_complex_data("timeline", cleaned_tl)
                notify_parties("Procedural Timetable Modified", "The Tribunal has updated the procedural timetable. Please check the portal.")
                st.success("Updated & Notified")
        else:
            st.dataframe(df[['date', 'event', 'owner', 'calc_status', 'logistics']], use_container_width=True)

# --- 2. LOGISTICS & REMINDERS ---
with tab_log:
    st.subheader("Event Logistics & Reminders")
    
    # Find next upcoming event
    upcoming = [e for e in timeline if datetime.strptime(e['date'], "%Y-%m-%d").date() >= date.today()]
    if upcoming:
        next_ev = sorted(upcoming, key=lambda x: x['date'])[0]
        days_left = (datetime.strptime(next_ev['date'], "%Y-%m-%d").date() - date.today()).days
        
        st.info(f"**Next Event:** {next_ev['event']} ({next_ev['date']})")
        
        c1, c2 = st.columns(2)
        c1.metric("Days Remaining", f"{days_left} Days")
        c2.write(f"**Action Required by:** {next_ev['owner']}")
        
        st.markdown(f"**Logistics Instructions:**\n{next_ev.get('logistics', 'No specific instructions.')}")
        
        if role == 'arbitrator':
            if st.button("🔔 Trigger Reminder Notification"):
                body = f"Reminder: {next_ev['event']} is due in {days_left} days.\nLogistics: {next_ev.get('logistics', '-')}"
                notify_parties(f"Reminder: {next_ev['event']}", body)
                
    else:
        st.success("No upcoming events scheduled.")

# --- 3. DELAY REQUESTS ---
with tab_delay:
    st.subheader("Extension of Time Requests")
    
    if role != 'arbitrator':
        with st.form("req_delay"):
            target_event = st.selectbox("Select Event", [e['event'] for e in timeline])
            reason = st.text_area("Reason for Delay Request")
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": target_event, "requestor": role, "reason": reason, 
                    "status": "Pending", "tribunal_reason": ""
                })
                data['delays'] = delays
                save_complex_data("delays", delays) 
                st.success("Request submitted to Tribunal.")
                
    # Shared View of Requests
    if delays:
        for i, req in enumerate(delays):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.write(f"**{req['event']}** (Req by: {req['requestor']})")
                c1.caption(f"Reason: {req['reason']}")
                c2.write(f"Status: **{req['status']}**")
                
                if role == 'arbitrator' and req['status'] == "Pending":
                    reason_arb = c3.text_input("Decision Reason", key=f"r_{i}")
                    if c3.button("Approve", key=f"a_{i}"):
                        req['status'] = "Approved"
                        req['tribunal_reason'] = reason_arb
                        data['delays'] = delays
                        save_complex_data("delays", delays)
                        notify_parties(f"Extension Approved: {req['event']}", f"Approved. Reason: {reason_arb}")
                        st.rerun()
                    if c3.button("Deny", key=f"d_{i}"):
                        req['status'] = "Denied"
                        req['tribunal_reason'] = reason_arb
                        data['delays'] = delays
                        save_complex_data("delays", delays)
                        notify_parties(f"Extension Denied: {req['event']}", f"Denied. Reason: {reason_arb}")
                        st.rerun()
                elif req.get('tribunal_reason'):
                    c3.info(f"Tribunal Note: {req['tribunal_reason']}")
    else:
        st.info("No active delay requests.")
