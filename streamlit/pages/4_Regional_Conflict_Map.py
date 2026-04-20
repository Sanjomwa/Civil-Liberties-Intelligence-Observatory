import streamlit as st
import pandas as pd
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE

st.set_page_config(
    page_title="Regional Conflict Pressure",
    page_icon="🗺️",
    layout="wide",
)

st.title("🗺️ Conflict Pressure (Kenya)")

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            conflict_events,
            fatalities,
            block_rate,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
    """)


df = load_data(start_date, end_date)

c1, c2, c3 = st.columns(3)

c1.metric("Conflict Events", df["conflict_events"].sum())
c2.metric("Fatalities", df["fatalities"].sum())
c3.metric("Avg Block Rate", f"{df['block_rate'].mean()*100:.2f}%")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["conflict_events"],
    name="Conflict"
))

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["fatalities"],
    name="Fatalities",
    yaxis="y2"
))

st.plotly_chart(fig, use_container_width=True)
