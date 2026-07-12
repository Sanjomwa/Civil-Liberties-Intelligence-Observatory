import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, correlation_color, alignment_color, confidence_color, inject_css
from services.marts import get_protocol_correlation
from components.status import render_state_badge, render_confidence_badge
from components.trust import render_trust_strip, attribution_footer


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Protocol ↔ Repression Correlation Engine",
    page_icon="📡",
    layout="wide"
)

inject_css()


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# DATA
# ============================================================

df = get_protocol_correlation(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No protocol correlation intelligence available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("📡 Protocol ↔ Repression Correlation Engine")

st.caption("""
Measures statistically validated alignment between protocol-level
anomaly escalation and national repression pressure.

High sustained correlation suggests coordinated suppression behavior.
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# PROTOCOL FILTER
# ============================================================

protocol = st.selectbox(
    "Select Protocol",
    sorted(df["protocol"].dropna().unique())
)

protocol_df = df[df["protocol"] == protocol]
latest_protocol = protocol_df.iloc[-1]


# ============================================================
# KPI ROW
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Rolling Correlation",
    f"{latest_protocol['rolling_pressure_corr']:.2f}"
    if latest_protocol["rolling_pressure_corr"] is not None
    else "N/A"
)

with c2:
    render_state_badge(
        "Alignment State",
        latest_protocol["alignment_state"],
        alignment_color(latest_protocol["alignment_state"]),
    )

with c3:
    render_state_badge(
        "Correlation Strength",
        latest_protocol["correlation_state"],
        correlation_color(latest_protocol["correlation_state"]),
    )

with c4:
    render_confidence_badge(
        "Confidence",
        latest_protocol["final_confidence_level"],
        confidence_color(latest_protocol["final_confidence_level"]),
    )

st.divider()


# ============================================================
# ROLLING CORRELATION TIMELINE
# ============================================================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=protocol_df["measurement_date"],
    y=protocol_df["rolling_pressure_corr"],
    name="Rolling Correlation",
    line=dict(width=3)
))

fig.add_hline(y=0.55)
fig.add_hline(y=-0.55)

apply_layout(
    fig,
    f"{protocol} Rolling Pressure Correlation"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.info("""
Positive values indicate protocol disruption rising with national pressure.

Negative values suggest inverse movement.

Strong sustained positive correlation is a potential synchronized
suppression signal.
""")


st.divider()


# ============================================================
# SYNCHRONIZED STRESS
# ============================================================

fig2 = go.Figure()

fig2.add_trace(go.Scatter(
    x=protocol_df["measurement_date"],
    y=protocol_df["synchronized_stress"],
    fill="tozeroy",
    name="Synchronization Strength"
))

apply_layout(
    fig2,
    "Escalation Synchronization Strength"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.info("""
Measures how consistently protocol interference and national pressure
move together over rolling windows.
""")


st.divider()


# ============================================================
# DIVERGENCE
# ============================================================

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    x=protocol_df["measurement_date"],
    y=protocol_df["stress_divergence"],
    name="Stress Divergence"
))

apply_layout(
    fig3,
    "Protocol vs Pressure Divergence"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

st.info("""
Large divergence means protocol behavior is moving independently
from national repression pressure.

This may indicate isolated protocol anomalies or alternate drivers.
""")


st.divider()


# ============================================================
# ALIGNMENT DISTRIBUTION
# ============================================================

align_counts = (
    protocol_df["alignment_state"]
    .value_counts()
    .reset_index()
)

align_counts.columns = ["alignment_state", "count"]

fig4 = px.bar(
    align_counts,
    x="alignment_state",
    y="count",
    color="alignment_state"
)

apply_layout(
    fig4,
    "Observed Alignment States"
)

st.plotly_chart(
    fig4,
    use_container_width=True
)


st.divider()


# ============================================================
# PROTOCOL RANKING
# ============================================================

latest_all = (
    df.sort_values("measurement_date")
    .groupby("protocol")
    .tail(1)
    .sort_values(
        "rolling_pressure_corr",
        ascending=False
    )
)

st.subheader("Current Protocol Correlation Ranking")

st.dataframe(
    latest_all[
        [
            "protocol",
            "rolling_pressure_corr",
            "correlation_state",
            "alignment_state",
            "final_confidence_level"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
