import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE
from utils.schema import CIVIL_LIBERTIES_MART_SCHEMA
from utils.validate import validate_schema


st.set_page_config(
    page_title="Protest vs Censorship",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Protest vs Censorship Correlation")


start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            block_rate,
            conflict_events,
            fatalities,
            takedown_requests,
            items_removed,
            google_requests,
            civil_liberties_pressure_index,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY measurement_date
    """)


df = load_data(start_date, end_date)

validate_schema(df, CIVIL_LIBERTIES_MART_SCHEMA, "Protest vs Censorship")

df["conflict_events"] = df["conflict_events"].fillna(0)

# ── FILTER ──
windows = sorted(df["suppression_window"].dropna().unique())
selected = st.sidebar.multiselect("Suppression windows", windows, default=windows)
df = df[df["suppression_window"].isin(selected)]


# ── KPI ──
threshold = df["conflict_events"].quantile(0.75)

high = df[df["conflict_events"] >= threshold]
low = df[df["conflict_events"] < threshold]

lift = (high["block_rate"].mean() - low["block_rate"].mean()) * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric("High-conflict days", len(high))
c2.metric("Block rate (high)", f"{high['block_rate'].mean()*100:.1f}%")
c3.metric("Block rate (low)", f"{low['block_rate'].mean()*100:.1f}%")
c4.metric("Censorship lift", f"+{lift:.1f} pp")

st.divider()

# ── TIME SERIES ──
fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["block_rate"] * 100,
    name="Block Rate %",
    line=dict(color=PALETTE["coral"], width=2)
))

fig.add_trace(go.Bar(
    x=df["measurement_date"],
    y=df["conflict_events"],
    name="Conflict Events"
))

st.plotly_chart(fig, use_container_width=True)

# ── SCATTER ──
fig2 = px.scatter(
    df,
    x="conflict_events",
    y=df["block_rate"] * 100,
    color="suppression_window",
    size="takedown_requests",
    trendline="ols",
)

st.plotly_chart(fig2, use_container_width=True)
