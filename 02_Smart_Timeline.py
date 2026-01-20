import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from db import load_timeline, save_timeline

st.set_page_config(page_title="Smart Timeline", layout="wide")

if st.session_state.get('user_role') is None:
    st.error("Please login.")
    st.stop()

# LOAD AND CLEAN DATA
raw_data = load_timeline()
df = pd.DataFrame(raw_data)

if df.empty:
    st.info("No schedule initialized. Arbitrator must generate PO1 first.")
    st.stop()

# --- VIZ ---
df['date'] = pd.to_datetime(df['date'])
df = df.sort_values(by="date")
pattern = [1, -1, 0.5, -0.5, 1.5, -1.5]
df['y_pos'] = (pattern * (len(df)//len(pattern)+1))[:len(df)]
color_map = {"Claimant": "#2980B9", "Respondent": "#D35400", "Tribunal": "#2C3E50", "All": "#7F8C8D"}
df['color'] = df['owner'].map(color_map).fillna("grey")

fig = go.Figure()
fig.add_trace(go.Scatter(x=[df['date'].min(), df['date'].max()], y=[0,0], mode="lines", line=dict(color="#BDC3C7", width=3)))

for i, row in df.iterrows():
    m = dict(size=12, color=row['color'])
    if row.get('status') == 'Pending': m.update(dict(line=dict(color='#C0392B', width=2), symbol='circle-open'))
    fig.add_trace(go.Scatter(x=[row['date']], y=[0], mode="markers", marker=m, name=row['event']))

for _, row in df.iterrows():
    lbl = f"<b>{row['event']}</b><br>{row['date'].strftime('%d %b')}"
    if row.get('status') == 'Pending': 
        n = pd.to_datetime(row.get('new_date', '')).strftime('%d %b') if pd.notna(row.get('new_date')) else "?"
        lbl += f"<br><span style='color:#C0392B'>(Req: {n})</span>"
    fig.add_trace(go.Scatter(x=[row['date'], row['date']], y=[0, row['y_pos']], mode="lines", line=dict(color=row['color'], width=1)))
    fig.add_trace(go.Scatter(x=[row['date']], y=[row['y_pos']], mode="text", text=[lbl], textposition="top center" if row['y_pos']>0 else "bottom center"))

fig.update_layout(height=400, showlegend=False, yaxis=dict(visible=False), xaxis=dict(visible=False), margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- MANAGE ---
if st.session_state['user_role'] == 'arbitrator':
    st.subheader("Tribunal Controls")
    pending = df[df['status'] == 'Pending']
    if pending.empty: st.info("No pending requests.")
    else:
        for i, row in pending.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([4,1])
                c1.write(f"**{row['event']}** request.")
                if c2.button("Approve", key=f"app_{i}"):
                    df.at[i, 'date'] = pd.to_datetime(row['new_date'])
                    df.at[i, 'status'] = 'Approved'
                    save_timeline(df.to_dict(orient="records"))
                    st.rerun()
else:
    st.subheader("Request Extension")
    evt = st.selectbox("Event", df['event'].unique())
    new_d = st.date_input("New Date")
    if st.button("Submit Request"):
        idx = df[df['event']==evt].index[0]
        df.at[idx, 'status'] = 'Pending'
        df.at[idx, 'new_date'] = str(new_d)
        save_timeline(df.to_dict(orient="records"))
        st.success("Request sent.")
