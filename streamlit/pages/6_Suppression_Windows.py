# pages/6_Suppression_Windows.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Suppression Windows · Observatory",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Suppression Windows Analysis")
st.caption("Regime detection across censorship, protests, and enforcement signals")


# ─────────────────────────────────────────────
# DATA LOAD (MART ONLY — NO DERIVED LABELS)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data():
    return run_query(f"""
        SELECT
            measurement_date,
            suppression_window,
            block_rate,
            blocked_tests,
            conflict_events,
            fatalities,
            takedown_requests,
            items_removed,
            google_requests,
            civil_liberties_pressure_index
        FROM {table("civil_liberties_mart")}
    """)


df = load_data()

if df is None or df.empty:
    st.warning("No suppression data available.")
    st.stop()


df["measurement_date"] = pd.to_datetime(df["measurement_date"])


# ─────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────

df["conflict_events"] = df["conflict_events"].fillna(0)
df["block_rate"] = df["block_rate"].fillna(0)


# ─────────────────────────────────────────────
# KPI BLOCK (CORRECT INTERPRETATION)
# ─────────────────────────────────────────────

window_counts = df.groupby("suppression_window").size().reset_index(name="days")

full = df[df["suppression_window"] == "Full Suppression Window"]
partial = df[df["suppression_window"].isin([
    "Blocking + Protest Day",
    "Blocking + Removal Activity"
])]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Full suppression days", len(full))
c2.metric("Partial suppression days", len(partial))
c3.metric("Peak pressure index", f"{df['civil_liberties_pressure_index'].max():.2f}")
c4.metric("Avg block rate", f"{df['block_rate'].mean()*100:.2f}%")

st.divider()


# ─────────────────────────────────────────────
# WINDOW DISTRIBUTION (FIXED INTERPRETATION)
# ─────────────────────────────────────────────

window_counts = window_counts.sort_values("days")

fig = px.bar(
    window_counts,
    x="days",
    y="suppression_window",
    orientation="h",
    title="Suppression Window Distribution (Days)",
    color="days",
    color_continuous_scale="Reds"
)

fig.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# TIME SERIES (CLEAN MULTI-SIGNAL VIEW)
# ─────────────────────────────────────────────

daily = df.groupby("measurement_date", as_index=False).agg({
    "block_rate": "mean",
    "conflict_events": "sum",
    "takedown_requests": "sum",
    "civil_liberties_pressure_index": "max"
})

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["civil_liberties_pressure_index"],
    name="Pressure Index",
    line=dict(color=PALETTE["coral"], width=2),
    fill="tozeroy"
))

fig2.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["block_rate"] * 100,
    name="Block Rate %",
    line=dict(color=PALETTE["amber"], width=2),
    yaxis="y2"
))

fig2.add_trace(go.Bar(
    x=daily["measurement_date"],
    y=daily["conflict_events"],
    name="Conflict Events",
    opacity=0.4
))

fig2.update_layout(
    title="Suppression Dynamics Over Time",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
    yaxis=dict(title="Pressure / Conflict"),
    yaxis2=dict(title="Block Rate %", overlaying="y", side="right")
)

st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# REGIME INTENSITY (CORRECT AGGREGATION)
# ─────────────────────────────────────────────

regime = df.groupby("suppression_window", as_index=False).agg({
    "civil_liberties_pressure_index": "mean",
    "block_rate": "mean",
    "conflict_events": "mean",
    "takedown_requests": "sum"
})

fig3 = px.bar(
    regime.sort_values("civil_liberties_pressure_index"),
    x="civil_liberties_pressure_index",
    y="suppression_window",
    orientation="h",
    color="civil_liberties_pressure_index",
    color_continuous_scale="Reds",
    title="Suppression Regime Intensity"
)

fig3.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False
)

st.plotly_chart(fig3, use_container_width=True)


st.divider()


# ─────────────────────────────────────────────
# RAW TABLE (DEBUG SAFE)
# ─────────────────────────────────────────────

st.subheader("📊 Suppression Window Dataset")

st.dataframe(
    df[[
        "measurement_date",
        "suppression_window",
        "block_rate",
        "conflict_events",
        "takedown_requests",
        "civil_liberties_pressure_index"
    ]],
    use_container_width=True,
    hide_index=True
)
