import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout
from services.marts import get_protocol_stress_intelligence
from components.trust import render_trust_strip


st.set_page_config(
    page_title="Protocol Stress Intelligence Observatory",
    page_icon="🔗",
    layout="wide"
)


init_state()
render_sidebar()


df = get_protocol_stress_intelligence(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No protocol intelligence data available.")
    st.stop()

latest = df.iloc[-1]


st.title("🔗 Protocol Stress Intelligence Observatory")

st.caption("""
Tracks protocol-level anomaly pressure, escalation behavior,
and statistical confidence across Kenya’s censorship surface.
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["date_key"].max()
)

st.divider()


protocol = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].unique())
)

protocol_df = df[df["protocol"] == protocol]
latest_protocol = protocol_df.iloc[-1]


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
    line=dict(width=3)
))

apply_layout(fig, f"{protocol} Stress Evolution")

st.plotly_chart(fig, use_container_width=True)

st.info("""
Higher stress indicates protocol behavior deviating sharply from historical normal operation.
Sustained spikes often suggest coordinated interference escalation.
""")


# ============================================================
# STATE DISTRIBUTION
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

apply_layout(fig2, "Observed State Distribution")

st.plotly_chart(fig2, use_container_width=True)

st.info("""
Shows how often this protocol entered each statistical regime.
""")


# ============================================================
# OBSERVABILITY SHARES
# ============================================================

fig3 = go.Figure()

for col in [
    "severe_obs_share",
    "elevated_obs_share",
    "insufficient_obs_share"
]:
    fig3.add_trace(go.Scatter(
        x=protocol_df["date_key"],
        y=protocol_df[col],
        stackgroup="one",
        name=col
    ))

apply_layout(fig3, "Observation Reliability Composition")

st.plotly_chart(fig3, use_container_width=True)

st.info("""
Explains why protocol states were assigned.
High insufficient share indicates sparse evidence.
""")


# ============================================================
# RANKING
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
