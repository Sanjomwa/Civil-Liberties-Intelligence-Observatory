import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from components.trust import render_trust_strip
from core.config import COUNTRY
from core.filters import render_sidebar
from core.state import init_state
from core.theme import apply_layout
from services.marts import get_protocol_stress_intelligence


st.set_page_config(
    page_title="Protocol Stress Intelligence Observatory",
    page_icon="🔗",
    layout="wide",
)


def _ensure_protocol_intelligence_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Make the page resilient to mart versions with partial protocol fields."""

    normalized = df.copy()

    if "protocol_stress_score" not in normalized.columns:
        if "anomaly_score" in normalized.columns:
            normalized["protocol_stress_score"] = normalized["anomaly_score"]
        else:
            normalized["protocol_stress_score"] = pd.NA

    defaults = {
        "protocol_state": "UNKNOWN",
        "confidence_level": "UNKNOWN",
        "regime_confidence": pd.NA,
        "severe_obs_share": 0.0,
        "elevated_obs_share": 0.0,
        "insufficient_obs_share": 0.0,
    }

    for column, default in defaults.items():
        if column not in normalized.columns:
            normalized[column] = default

    for column in [
        "protocol_stress_score",
        "regime_confidence",
        "severe_obs_share",
        "elevated_obs_share",
        "insufficient_obs_share",
    ]:
        normalized[column] = pd.to_numeric(normalized[column], errors="coerce")

    return normalized


def _format_number(value, fallback: str = "N/A") -> str:
    if pd.isna(value):
        return fallback
    return f"{float(value):.2f}"


init_state()
render_sidebar()


df = get_protocol_stress_intelligence(
    st.session_state.start_date,
    st.session_state.end_date,
)

if df.empty:
    st.warning("No protocol intelligence data available.")
    st.stop()

df = _ensure_protocol_intelligence_columns(df)
latest = df.iloc[-1]


st.title("🔗 Protocol Stress Intelligence Observatory")

st.caption(
    f"""
Tracks protocol-level anomaly pressure, escalation behavior,
and statistical confidence across {COUNTRY}'s censorship surface.
"""
)


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["date_key"].max(),
)

st.divider()


protocol = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].dropna().unique()),
)

protocol_df = df[df["protocol"] == protocol].copy()
latest_protocol = protocol_df.iloc[-1]


c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Stress Score",
    _format_number(latest_protocol["protocol_stress_score"]),
)

c2.metric(
    "Current State",
    str(latest_protocol["protocol_state"]),
)

c3.metric(
    "Confidence",
    str(latest_protocol["confidence_level"]),
)

c4.metric(
    "Regime Confidence",
    _format_number(latest_protocol["regime_confidence"]),
)

st.divider()


fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=protocol_df["date_key"],
        y=protocol_df["protocol_stress_score"],
        name="Stress Score",
        line=dict(width=3),
    )
)

apply_layout(fig, f"{protocol} Stress Evolution")

st.plotly_chart(fig, width="stretch")

st.info(
    """
Higher stress indicates protocol behavior deviating sharply from historical
normal operation. Sustained spikes often suggest coordinated interference
escalation.
"""
)


state_counts = protocol_df["protocol_state"].value_counts().reset_index()
state_counts.columns = ["protocol_state", "count"]

fig2 = px.bar(
    state_counts,
    x="protocol_state",
    y="count",
    color="protocol_state",
)

apply_layout(fig2, "Observed State Distribution")

st.plotly_chart(fig2, width="stretch")

st.info("Shows how often this protocol entered each statistical regime.")


fig3 = go.Figure()

for column in [
    "severe_obs_share",
    "elevated_obs_share",
    "insufficient_obs_share",
]:
    fig3.add_trace(
        go.Scatter(
            x=protocol_df["date_key"],
            y=protocol_df[column].fillna(0),
            stackgroup="one",
            name=column,
        )
    )

apply_layout(fig3, "Observation Reliability Composition")

st.plotly_chart(fig3, width="stretch")

st.info(
    """
Explains why protocol states were assigned. A high insufficient share indicates
sparse evidence.
"""
)


latest_all = (
    df.sort_values("date_key")
    .groupby("protocol")
    .tail(1)
    .sort_values("protocol_stress_score", ascending=False, na_position="last")
)

st.subheader("Current Protocol Ranking")

st.dataframe(
    latest_all[
        [
            "protocol",
            "protocol_stress_score",
            "protocol_state",
            "confidence_level",
            "regime_confidence",
        ]
    ],
    width="stretch",
    hide_index=True,
)
