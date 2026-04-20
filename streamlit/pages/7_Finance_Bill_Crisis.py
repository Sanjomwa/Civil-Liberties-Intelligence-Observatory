# pages/7_Finance_Bill_Crisis.py

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from utils.bq_client import run_query, table, PALETTE


st.set_page_config(
    page_title="Finance Bill Crisis · Observatory",
    page_icon="🔥",
    layout="wide"
)

st.title("🔥 Kenya Finance Bill Crisis (2024)")
st.caption("Gen Z protests, censorship spikes, and network interference convergence window")


# ─────────────────────────────────────────────
# DATA LOAD (STRICT MART FILTER ONLY)
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
        FROM {table('civil_liberties_mart')}
        WHERE suppression_window = 'FINANCE_BILL_CRISIS'
        ORDER BY measurement_date
    """)


df = load_data()

if df.empty:
    st.warning("No Finance Bill Crisis data found in mart.")
    st.stop()


df["measurement_date"] = pd.to_datetime(df["measurement_date"])


# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────

c1, c2, c3, c4 = st.columns(4)

c1.metric("Crisis Days", len(df))
c2.metric("Total Conflict Events", f"{df['conflict_events'].sum():,.0f}")
c3.metric("Total Takedowns", f"{df['takedown_requests'].sum():,.0f}")
c4.metric("Peak Pressure Index", f"{df['civil_liberties_pressure_index'].max():.2f}")

st.divider()


# ─────────────────────────────────────────────
# CORE TIMELINE VIEW
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
    name="Conflict Events",
    marker_color="rgba(239,159,39,0.5)"
))

fig.add_trace(go.Scatter(
    x=df["measurement_date"],
    y=df["civil_liberties_pressure_index"],
    name="Pressure Index",
    yaxis="y2",
    line=dict(color=PALETTE["teal"], width=2)
))

fig.update_layout(
    title="Finance Bill Crisis: Censorship vs Protest vs Pressure",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    legend=dict(orientation="h"),
    yaxis=dict(title="Block / Conflict"),
    yaxis2=dict(overlaying="y", side="right", title="Pressure Index"),
)

st.plotly_chart(fig, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# AGGREGATED INSIGHT VIEW
# ─────────────────────────────────────────────

df["phase"] = pd.cut(
    df["civil_liberties_pressure_index"],
    bins=[0, 0.3, 0.6, 1.0],
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
# TRADEOFF ANALYSIS
# ─────────────────────────────────────────────

fig3 = px.scatter(
    df,
    x="conflict_events",
    y=df["block_rate"] * 100,
    size="takedown_requests",
    color="civil_liberties_pressure_index",
    trendline="ols",
    title="Conflict vs Censorship Tradeoff (Crisis Window)"
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
