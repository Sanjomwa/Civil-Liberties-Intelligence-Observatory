import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE
from utils.schema import CIVIL_LIBERTIES_MART_SCHEMA
from utils.validate import validate_schema


# ─────────────────────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="Protest vs Censorship",
    page_icon="⚡",
    layout="wide",
)

st.title("⚡ Protest vs Censorship Correlation")
st.caption("Do political unrest periods align with digital censorship pressure in Kenya?")


# ─────────────────────────────────────────────────────────────
# GLOBAL FILTERS
# ─────────────────────────────────────────────────────────────

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


# ─────────────────────────────────────────────────────────────
# DATA LOAD
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_data(start_date, end_date):
    return run_query(f"""
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
    """)


df = load_data(start_date, end_date)

# ─────────────────────────────────────────────────────────────
# SCHEMA VALIDATION (GUARD RAIL)
# ─────────────────────────────────────────────────────────────

validate_schema(df, CIVIL_LIBERTIES_MART_SCHEMA, "Protest vs Censorship")


# ─────────────────────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────────────────────

df["conflict_events"] = df["conflict_events"].fillna(0)


# ─────────────────────────────────────────────────────────────
# SIDEBAR FILTER (SUPPRESSION WINDOWS)
# ─────────────────────────────────────────────────────────────

st.sidebar.subheader("🧠 Suppression Window Filter")

windows = sorted(df["suppression_window"].dropna().unique().tolist())

selected_windows = st.sidebar.multiselect(
    "Select regimes",
    windows,
    default=windows
)

df = df[df["suppression_window"].isin(selected_windows)]


# ─────────────────────────────────────────────────────────────
# KPI LAYER
# ─────────────────────────────────────────────────────────────

protest_threshold = df["conflict_events"].quantile(0.75)

high_conflict = df[df["conflict_events"] >= protest_threshold]
low_conflict = df[df["conflict_events"] < protest_threshold]

lift = (
    high_conflict["block_rate"].mean()
    - low_conflict["block_rate"].mean()
) * 100

c1, c2, c3, c4 = st.columns(4)

c1.metric("High-conflict days", len(high_conflict))
c2.metric("Avg block rate (high conflict)", f"{high_conflict['block_rate'].mean()*100:.1f}%")
c3.metric("Avg block rate (low conflict)", f"{low_conflict['block_rate'].mean()*100:.1f}%")
c4.metric("Censorship lift", f"+{lift:.1f} pp", delta_color="inverse")

st.divider()


# ─────────────────────────────────────────────────────────────
# TIME SERIES VIEW
# ─────────────────────────────────────────────────────────────

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
    name="Conflict Events",
    marker_color="rgba(239,159,39,0.5)"
))

fig.update_layout(
    title="Censorship vs Conflict Over Time",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
    xaxis=dict(title="Date"),
    yaxis=dict(title="Block Rate %"),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────────────────────
# CORRELATION VIEW
# ─────────────────────────────────────────────────────────────

fig2 = px.scatter(
    df,
    x="conflict_events",
    y=df["block_rate"] * 100,
    color="suppression_window",
    size="takedown_requests",
    trendline="ols",
    labels={
        "conflict_events": "Conflict events",
        "y": "Block rate %",
    },
    height=450,
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
)

st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# SUPPRESSION WINDOW ANALYSIS
# ─────────────────────────────────────────────────────────────

st.subheader("🧠 Suppression Window Impact Analysis")

context = df.groupby("suppression_window", as_index=False).agg({
    "block_rate": "mean",
    "conflict_events": "mean",
    "takedown_requests": "sum"
})

fig3 = px.bar(
    context.sort_values("block_rate"),
    x="block_rate",
    y="suppression_window",
    orientation="h",
)

fig3.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False,
)

st.plotly_chart(fig3, use_container_width=True)
