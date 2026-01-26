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
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    if role == 'arbitrator':
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    # ...
    st.divider()
    if st.button("Logout"): st.session_state['user_role'] = None; st.switch_page("main.py")

st.title("📅 Phase 4: Procedural Timetable")

# --- DATA LOAD & REPAIR ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

cleaned_timeline = []
needs_save = False
for idx, e in enumerate(timeline):
    if not isinstance(e, dict): continue
    if 'current_date' not in e: e['current_date'] = e.get('date', str(date.today())); needs_save = True
    if 'original_date' not in e: e['original_date'] = e.get('date', str(date.today())); needs_save = True
    if 'logistics' not in e: e['logistics'] = "To Be Determined"; needs_save = True
    if 'id' not in e: e['id'] = f"evt_{idx}_{int(datetime.now().timestamp())}"; needs_save = True
    cleaned_timeline.append(e)

if needs_save:
    timeline = cleaned_timeline
    save_complex_data("timeline", timeline)

def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    emails = []
    if c: emails.append(c)
    if r: emails.append(r)
    return emails

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["📊 Visual Schedule", "⏳ Extension of Time Requests", "📝 Change Log"])

with tab1:
    if not timeline:
        st.warning("No procedural timetable found. Arbitrator must generate PO1 first.")
    else:
        df = pd.DataFrame(timeline)
        df['Date'] = pd.to_datetime(df['current_date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values(by='Date')
        
        heights = []
        for i in range(len(df)):
            val = (i % 3) + 1
            heights.append(val if i % 2 == 0 else val * -1)
        df['Height'] = heights
        df['Zero'] = 0
        df['Status'] = df.apply(lambda x: "Completed" if x['Date'] < pd.to_datetime(date.today()) else "Upcoming", axis=1)

        c = alt.Chart(df).mark_circle(size=120).encode(
            x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
            y='Height', color='Status', tooltip=['event', 'current_date']
        ).properties(height=300)
        t = alt.Chart(df).mark_text(align='center', dy=-15).encode(x='Date', y='Height', text='event')
        st.altair_chart(c + t, use_container_width=True)

        st.markdown("### Schedule Details")
        display_df = df[['event', 'current_date', 'owner', 'logistics', 'Status']].copy()
        display_df.columns = ['Event', 'Date', 'Obligated Party', 'To-Do (Logistics)', 'Status']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        if role == 'arbitrator':
            st.divider()
            c_edit, c_add = st.columns(2)
            
            with c_edit:
                with st.container(border=True):
                    st.subheader("✏️ Edit Event Details")
                    evt_opts = [e['event'] for e in timeline]
                    if evt_opts:
                        target = st.selectbox("Select Event to Edit", evt_opts)
                        curr = next((x for x in timeline if x['event'] == target), {})
                        c_date = datetime.strptime(curr.get('current_date', str(date.today())), "%Y-%m-%d").date()
                        c_log = curr.get('logistics', '')
                        
                        with st.form("edit_form"):
                            new_date = st.date_input("Date", value=c_date)
                            new_log = st.text_area("To-Do / Logistics", value=c_log, height=150)
                            reason = st.text_input("Reason (if moving date)")
                            
                            if st.form_submit_button("💾 Save Changes"):
                                changed_date = False
                                for e in timeline:
                                    if e['event'] == target:
                                        e['logistics'] = new_log
                                        if str(new_date) != e['current_date']:
                                            e['current_date'] = str(new_date)
                                            changed_date = True
                                            if 'history' not in e: e['history'] = []
                                            e['history'].append(f"Moved to {new_date}. Reason: {reason}")
                                save_complex_data("timeline", timeline)
                                if changed_date:
                                    send_email_notification(get_party_emails(), "Timetable Update", f"Event '{target}' moved to {new_date}.\nReason: {reason}")
                                st.success("Updated.")
                                st.rerun()

            with c_add:
                with st.container(border=True):
                    st.subheader("➕ Add New Event")
                    with st.form("add_form"):
                        n_name = st.text_input("Event Name")
                        n_date = st.date_input("Date")
                        n_owner = st.selectbox("Obligated Party", ["Claimant", "Respondent", "Tribunal", "Both"])
                        n_log = st.text_area("To-Do / Logistics", height=150)
                        if st.form_submit_button("Add Event"):
                            new_e = {"id": f"new_{int(datetime.now().timestamp())}", "event": n_name, "current_date": str(n_date), "original_date": str(n_date), "owner": n_owner, "logistics": n_log, "status": "Upcoming", "history": ["Added manually"]}
                            timeline.append(new_e)
                            save_complex_data("timeline", timeline)
                            send_email_notification(get_party_emails(), "New Event Added", f"Added: '{n_name}' on {n_date}.\nDetails: {n_log}")
                            st.success("Event Added.")
                            st.rerun()

with tab2:
    st.subheader("Requests for Extension of Time")
    if role in ['claimant', 'respondent']:
        with st.form("eot_req"):
            tgt = st.selectbox("Event", [e['event'] for e in timeline])
            rsn = st.text_area("Reason for Request", height=150)
            prop = st.date_input("Proposed Date")
            if st.form_submit_button("Submit Request"):
                delays.append({"event": tgt, "requestor": role, "reason": rsn, "proposed_date": str(prop), "status": "Pending", "tribunal_decision": ""})
                save_complex_data("delays", delays)
                st.success("Submitted.")
                st.rerun()

    if delays:
        for i, d in enumerate(delays):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{d['event']}**")
                c1.caption(f"Req: {d['requestor']} | New Date: {d['proposed_date']}")
                with c1.expander("View Reason"): st.write(d['reason'])
                c2.write(f"Status: **{d['status']}**")
                if d.get('tribunal_decision'): c2.info(f"Note: {d['tribunal_decision']}")
                
                if role == 'arbitrator' and d['status'] == "Pending":
                    with st.form(f"dec_{i}"):
                        dec_note = st.text_area("Decision Reasoning", height=150)
                        c_a, c_d = st.columns(2)
                        app = c_a.form_submit_button("Approve")
                        den = c_d.form_submit_button("Deny")
                        
                        if app:
                            d['status'] = "Approved"; d['tribunal_decision'] = dec_note
                            for t in timeline:
                                if t['event'] == d['event']: t['current_date'] = d['proposed_date']
                            save_complex_data("timeline", timeline); save_complex_data("delays", delays)
                            send_email_notification(get_party_emails(), f"EoT Approved: {d['event']}", f"Approved.\n\nTribunal Note:\n{dec_note}")
                            st.success("Approved."); st.rerun()
                        if den:
                            d['status'] = "Denied"; d['tribunal_decision'] = dec_note
                            save_complex_data("delays", delays)
                            send_email_notification(get_party_emails(), f"EoT Denied: {d['event']}", f"Denied.\n\nTribunal Note:\n{dec_note}")
                            st.warning("Denied."); st.rerun()
