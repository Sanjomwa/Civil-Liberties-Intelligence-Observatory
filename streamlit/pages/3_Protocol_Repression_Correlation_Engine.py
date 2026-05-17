# pages/3_Protocol_Repression_Correlation_Engine.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, stress_color
from services.marts import get_protocol_regimes
from components.trust import render_trust_strip


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Protocol Stress Intelligence Observatory",
    page_icon="🔗",
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
    st.warning("No protocol intelligence data available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("🔗 Protocol Stress Intelligence Observatory")

st.caption(
    """
    Tracks protocol-level anomaly pressure, escalation states,
    and statistical confidence across Kenya's censorship surface.
    """
)

render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["date_key"].max()
)

st.divider()


# ============================================================
# PROTOCOL FILTER
# ============================================================

protocol = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].unique())
)

protocol_df = df[df["protocol"] == protocol]
latest_protocol = protocol_df.iloc[-1]


# ============================================================
# KPI ROW
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Stress Score",
    f"{latest_protocol['protocol_stress_score']:.2f}"
)

c2.metric(
    "Current State",
    latest_protocol["protocol_state"]
)

c3.metric(
    "Confidence",
    latest_protocol["confidence_level"]
)

c4.metric(
    "Regime Confidence",
    f"{latest_protocol['regime_confidence']:.2f}"
)

st.divider()


# ============================================================
# STRESS TIMELINE
# ============================================================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=protocol_df["date_key"],
    y=protocol_df["protocol_stress_score"],
    name="Stress Score",
    line=dict(width=2)
))

apply_layout(
    fig,
    f"{protocol} Protocol Stress Trend"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.markdown("""
**Plain English**

Higher stress means protocol behavior is diverging sharply from
historical normal operation.

Sustained spikes often indicate interference escalation.
""")

st.divider()


# ============================================================
# REGIME DISTRIBUTION
# ============================================================

state_counts = (
    protocol_df["protocol_state"]
    .value_counts()
    .reset_index()
)

state_counts.columns = ["protocol_state", "count"]

fig2 = px.bar(
    state_counts,
    x="protocol_state",
    y="count",
    color="protocol_state"
)

apply_layout(
    fig2,
    "Observed Regime Distribution"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.markdown("""
This shows how often this protocol spent time in each
suppression regime.
""")

st.divider()


# ============================================================
# OBSERVABILITY SHARES
# ============================================================

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=protocol_df["date_key"],
    y=protocol_df["severe_obs_share"],
    name="Severe Share",
    stackgroup="one"
))

fig3.add_trace(go.Scatter(
    x=protocol_df["date_key"],
    y=protocol_df["elevated_obs_share"],
    name="Elevated Share",
    stackgroup="one"
))

fig3.add_trace(go.Scatter(
    x=protocol_df["date_key"],
    y=protocol_df["insufficient_obs_share"],
    name="Insufficient Share",
    stackgroup="one"
))

apply_layout(
    fig3,
    "Observation Reliability Composition"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

st.markdown("""
This explains *why* the protocol state was assigned.

High insufficient share means evidence was sparse.
""")

st.divider()


# ============================================================
# RANKING TABLE
# ============================================================

latest_all = (
    df.sort_values("date_key")
    .groupby("protocol")
    .tail(1)
    .sort_values("protocol_stress_score", ascending=False)
)

st.subheader("Current Protocol Ranking")

st.dataframe(
    latest_all[
        [
            "protocol",
            "protocol_stress_score",
            "protocol_state",
            "confidence_level",
            "regime_confidence"
        ]
    ],
    use_container_width=True,
    hide_index=True
)
