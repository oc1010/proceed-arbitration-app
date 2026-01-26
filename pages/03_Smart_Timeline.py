import streamlit as st
import pandas as pd
import altair as alt
from datetime import date, datetime, timedelta
from db import load_complex_data, save_complex_data, load_responses
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Smart Timeline", layout="wide")

# --- AUTHENTICATION ---
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
        st.page_link("pages/00_Edit_Questionnaire.py", label="✏️ Edit Qs")
        st.page_link("pages/01_Drafting_Engine.py", label="📝 Drafting")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    elif role in ['claimant', 'respondent']:
        st.page_link("pages/00_Fill_Questionnaire.py", label="📝 Fill Qs")
        st.page_link("pages/02_Doc_Production.py", label="📂 Docs")
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
        st.page_link("pages/04_Cost_Management.py", label="💰 Costs")
    st.divider()
    if st.button("Logout"): st.session_state['user_role'] = None; st.switch_page("main.py")

st.title("📅 Phase 4: Procedural Timetable")

# --- EMAIL FUNCTION (Professional & Separate) ---
def send_professional_email(to_emails, subject, body_content):
    """Sends individual professional emails to each recipient."""
    smtp_user = st.secrets.get("ST_MAIL_USER")
    smtp_pass = st.secrets.get("ST_MAIL_PASSWORD")
    smtp_server = st.secrets.get("ST_MAIL_SERVER", "smtp.gmail.com")
    smtp_port = st.secrets.get("ST_MAIL_PORT", 587)

    # Professional Template
    email_body = f"""
    [AUTOMATIC NOTIFICATION - PROCEED ARBITRATION PLATFORM]
    
    Subject: {subject}
    Date: {datetime.now().strftime("%Y-%m-%d %H:%M")}
    
    -------------------------------------------------------
    
    {body_content}
    
    -------------------------------------------------------
    
    PLEASE DO NOT REPLY DIRECTLY TO THIS EMAIL.
    For any queries, please reach out to the Arbitrator directly or log in to the PROCEED platform.
    """

    if smtp_user and smtp_pass and to_emails:
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_pass)
                
                # Send separately to ensure delivery to all, even if duplicates exist
                unique_emails = list(set(to_emails))
                for recipient in unique_emails:
                    msg = MIMEMultipart()
                    msg['From'] = smtp_user
                    msg['To'] = recipient
                    msg['Subject'] = f"[PROCEED] {subject}"
                    msg.attach(MIMEText(email_body, 'plain'))
                    server.send_message(msg)
            
            st.toast(f"📧 Professional notification sent to {len(unique_emails)} parties.", icon="✅")
        except Exception as e:
            st.error(f"⚠️ Email Sending Failed: {e}")
    else:
        st.warning("⚠️ Email credentials missing in Secrets or no recipients found.")

def get_party_emails():
    p2 = load_responses("phase2")
    c = p2.get('claimant', {}).get('contact_email')
    r = p2.get('respondent', {}).get('contact_email')
    return [e for e in [c, r] if e]

# --- DATA AUTO-REPAIR (Fixes KeyError) ---
data = load_complex_data()
timeline = data.get("timeline", [])
delays = data.get("delays", [])

# Repair logic: Runs every time to ensure data integrity
repaired_timeline = []
data_was_fixed = False

for idx, e in enumerate(timeline):
    if not isinstance(e, dict): continue
    
    # fix keys
    if 'current_date' not in e: 
        e['current_date'] = e.get('date', str(date.today()))
        data_was_fixed = True
    if 'original_date' not in e: 
        e['original_date'] = e.get('date', str(date.today()))
        data_was_fixed = True
    if 'logistics' not in e: 
        e['logistics'] = "To Be Determined"
        data_was_fixed = True
    if 'id' not in e: 
        e['id'] = f"evt_{idx}_{int(datetime.now().timestamp())}"
        data_was_fixed = True
        
    repaired_timeline.append(e)

if data_was_fixed:
    timeline = repaired_timeline
    save_complex_data("timeline", timeline)
    st.toast("System: Timeline data structure repaired.")

# --- TAB 1: VISUAL & TABLE ---
tab1, tab2, tab3 = st.tabs(["📊 Visual Schedule", "⏳ Extension of Time Requests", "📝 Change Log"])

with tab1:
    if not timeline:
        st.info("No timeline data. Arbitrator needs to generate PO1.")
    else:
        # 1. CHART
        df = pd.DataFrame(timeline)
        df['Date'] = pd.to_datetime(df['current_date'], errors='coerce')
        df = df.dropna(subset=['Date']).sort_values(by='Date')
        
        # Stagger logic
        heights = []
        for i in range(len(df)):
            val = (i % 3) + 1
            heights.append(val if i % 2 == 0 else val * -1)
        df['Height'] = heights
        df['Zero'] = 0
        df['Status'] = df.apply(lambda x: "Completed" if x['Date'] < pd.to_datetime(date.today()) else "Upcoming", axis=1)

        # Altair
        c = alt.Chart(df).mark_circle(size=120).encode(
            x=alt.X('Date', axis=alt.Axis(format='%d %b %Y', title='Timeline')),
            y='Height', color='Status', tooltip=['event', 'current_date']
        ).properties(height=300)
        t = alt.Chart(df).mark_text(align='center', dy=-15).encode(x='Date', y='Height', text='event')
        st.altair_chart(c + t, use_container_width=True)

        # 2. READ-ONLY TABLE
        st.markdown("### Schedule Details")
        display_df = df[['event', 'current_date', 'owner', 'logistics', 'Status']].copy()
        display_df.columns = ['Event', 'Date', 'Obligated Party', 'To-Do (Logistics)', 'Status']
        st.dataframe(display_df, use_container_width=True, hide_index=True)

        # 3. EDIT FORM (Arbitrator Only - Prevents Refreshing)
        if role == 'arbitrator':
            st.divider()
            c_edit, c_add = st.columns(2)
            
            # EDIT EXISTING
            with c_edit:
                with st.container(border=True):
                    st.subheader("✏️ Edit Event Details")
                    evt_opts = [e['event'] for e in timeline]
                    if evt_opts:
                        target = st.selectbox("Select Event to Edit", evt_opts)
                        
                        # Find current data
                        curr = next((x for x in timeline if x['event'] == target), {})
                        c_date_val = datetime.strptime(curr.get('current_date', str(date.today())), "%Y-%m-%d").date()
                        c_todo_val = curr.get('logistics', '')
                        
                        with st.form("edit_existing"):
                            # Big expandable box for To-Do
                            new_todo = st.text_area("To-Do / Logistics", value=c_todo_val, height=150)
                            new_date = st.date_input("Date", value=c_date_val)
                            reason = st.text_input("Reason for Date Change (Optional)")
                            
                            if st.form_submit_button("💾 Save Changes"):
                                changed = False
                                for e in timeline:
                                    if e['event'] == target:
                                        e['logistics'] = new_todo
                                        if str(new_date) != e['current_date']:
                                            e['current_date'] = str(new_date)
                                            if 'history' not in e: e['history'] = []
                                            e['history'].append(f"Moved to {new_date}. Reason: {reason}")
                                            changed = True
                                save_complex_data("timeline", timeline)
                                if changed:
                                    send_professional_email(get_party_emails(), "Timeline Update", f"Event '{target}' moved to {new_date}.\nReason: {reason}")
                                st.success("Updated!")
                                st.rerun()

            # ADD NEW
            with c_add:
                with st.container(border=True):
                    st.subheader("➕ Add New Event")
                    with st.form("add_new"):
                        n_name = st.text_input("Event Name")
                        n_date = st.date_input("Date")
                        n_owner = st.selectbox("Obligated Party", ["Claimant", "Respondent", "Tribunal", "Both"])
                        # Big expandable box
                        n_todo = st.text_area("To-Do / Logistics", height=150)
                        
                        if st.form_submit_button("Add to Timeline"):
                            new_e = {
                                "id": f"new_{int(datetime.now().timestamp())}",
                                "event": n_name, "current_date": str(n_date),
                                "original_date": str(n_date), "owner": n_owner,
                                "logistics": n_todo, "status": "Upcoming", "history": ["Added manually"]
                            }
                            timeline.append(new_e)
                            save_complex_data("timeline", timeline)
                            send_professional_email(get_party_emails(), "New Event Added", f"The Tribunal has added '{n_name}' on {n_date}.\nDetails: {n_todo}")
                            st.success("Event Added.")
                            st.rerun()

# --- TAB 2: EoT REQUESTS ---
with tab2:
    st.subheader("Extension of Time Requests")
    
    if role in ['claimant', 'respondent']:
        with st.form("eot_req"):
            # Big expandable box
            evt_list = [e['event'] for e in timeline]
            tgt = st.selectbox("Select Event", evt_list) if evt_list else st.text_input("Event Name")
            reason = st.text_area("Reason for Request (Detailed)", height=200)
            prop = st.date_input("Proposed Date")
            
            if st.form_submit_button("Submit Request"):
                delays.append({
                    "event": tgt, "requestor": role, "reason": reason,
                    "proposed_date": str(prop), "status": "Pending", "tribunal_decision": ""
                })
                save_complex_data("delays", delays)
                # Send email notification to Arbitrator? (Not implemented here, but parties get notified on decision)
                st.success("Request Submitted.")
                st.rerun()

    if delays:
        for i, d in enumerate(delays):
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                c1.write(f"**{d['event']}** (Req: {d['requestor']})")
                c1.write(f"Proposed: {d['proposed_date']}")
                with c1.expander("View Reason"):
                    st.write(d['reason'])
                
                c2.write(f"Status: **{d['status']}**")
                
                if role == 'arbitrator' and d['status'] == "Pending":
                    with st.form(f"dec_form_{i}"):
                        # Big expandable box for decision
                        dec_note = st.text_area("Decision Reasoning", height=150)
                        c_a, c_d = st.columns(2)
                        app = c_a.form_submit_button("Approve")
                        den = c_d.form_submit_button("Deny")
                        
                        if app:
                            d['status'] = "Approved"
                            d['tribunal_decision'] = dec_note
                            # Update Timeline
                            for t in timeline:
                                if t['event'] == d['event']:
                                    t['current_date'] = d['proposed_date']
                                    if 'history' not in t: t['history'] = []
                                    t['history'].append(f"EoT Approved. New: {d['proposed_date']}")
                            save_complex_data("timeline", timeline)
                            save_complex_data("delays", delays)
                            send_professional_email(get_party_emails(), f"EoT Approved: {d['event']}", f"Delay approved.\n\nTribunal Reasoning:\n{dec_note}")
                            st.success("Approved.")
                            st.rerun()
                            
                        if den:
                            d['status'] = "Denied"
                            d['tribunal_decision'] = dec_note
                            save_complex_data("delays", delays)
                            send_professional_email(get_party_emails(), f"EoT Denied: {d['event']}", f"Delay denied.\n\nTribunal Reasoning:\n{dec_note}")
                            st.warning("Denied.")
                            st.rerun()

# --- TAB 3: LOG ---
with tab3:
    st.write("### Change Log")
    log_data = []
    for t in timeline:
        for h in t.get('history', []):
            log_data.append({"Event": t['event'], "Change": h})
    if log_data:
        st.dataframe(pd.DataFrame(log_data), use_container_width=True)
