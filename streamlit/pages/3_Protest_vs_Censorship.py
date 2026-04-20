import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.bq_client import run_query, table, PALETTE

st.set_page_config(
    page_title="Protest vs Censorship",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Protest vs Censorship Correlation")

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


# ─────────────────────────────────────────────
# SAFE DATA LOAD (FIXED)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):

    sql = f"""
        SELECT
            measurement_date,
            block_rate,
            conflict_events,
            fatalities,
            takedown_requests,
            civil_liberties_pressure_index,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY measurement_date
    """

    return run_query(sql)


df = load_data(start_date, end_date)


# ─────────────────────────────────────────────
# HARD STOP IF QUERY FAILED
# ─────────────────────────────────────────────

if df is None or df.empty:
    st.error("No data returned from BigQuery (check mart build).")
    st.stop()


# ─────────────────────────────────────────────
# SAFE COLUMN HANDLING
# ─────────────────────────────────────────────

required_cols = ["conflict_events", "block_rate"]

for col in required_cols:
    if col not in df.columns:
        st.error(f"Missing column in dataset: {col}")
        st.stop()

df["conflict_events"] = df["conflict_events"].fillna(0)


# ─────────────────────────────────────────────
# FILTERS
# ─────────────────────────────────────────────

if "suppression_window" in df.columns:
    windows = sorted(df["suppression_window"].dropna().unique())
    selected = st.sidebar.multiselect(
        "Suppression windows", windows, default=windows)
    df = df[df["suppression_window"].isin(selected)]


# ─────────────────────────────────────────────
# KPI LOGIC
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# TIME SERIES
# ─────────────────────────────────────────────

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


# ─────────────────────────────────────────────
# SCATTER (SAFE)
# ─────────────────────────────────────────────

fig2 = px.scatter(
    df,
    x="conflict_events",
    y=df["block_rate"] * 100,
    color="suppression_window" if "suppression_window" in df.columns else None,
    size="takedown_requests" if "takedown_requests" in df.columns else None,
)

st.plotly_chart(fig2, use_container_width=True)
