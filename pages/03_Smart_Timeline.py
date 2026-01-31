import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime
from db import load_complex_data, save_complex_data, send_email_notification

st.set_page_config(page_title="Smart Timeline", layout="wide")

role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    if role == 'arbitrator':
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    st.divider()
    if st.button("Logout"): 
        st.session_state['user_role'] = None
        st.switch_page("main.py")

st.title("📅 Phase 4: Procedural Timetable")

# --- LOAD DATA ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

# --- LOGIC: AUTO-UPDATE STATUS [cite: 124-126] ---
# Check deadlines against today to trigger "Awaiting Compliance"
today = date.today()
dirty = False

for event in timeline:
    # Ensure keys exist [cite: 54-63]
    if 'milestone' not in event: event['milestone'] = event.get('event', 'Untitled')
    if 'deadline' not in event: event['deadline'] = event.get('current_date', str(today))
    if 'responsible_party' not in event: event['responsible_party'] = event.get('owner', 'All')
    
    # Status Logic
    d_dead = datetime.strptime(event['deadline'], "%Y-%m-%d").date()
    current_status = event.get('compliance_status', 'Commenced and Pending')
    
    if current_status not in ['Completed', 'Pending Determination']:
        if today > d_dead:
            if current_status != "Awaiting Compliance":
                event['compliance_status'] = "Awaiting Compliance" # Turns RED
                dirty = True
        else:
            if current_status == "Awaiting Compliance": # Reset if date moved forward
                event['compliance_status'] = "Commenced and Pending"
                dirty = True

if dirty:
    save_complex_data("timeline", timeline)

# --- TABS ---
t1, t2 = st.tabs(["📊 Main Schedule", "⏳ Extension Requests"])

with t1:
    if not timeline:
        st.warning("No timetable set. Generate PO1 first.")
    else:
        # VISUAL CHART
        df = pd.DataFrame(timeline)
        df['Date'] = pd.to_datetime(df['deadline'])
        
        c = alt.Chart(df).mark_circle(size=200).encode(
            x='Date', y='responsible_party', 
            color=alt.Color('compliance_status', scale=alt.Scale(domain=['Completed', 'Awaiting Compliance', 'Commenced and Pending'], range=['blue', 'red', 'green'])),
            tooltip=['milestone', 'deadline', 'compliance_status']
        ).interactive()
        st.altair_chart(c, use_container_width=True)
        
        # DETAILED LIST
        for i, e in enumerate(timeline):
            with st.container(border=True):
                c1, c2, c3 = st.columns([3, 2, 2])
                c1.markdown(f"### {e['milestone']}")
                c1.caption(f"Responsible: **{e['responsible_party']}**")
                
                # Deadline & Days Remaining [cite: 65]
                d_dead = datetime.strptime(e['deadline'], "%Y-%m-%d").date()
                days_rem = (d_dead - today).days
                c2.write(f"**Deadline:** {e['deadline']}")
                if days_rem < 0:
                    c2.markdown(f":red[**{abs(days_rem)} Days Overdue**]")
                else:
                    c2.markdown(f":green[**{days_rem} Days Remaining**]")
                
                # Compliance Status [cite: 58]
                stat = e.get('compliance_status', 'Pending')
                s_color = "red" if stat == "Awaiting Compliance" else "blue" if stat == "Completed" else "green"
                c3.markdown(f"Status: :{s_color}[**{stat}**]")
                
                # Manual Override (Tribunal)
                if role == 'arbitrator':
                    new_s = c3.selectbox("Set Status", ["Commenced and Pending", "Completed", "Pending Determination"], key=f"s_{i}")
                    if c3.button("Update", key=f"u_{i}"):
                        e['compliance_status'] = new_s
                        save_complex_data("timeline", timeline)
                        st.rerun()

with t2:
    st.subheader("Requests for Extension of Time (EoT)")
    st.info("Approved delays are tracked by the AI for Cost Penalties (0.5% / day).")
    
    # REQUEST FORM (Parties)
    if role in ['claimant', 'respondent']:
        with st.form("req_delay"):
            target = st.selectbox("Milestone", [e['milestone'] for e in timeline])
            reason = st.text_area("Reason")
            new_date = st.date_input("Proposed Deadline")
            if st.form_submit_button("Submit EoT Request"):
                delays.append({
                    "event": target, "requestor": role, "reason": reason,
                    "proposed_date": str(new_date), "status": "Pending"
                })
                save_complex_data("delays", delays)
                st.success("Request Submitted.")
                st.rerun()

    # REVIEW LIST
    for i, d in enumerate(delays):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{d['event']}** (Req by: {d['requestor']})")
            c1.caption(f"Proposed: {d['proposed_date']} | Reason: {d['reason']}")
            c2.write(f"Status: **{d['status']}**")
            
            # TRIBUNAL DECISION
            if role == 'arbitrator' and d['status'] == 'Pending':
                col_a, col_d = st.columns(2)
                if col_a.button("Approve", key=f"app_{i}"):
                    d['status'] = "Approved" # AI Counts this
                    # Update actual timeline
                    for t in timeline:
                        if t['milestone'] == d['event']:
                            t['deadline'] = d['proposed_date']
                            t['compliance_status'] = "Commenced and Pending" # Reset red flag
                            if 'amendment_history' not in t: t['amendment_history'] = []
                            t['amendment_history'].append(f"Extended to {d['proposed_date']}")
                    save_complex_data("timeline", timeline)
                    save_complex_data("delays", delays)
                    st.rerun()
                    
                if col_d.button("Deny", key=f"den_{i}"):
                    d['status'] = "Denied"
                    save_complex_data("delays", delays)
                    st.rerun()
