# pages/1_Censorship_Timeline.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.bq_client import run_query, table, STATUS_COLORS

st.set_page_config(
    page_title="Censorship Timeline",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Censorship Timeline")
st.caption("Tracking censorship, conflict, and suppression dynamics in Kenya (2023–2025)")


# ─────────────────────────────────────────────────────────────
# GLOBAL FILTERS (from app.py)
# ─────────────────────────────────────────────────────────────

start_date = st.session_state.get("start_date")
end_date = st.session_state.get("end_date")


# ─────────────────────────────────────────────────────────────
# DATA LOAD (ONLY MART FIELDS)
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def load_timeline(start_date, end_date):
    return run_query(f"""
        SELECT
            measurement_date,
            block_rate,
            blocked_tests,
            conflict_events,
            takedown_requests,
            suppression_window,
            civil_liberties_pressure_index
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN '{start_date}' AND '{end_date}'
        ORDER BY measurement_date
    """)


df = load_timeline(start_date, end_date)


# ─────────────────────────────────────────────────────────────
# KPI ROW
# ─────────────────────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

c1.metric("Avg Block Rate", f"{df['block_rate'].mean() * 100:.2f}%")
c2.metric("Total Blocked Tests", f"{df['blocked_tests'].sum():,.0f}")
c3.metric("Conflict Events", f"{df['conflict_events'].sum():,.0f}")
c4.metric("Takedown Requests", f"{df['takedown_requests'].sum():,.0f}")

st.divider()


# ─────────────────────────────────────────────────────────────
# MAIN TIME SERIES (NO PYTHON AGGREGATION)
# ─────────────────────────────────────────────────────────────

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["block_rate"] * 100,
    name="Block Rate %",
    line=dict(width=2)
))

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["conflict_events"],
    name="Conflict Events",
    yaxis="y2"
))

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["takedown_requests"],
    name="Takedown Requests",
    yaxis="y3"
))

fig.update_layout(
    title="Censorship vs Conflict Over Time",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    xaxis=dict(title="Date"),
    yaxis=dict(title="Block Rate %"),
    yaxis2=dict(overlaying="y", side="right", title="Conflict Events"),
    yaxis3=dict(overlaying="y", side="right", position=0.95, title="Takedowns"),
    legend=dict(orientation="h")
)

st.plotly_chart(fig, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────────────────────
# SUPPRESSION WINDOWS
# ─────────────────────────────────────────────────────────────

st.subheader("🧠 Suppression Windows")

window_df = (
    df.groupby("suppression_window", as_index=False)
    .size()
    .sort_values("size", ascending=False)
)

fig2 = px.bar(
    window_df,
    x="size",
    y="suppression_window",
    orientation="h"
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False
)

st.plotly_chart(fig2, use_container_width=True)


# ─────────────────────────────────────────────────────────────
# MONTHLY AGGREGATION (SAFE DERIVED VIEW)
# ─────────────────────────────────────────────────────────────

df["year_month"] = pd.to_datetime(df["measurement_date"]).dt.to_period("M").astype(str)

monthly = df.groupby("year_month", as_index=False).agg({
    "block_rate": "mean",
    "conflict_events": "sum",
    "takedown_requests": "sum"
})

st.subheader("📊 Monthly Trends")

st.line_chart(
    monthly.set_index("year_month")[["block_rate", "conflict_events", "takedown_requests"]]
)
