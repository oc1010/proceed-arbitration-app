import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from db import load_complex_data, save_complex_data, load_responses, send_notification
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
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    
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

# --- LOAD DATA & AUTO-REPAIR ---
# We repair data BEFORE doing anything else to prevent KeyErrors
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

data_needs_save = False
cleaned_timeline = []
for idx, e in enumerate(timeline):
    if not isinstance(e, dict): continue
    
    # Check and fix missing keys
    if 'current_date' not in e:
        e['current_date'] = e.get('date', str(date.today()))
        data_needs_save = True
    if 'original_date' not in e:
        e['original_date'] = e.get('date', str(date.today()))
        data_needs_save = True
    if 'logistics' not in e:
        e['logistics'] = "To Be Determined"
        data_needs_save = True
    if 'id' not in e:
        e['id'] = f"evt_{idx}_{int(datetime.now().timestamp())}"
        data_needs_save = True
        
    cleaned_timeline.append(e)

if data_needs_save:
    timeline = cleaned_timeline
    save_complex_data("timeline", timeline)
    st.toast("System: Timeline data structure normalized.")

# --- HELPER: GET PARTY EMAILS ---
def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- TAB 1: VISUAL & TABLE ---
tab1, tab2, tab3 = st.tabs(["📊 Visual Schedule", "⏳ Extension of Time Requests", "📝 Change Log"])

with tab1:
    if not timeline:
        st.warning("No procedural timetable found. Arbitrator must generate PO1 first.")
    else:
        # Prepare Data
        df = pd.DataFrame(timeline)
        
        # Parse Dates
        df['Date'] = pd.to_datetime(df['current_date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df = df.sort_values(by='Date')
        
        # Staggered Heights
        heights = []
        for i in range(len(df)):
            val = (i % 3) + 1
            heights.append(val if i % 2 == 0 else val * -1)
        df['Height'] = heights
        df['Zero'] = 0
        df['Status'] = df.apply(lambda x: "Completed" if x['Date'] < pd.to_datetime(date.today()) else "Upcoming", axis=1)

        # Altair Chart
        chart = alt.Chart(df).mark_circle(size=120).encode(
            x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
            y='Height', 
            color=alt.Color('Status', scale=alt.Scale(domain=['Completed', 'Upcoming'], range=['#28a745', '#007bff'])),
            tooltip=['event', 'current_date', 'owner', 'logistics']
        ).properties(height=300)
        
        # Add labels
        text = alt.Chart(df).mark_text(align='center', baseline='middle', dy=-15).encode(
            x='Date', y='Height', text='event'
        )
        
        st.altair_chart(chart + text, use_container_width=True)

        # TABLE (Read-Only to prevent refreshing)
        st.markdown("### Schedule Details")
        display_df = df[['event', 'current_date', 'owner', 'logistics', 'Status']].copy()
        display_df.columns = ['Event', 'Date', 'Obligated Party', 'To-Do (Logistics)', 'Status']
        
        st.dataframe(
            display_df, 
            use_container_width=True, 
            hide_index=True,
            column_config={
                "To-Do (Logistics)": st.column_config.TextColumn("To-Do", width="large"),
                "Status": st.column_config.TextColumn("Status", width="small")
            }
        )

        # ARBITRATOR ACTIONS (Forms prevent page refresh)
        if role == 'arbitrator':
            st.divider()
            st.subheader("Manage Timetable")
            
            c_edit, c_add = st.columns(2)
            
            # 1. EDIT EXISTING EVENT (Logistics/To-Do or Date)
            with c_edit:
                with st.container(border=True):
                    st.write("✏️ **Edit Event Details**")
                    # Select event to edit
                    evt_names = [e['event'] for e in timeline]
                    if evt_names:
                        target = st.selectbox("Select Event", evt_names, key="edit_sel")
                        
                        # Find current values
                        curr_evt = next((e for e in timeline if e['event'] == target), {})
                        curr_todo = curr_evt.get('logistics', '')
                        curr_date = datetime.strptime(curr_evt.get('current_date', str(date.today())), "%Y-%m-%d").date()
                        
                        with st.form("edit_evt_form"):
                            new_date = st.date_input("Date", value=curr_date)
                            new_todo = st.text_area("To-Do / Logistics (Expandable)", value=curr_todo, height=150)
                            change_reason = st.text_input("Reason for Change (if date moved)")
                            
                            if st.form_submit_button("💾 Save Changes"):
                                date_changed = False
                                for e in timeline:
                                    if e['event'] == target:
                                        e['logistics'] = new_todo
                                        if str(new_date) != e['current_date']:
                                            e['current_date'] = str(new_date)
                                            date_changed = True
                                            if 'history' not in e: e['history'] = []
                                            e['history'].append(f"Moved to {new_date}. Reason: {change_reason}")
                                
                                save_complex_data("timeline", timeline)
                                
                                if date_changed:
                                    send_notification(get_party_emails(), "Timetable Update", f"Event '{target}' moved to {new_date}.\nReason: {change_reason}")
                                    st.success("Date & Logistics Updated.")
                                else:
                                    st.success("Logistics Updated.")
                                st.rerun()

            # 2. ADD NEW EVENT
            with c_add:
                with st.container(border=True):
                    st.write("➕ **Add New Event**")
                    with st.form("add_evt_form"):
                        n_name = st.text_input("Event Name")
                        n_date = st.date_input("Date")
                        n_owner = st.selectbox("Obligated Party", ["Claimant", "Respondent", "Tribunal", "Both"])
                        n_todo = st.text_area("To-Do / Logistics", height=100)
                        
                        if st.form_submit_button("Add Event"):
                            new_entry = {
                                "id": f"evt_{int(datetime.now().timestamp())}",
                                "event": n_name,
                                "original_date": str(n_date),
                                "current_date": str(n_date),
                                "owner": n_owner,
                                "logistics": n_todo,
                                "status": "Upcoming",
                                "history": ["Created manually"]
                            }
                            timeline.append(new_entry)
                            save_complex_data("timeline", timeline)
                            send_notification(get_party_emails(), "New Event Added", f"The Tribunal has added '{n_name}' on {n_date}.")
                            st.success("Event Added.")
                            st.rerun()

# --- TAB 2: EoT REQUESTS ---
with tab2:
    st.subheader("Requests for Extension of Time")
    
    # Request Form
    if role in ['claimant', 'respondent']:
        with st.form("eot_req"):
            t_evt = st.selectbox("Select Event", [e['event'] for e in timeline])
            t_reason = st.text_area("Reason for Request (Expandable)", height=150)
            t_date = st.date_input("Proposed Date")
            
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": t_evt, "requestor": role, "reason": t_reason,
                    "proposed_date": str(t_date), "status": "Pending", "tribunal_decision": ""
                })
                save_complex_data("delays", delays)
                send_notification(['arbitrator'], f"EoT Request: {t_evt}", f"{role} requests delay until {t_date}.\nReason: {t_reason}")
                st.success("Submitted.")
                st.rerun()

    # Review & Decision
    if delays:
        for i, req in enumerate(delays):
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                c1.markdown(f"**{req['event']}**")
                c1.caption(f"Requestor: {req['requestor'].upper()} | Proposed: {req['proposed_date']}")
                c1.write(f"Reason: {req['reason']}")
                
                c2.markdown(f"**Status:** `{req['status']}`")
                if req.get('tribunal_decision'):
                    c2.info(f"Decision Note: {req['tribunal_decision']}")
                
                # Decision Form (Arbitrator)
                if role == 'arbitrator' and req['status'] == "Pending":
                    with st.form(f"dec_form_{i}"):
                        d_reason = st.text_area("Decision Reasoning", height=100)
                        c_app, c_den = st.columns(2)
                        
                        approved = c_app.form_submit_button("Approve")
                        denied = c_den.form_submit_button("Deny")
                        
                        if approved:
                            req['status'] = "Approved"
                            req['tribunal_decision'] = d_reason
                            # Update Timeline Immediately
                            for t in timeline:
                                if t['event'] == req['event']:
                                    t['current_date'] = req['proposed_date']
                                    if 'history' not in t: t['history'] = []
                                    t['history'].append(f"EoT Approved. New Date: {req['proposed_date']}")
                            
                            save_complex_data("timeline", timeline)
                            save_complex_data("delays", delays)
                            send_notification(get_party_emails(), f"EoT Approved: {req['event']}", f"Delay approved.\nNote: {d_reason}")
                            st.success("Approved."); st.rerun()
                            
                        if denied:
                            req['status'] = "Denied"
                            req['tribunal_decision'] = d_reason
                            save_complex_data("delays", delays)
                            send_notification(get_party_emails(), f"EoT Denied: {req['event']}", f"Delay denied.\nReason: {d_reason}")
                            st.warning("Denied."); st.rerun()
    else:
        st.info("No pending requests.")

# --- TAB 3: LOG ---
with tab3:
    st.subheader("Change Log")
    log = []
    for t in timeline:
        for h in t.get('history', []):
            log.append({"Event": t['event'], "Change": h})
    if log: st.dataframe(pd.DataFrame(log), use_container_width=True)
    else: st.caption("No changes recorded.")
