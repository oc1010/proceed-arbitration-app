import streamlit as st
from db import load_complex_data, send_notification

st.set_page_config(page_title="Notifications", layout="wide")
role = st.session_state.get('user_role')
if not role: st.error("Access Denied"); st.stop()

with st.sidebar:
    st.write(f"User: **{role.upper()}**")
    st.divider()
    st.page_link("main.py", label="🏠 Home")
    st.page_link("pages/05_Notifications.py", label="🔔 Notifications")
    if role == 'arbitrator':
        st.page_link("pages/03_Smart_Timeline.py", label="📅 Timeline")
    st.divider()
    if st.button("Logout"): st.session_state['user_role'] = None; st.switch_page("main.py")

st.title("🔔 Notification Center")

data = load_complex_data()
all_notifs = data.get("notifications", [])

# 1. INBOX
st.subheader("Received Notifications")
# Filter: User sees msg if their role is in 'to_roles' OR if they are Admin (Arbitrator/LCIA)
my_msgs = [n for n in all_notifs if role in n.get('to_roles', []) or role in ['arbitrator', 'lcia']]

if my_msgs:
    for msg in reversed(my_msgs): # Newest first
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"### {msg['subject']}")
            c1.write(msg.get('body'))
            
            c2.caption(f"📅 {msg['date']}")
            # Format recipients nicely
            recip_str = ", ".join([r.title() for r in msg.get('to_roles', [])])
            c2.info(f"To: {recip_str}")
else:
    st.info("No notifications to display.")

# 2. COMPOSE (Arbitrator Only)
if role in ['arbitrator', 'lcia']:
    st.divider()
    st.subheader("📢 Send New Notification")
    
    with st.form("compose_notif"):
        recips = st.multiselect("Recipients", ["claimant", "respondent"], default=["claimant", "respondent"])
        subj = st.text_input("Subject")
        body = st.text_area("Message (Expandable)", height=150)
        
        if st.form_submit_button("Send Notification"):
            if recips and subj and body:
                send_notification(recips, subj, body)
                st.success("Notification sent successfully.")
                st.rerun()
            else:
                st.error("Please fill all fields.")
