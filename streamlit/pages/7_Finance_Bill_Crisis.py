# pages/7_Finance_Bill_Crisis.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.bq_client import run_query, table, PALETTE


# ─────────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────────

st.set_page_config(
    page_title="Finance Bill Crisis · Observatory",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Kenya Finance Bill Crisis (2024)")
st.caption("Convergence of protests, censorship pressure, and enforcement escalation")


# ─────────────────────────────────────────────
# DATA LOAD (MART-STRICT FILTER)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data():
    return run_query(f"""
        SELECT
            measurement_date,
            block_rate,
            blocked_tests,
            conflict_events,
            fatalities,
            takedown_requests,
            items_removed,
            google_requests,
            civil_liberties_pressure_index
        FROM {table("civil_liberties_mart")}
        WHERE suppression_window = 'FINANCE_BILL_CRISIS'
        ORDER BY measurement_date
    """)


df = load_data()

if df is None or df.empty:
    st.warning("No Finance Bill Crisis data found.")
    st.stop()


df["measurement_date"] = pd.to_datetime(df["measurement_date"])


# ─────────────────────────────────────────────
# CLEANING
# ─────────────────────────────────────────────

for col in [
    "block_rate",
    "conflict_events",
    "takedown_requests",
    "civil_liberties_pressure_index"
]:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


# ─────────────────────────────────────────────
# KPI BLOCK
# ─────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

c1.metric("Crisis Days", len(df))
c2.metric("Total Conflict Events", f"{df['conflict_events'].sum():,.0f}")
c3.metric("Total Takedowns", f"{df['takedown_requests'].sum():,.0f}")
c4.metric("Peak Pressure Index", f"{df['civil_liberties_pressure_index'].max():.2f}")

st.divider()


# ─────────────────────────────────────────────
# CORE TIMELINE (CLEAN SIGNAL STACK)
# ─────────────────────────────────────────────

daily = df.groupby("measurement_date", as_index=False).agg({
    "block_rate": "mean",
    "conflict_events": "sum",
    "takedown_requests": "sum",
    "civil_liberties_pressure_index": "max"
})

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["block_rate"] * 100,
    name="Block Rate %",
    line=dict(color=PALETTE["coral"], width=2)
))

fig.add_trace(go.Bar(
    x=daily["measurement_date"],
    y=daily["conflict_events"],
    name="Conflict Events",
    marker_color="rgba(239,159,39,0.5)"
))

fig.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["civil_liberties_pressure_index"],
    name="Pressure Index",
    line=dict(color=PALETTE["teal"], width=2),
    yaxis="y2"
))

fig.update_layout(
    title="Crisis Dynamics: Censorship vs Protest vs Pressure",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
    yaxis=dict(title="Events / Block Rate"),
    yaxis2=dict(title="Pressure Index", overlaying="y", side="right")
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# PHASE SEGMENTATION (NO ARTIFICIAL TRENDLINES)
# ─────────────────────────────────────────────

df["phase"] = pd.cut(
    df["civil_liberties_pressure_index"],
    bins=[-0.01, 0.3, 0.6, 1.0],
    labels=["Low Pressure", "Medium Pressure", "High Pressure"]
)

phase = df.groupby("phase", as_index=False).agg({
    "block_rate": "mean",
    "conflict_events": "mean",
    "takedown_requests": "sum",
    "civil_liberties_pressure_index": "mean"
})

fig2 = px.bar(
    phase,
    x="civil_liberties_pressure_index",
    y="phase",
    orientation="h",
    color="phase",
    title="Crisis Intensity Phases"
)

fig2.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    showlegend=False
)

st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# TRADEOFF SCATTER (NO statsmodels DEPENDENCY)
# ─────────────────────────────────────────────

fig3 = px.scatter(
    df,
    x="conflict_events",
    y=df["block_rate"] * 100,
    size="takedown_requests",
    color="civil_liberties_pressure_index",
    title="Conflict vs Censorship Tradeoff"
)

fig3.update_layout(
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF"
)

st.plotly_chart(fig3, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# RAW TABLE
# ─────────────────────────────────────────────

st.subheader("📊 Crisis Dataset")

st.dataframe(
    df[[
        "measurement_date",
        "block_rate",
        "conflict_events",
        "fatalities",
        "takedown_requests",
        "civil_liberties_pressure_index"
    ]],
    use_container_width=True,
    hide_index=True
)
