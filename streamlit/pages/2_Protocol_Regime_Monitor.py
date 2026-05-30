# pages/2_Protocol_Regime_Monitor.py

import streamlit as st
import plotly.graph_objects as go

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, stress_color

from services.marts import get_protocol_regimes

from components.kpis import metric_row
from components.trust import render_trust_strip


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Protocol Regime Monitor",
    page_icon="🛰️",
    layout="wide"
)


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# DATA
# ============================================================

df = get_protocol_regimes(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No protocol regime data available.")
    st.stop()


latest_date = df["date_key"].max()

latest = df[
    df["date_key"] == latest_date
]


# ============================================================
# HEADER
# ============================================================

st.title("Protocol Regime Monitor")

st.caption(
    f"Protocol-level censorship regime classification "
    f"across {COUNTRY} (June 2023 – June 2025)"
)


# ============================================================
# TRUST STRIP
# ============================================================

render_trust_strip(
    reporting_version=latest.iloc[0]["reporting_version"],
    snapshot_at=latest.iloc[0]["snapshot_at"],
    max_date=latest_date
)

st.divider()


# ============================================================
# KPI ROW
# ============================================================

metric_row([
    (
        "Protocols Monitored",
        f"{latest['protocol'].nunique()}"
    ),
    (
        "Elevated Protocols",
        f"{(latest['trend_state'] == 'HIGH_PROTOCOL_ANOMALY').sum()}"
    ),
    (
        "Critical Shifts",
        f"{(latest['trend_state'] == 'CRITICAL_PROTOCOL_SHIFT').sum()}"
    ),
    (
        "Average Confidence",
        f"{latest['regime_confidence'].mean():.2f}"
    ),
])

st.divider()


# ============================================================
# PROTOCOL STRESS HEATMAP
# ============================================================

st.subheader("Protocol Stress Heatmap")

st.markdown("""
This heatmap shows protocol-level digital stress over time.

Higher intensity means stronger statistically abnormal interference
behavior compared to historical baseline performance.

Bright regions indicate possible coordinated protocol disruption.
""")

heat = df.pivot_table(
    index="protocol",
    columns="date_key",
    values="protocol_stress_score"
)

fig = go.Figure(
    data=go.Heatmap(
        z=heat.values,
        x=heat.columns,
        y=heat.index
    )
)

apply_layout(
    fig,
    "Protocol Stress Over Time"
)

fig.update_layout(
    height=700,
    xaxis_title="Date",
    yaxis_title="Protocol"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()


# ============================================================
# CURRENT PROTOCOL RANKING
# ============================================================

st.subheader("Current Protocol Ranking")

st.markdown("""
Protocols ranked by current interference stress score.

This helps identify which protocol families are experiencing
the strongest censorship pressure right now.
""")

ranked = latest.sort_values(
    "protocol_stress_score",
    ascending=False
)

st.dataframe(
    ranked[
        [
            "protocol",
            "protocol_state",
            "protocol_stress_score",
            "regime_confidence",
            "severe_obs_share",
            "elevated_obs_share",
            "insufficient_obs_share",
            "sample_quality_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()


# ============================================================
# PROTOCOL DETAIL EXPLORER
# ============================================================

st.subheader("Protocol Detail Explorer")

selected = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].unique())
)

detail = df[
    df["protocol"] == selected
].sort_values("date_key")


st.markdown(f"""
Detailed regime evolution for **{selected}**

This shows:

- protocol stress score
- anomaly behavior
- confidence-adjusted reliability
""")


fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=detail["date_key"],
    y=detail["protocol_stress_score"],
    name="Stress Score",
    line=dict(
        color="#E8593C",
        width=3
    )
))

fig2.add_trace(go.Scatter(
    x=detail["date_key"],
    y=detail["anomaly_score"],
    name="Anomaly Score",
    line=dict(
        color="#2EC4B6",
        dash="dash"
    )
))

apply_layout(
    fig2,
    f"{selected} Regime Evolution"
)

fig2.update_layout(
    xaxis_title="Date",
    yaxis_title="Score"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.divider()


# ============================================================
# CONFIDENCE QUALITY VIEW
# ============================================================

st.subheader("Confidence & Statistical Reliability")

st.markdown("""
This shows how statistically trustworthy protocol classifications are.

Lower confidence often reflects:

- sparse observations
- insufficient baseline history
- zero-variance statistical windows
""")

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    x=detail["date_key"],
    y=detail["regime_confidence"],
    marker_color=[
        stress_color(v)
        for v in detail["protocol_state"]
    ],
    name="Confidence"
))

apply_layout(
    fig3,
    f"{selected} Statistical Confidence"
)

fig3.update_layout(
    xaxis_title="Date",
    yaxis_title="Confidence"
)

st.plotly_chart(
    fig3,
    use_container_width=True)
