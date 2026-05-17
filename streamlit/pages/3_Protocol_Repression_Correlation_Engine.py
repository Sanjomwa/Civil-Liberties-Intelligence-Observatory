# pages/3_Protocol_Repression_Correlation_Engine.py

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, stress_color

from services.marts import get_protocol_correlation

from components.trust import (
    render_trust_strip,
    insufficient_history_notice
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Protocol ↔ Repression Correlation Engine",
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

df = get_protocol_correlation(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No protocol correlation data available.")
    st.stop()

latest = df.iloc[-1]

# ============================================================
# HEADER
# ============================================================

st.title("🔗 Protocol ↔ Repression Correlation Engine")

st.caption(
    """
    Measures statistical alignment between protocol-level stress
    and national digital repression pressure.

    High sustained correlation suggests coordinated suppression behavior.
    """
)

# ============================================================
# TRUST STRIP
# ============================================================

render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["date_key"].max()
)

st.divider()

# ============================================================
# FILTER BY PROTOCOL
# ============================================================

protocols = sorted(df["protocol"].unique())

selected_protocol = st.selectbox(
    "Select Protocol",
    protocols
)

protocol_df = df[df["protocol"] == selected_protocol]

latest_protocol = protocol_df.iloc[-1]

# ============================================================
# KPI ROW
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Rolling Correlation",
    f"{latest_protocol['rolling_correlation']:.2f}"
)

c2.metric(
    "Alignment State",
    latest_protocol["alignment_state"]
)

c3.metric(
    "Window Observations",
    int(latest_protocol["window_obs"])
)

c4.metric(
    "Correlation Strength",
    f"{latest_protocol['correlation_strength']:.2f}"
)

st.divider()

# ============================================================
# INSUFFICIENT HISTORY
# ============================================================

if latest_protocol["insufficient_history_flag"]:
    insufficient_history_notice()

# ============================================================
# CORRELATION TIMELINE
# ============================================================

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=protocol_df["date_key"],
    y=protocol_df["rolling_correlation"],
    mode="lines",
    name="Rolling Correlation"
))

fig.add_hline(
    y=0.7,
    line_dash="dash",
    annotation_text="Strong Alignment"
)

fig.add_hline(
    y=0.3,
    line_dash="dot",
    annotation_text="Weak Alignment"
)

apply_layout(
    fig,
    f"{selected_protocol}: Rolling Correlation with National Pressure"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.markdown("""
**What this shows**

- Higher values indicate protocol stress rising alongside national repression pressure
- Sustained high alignment suggests coordinated interference patterns
- Near-zero correlation suggests unrelated local variation
""")

st.divider()

# ============================================================
# ALIGNMENT HEATMAP
# ============================================================

heat = protocol_df.copy()

fig2 = px.density_heatmap(
    heat,
    x="date_key",
    y="alignment_state",
    z="rolling_correlation",
    histfunc="avg"
)

apply_layout(
    fig2,
    "Alignment Regime Density"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.markdown("""
This heatmap reveals whether the protocol spends most of its
history in weak, moderate, or severe alignment regimes.
""")

st.divider()

# ============================================================
# FULL PROTOCOL RANKING
# ============================================================

st.subheader("Current Protocol Correlation Ranking")

latest_all = (
    df.sort_values("date_key")
    .groupby("protocol")
    .tail(1)
    .sort_values("rolling_correlation", ascending=False)
)

st.dataframe(
    latest_all[
        [
            "protocol",
            "rolling_correlation",
            "alignment_state",
            "window_obs",
            "correlation_strength"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

# ============================================================
# RAW DATA
# ============================================================

with st.expander("View Raw Correlation Data"):
    st.dataframe(
        protocol_df,
        use_container_width=True,
        hide_index=True
    )
