# pages/6_Suppression_Windows.py

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from utils.bq_client import run_query, table, PALETTE, SUPPRESSION_COLORS


st.set_page_config(
    page_title="Suppression Windows · Observatory",
    page_icon="🚨",
    layout="wide"
)

st.title("🚨 Suppression Windows")
st.caption("System-generated regimes of censorship + conflict + legal pressure")


# ─────────────────────────────────────────────
# DATA LOAD (STRICT MART ONLY)
# ─────────────────────────────────────────────

@st.cache_data(ttl=3600)
def load_data(start_date=None, end_date=None):
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
        FROM {table('civil_liberties_mart')}
        WHERE 1=1
        ORDER BY measurement_date
    """)

df = load_data()

if df.empty:
    st.warning("No suppression data available.")
    st.stop()


df["measurement_date"] = pd.to_datetime(df["measurement_date"])


# ─────────────────────────────────────────────
# KPIs
# ─────────────────────────────────────────────

full_windows = df[df["suppression_window"] == "FINANCE_BILL_CRISIS"]
active_suppression = df[df["suppression_window"] == "ACTIVE_SUPPRESSION"]

c1, c2, c3, c4 = st.columns(4)

c1.metric("Finance Crisis Days", len(full_windows))
c2.metric("Active Suppression Days", len(active_suppression))
c3.metric("Peak Pressure Index", f"{df['civil_liberties_pressure_index'].max():.2f}")
c4.metric("Avg Block Rate", f"{df['block_rate'].mean()*100:.2f}%")

st.divider()


# ─────────────────────────────────────────────
# WINDOW DISTRIBUTION
# ─────────────────────────────────────────────

window_counts = (
    df.groupby("suppression_window", as_index=False)
    .size()
    .sort_values("size", ascending=True)
)

fig = px.bar(
    window_counts,
    x="size",
    y="suppression_window",
    orientation="h",
    title="Suppression Window Frequency"
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
# INTENSITY OVER TIME (FIXED METRIC)
# ─────────────────────────────────────────────

daily = df.groupby("measurement_date", as_index=False).agg({
    "civil_liberties_pressure_index": "max",
    "block_rate": "mean",
    "conflict_events": "sum",
    "takedown_requests": "sum"
})

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["civil_liberties_pressure_index"],
    fill="tozeroy",
    name="Pressure Index",
    line=dict(color=PALETTE["coral"])
))

fig2.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["block_rate"] * 100,
    name="Block Rate %",
    yaxis="y2",
    line=dict(color=PALETTE["amber"])
))

fig2.update_layout(
    title="Suppression Pressure Over Time",
    plot_bgcolor="#0D0D0F",
    paper_bgcolor="#0D0D0F",
    font_color="#E8E6DF",
    yaxis=dict(title="Pressure Index"),
    yaxis2=dict(overlaying="y", side="right", title="Block Rate %"),
    legend=dict(orientation="h")
)

st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ─────────────────────────────────────────────
# REGIME BREAKDOWN
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
    color_continuous_scale="Reds"
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
# FULL TABLE VIEW
# ─────────────────────────────────────────────

st.subheader("📊 Suppression Window Dataset")

st.dataframe(
    df[[
        "measurement_date",
        "suppression_window",
        "block_rate",
        "conflict_events",
        "fatalities",
        "takedown_requests",
        "civil_liberties_pressure_index"
    ]],
    use_container_width=True,
    hide_index=True
)
