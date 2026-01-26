import streamlit as st
import pandas as pd
from datetime import datetime
from db import load_complex_data, send_notification

st.set_page_config(page_title="Notifications", layout="wide")
role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

# --- SIDEBAR ---
with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    if role == 'arbitrator':
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
    st.divider()
    if st.button("Logout"): st.session_state['user_role'] = None; st.switch_page("main.py")

st.title("🔔 Notifications & Alerts")

data = load_complex_data()
all_notifs = data.get("notifications", [])

# 1. MY NOTIFICATIONS (Inbox)
st.subheader("Inbox")
# Filter: Show if role is in 'to_roles' OR if user is arbitrator/lcia (they see everything sent)
my_msgs = [n for n in all_notifs if role in n.get('to_roles', []) or role in ['arbitrator', 'lcia']]

if my_msgs:
    # Show newest first
    for msg in reversed(my_msgs):
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.write(f"**{msg['subject']}**")
            c1.caption(msg.get('body'))
            c2.caption(f"{msg['date']}")
            if role in ['arbitrator', 'lcia']:
                c2.info(f"To: {msg['to_roles']}")
else:
    st.info("No notifications found.")

# 2. COMPOSE (Arbitrator/LCIA Only)
if role in ['arbitrator', 'lcia']:
    st.divider()
    st.subheader("📢 Send Notification")
    
    with st.form("send_note"):
        recipients = st.multiselect("Recipients", ["claimant", "respondent"], default=["claimant", "respondent"])
        subj = st.text_input("Subject")
        body = st.text_area("Message Body", height=150)
        
        if st.form_submit_button("Send Notification"):
            if recipients and subj and body:
                send_notification(recipients, subj, body)
                st.success("Sent!")
                st.rerun()
            else:
                st.error("Please fill all fields.")
