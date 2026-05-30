# pages/1_National_Stress_Observatory.py

import streamlit as st
import plotly.graph_objects as go

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout, stress_color

from services.marts import get_national_stress

from components.kpis import metric_row
from components.trust import (
    render_trust_strip,
    insufficient_history_notice
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="National Stress Observatory",
    page_icon="📈",
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

df = get_national_stress(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No national stress data available.")
    st.stop()


latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("National Stress Observatory")

st.caption(
    f"Country-level digital suppression pressure across {COUNTRY} "
    "(June 2023 – June 2025)"
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
# KPI ROW
# ============================================================

metric_row([
    (
        "Current Pressure",
        f"{latest['composite_pressure_score']:.2f}"
    ),
    (
        "Pressure Delta",
        f"{latest['pressure_delta']:.2f}"
    ),
    (
        "Elevated Protocols",
        f"{int(latest['elevated_protocol_count'])}"
    ),
    (
        "Sample Quality",
        f"{latest['avg_sample_quality_score']:.2f}"
    ),
])

st.divider()


# ============================================================
# INSUFFICIENT HISTORY WARNING
# ============================================================

if latest["baseline_days_30d"] < 14:
    insufficient_history_notice()


# ============================================================
# NATIONAL PRESSURE TIMELINE
# ============================================================

st.subheader("National Digital Pressure Trend")

st.markdown(f"""
This chart compares {COUNTRY}'s **observed national digital pressure**
against its **historical baseline trend**.

**How to read this**

- **Coral / Orange line** → current observed pressure conditions
- **Teal dashed line** → expected historical baseline

When observed pressure rises sharply above baseline,
the country may be experiencing unusual digital suppression
activity or elevated network interference conditions.
""")

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["composite_pressure_score"],
    name="Observed National Pressure",
    line=dict(
        color="#E8593C",
        width=3
    )
))

fig.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["rolling_baseline_pressure"],
    name="Historical Baseline",
    line=dict(
        color="#2EC4B6",
        width=2,
        dash="dash"
    )
))

apply_layout(
    fig,
    "Observed Pressure vs Historical Baseline"
)

fig.update_layout(
    hovermode="x unified",
    yaxis_title="Pressure Score",
    xaxis_title="Date"
)

st.plotly_chart(
    fig,
    use_container_width=True
)

st.divider()


# ============================================================
# SUPPRESSION WINDOW PROBABILITY
# ============================================================

st.subheader("Suppression Window Probability")

st.markdown("""
This chart estimates the likelihood that a day reflects a
**coordinated digital suppression event**.

The model combines:

- protocol-level censorship anomalies
- elevated blocking behavior
- protest / conflict pressure
- statistically abnormal network stress

**Probability scale**

- **0–30%** → normal background conditions
- **30–60%** → elevated digital stress
- **60–80%** → strong suppression indicators
- **80–100%** → critical coordinated suppression window
""")

valid_df = df[
    df["suppression_window_probability"].notna()
]

fig2 = go.Figure()

fig2.add_trace(go.Bar(
    x=valid_df["date_key"],
    y=valid_df["suppression_window_probability"],
    marker_color=[
        stress_color(s)
        for s in valid_df["suppression_window_class"]
    ],
    name="Suppression Probability"
))

apply_layout(
    fig2,
    "Suppression Probability"
)

fig2.update_layout(
    yaxis=dict(
        title="Probability",
        tickformat=".0%",
        range=[0, 1]
    ),
    xaxis_title="Date"
)

fig2.add_hline(y=0.30, line_dash="dot", opacity=0.4)
fig2.add_hline(y=0.60, line_dash="dot", opacity=0.5)
fig2.add_hline(y=0.80, line_dash="dot", opacity=0.6)

st.plotly_chart(
    fig2,
    use_container_width=True
)

st.caption(
    f"Higher values indicate stronger evidence that observed "
    f"network conditions diverge from {COUNTRY}'s normal baseline."
)

st.divider()


# ============================================================
# PROTOCOL ESCALATION LOAD
# ============================================================

st.subheader("Protocol Escalation Load")

st.markdown("""
This shows how many monitored protocols experienced elevated
interference conditions on each day.

Large spikes often indicate broader network-level stress rather
than isolated protocol instability.
""")

fig3 = go.Figure()

fig3.add_trace(go.Scatter(
    x=df["date_key"],
    y=df["elevated_protocol_count"],
    fill="tozeroy",
    line=dict(
        color="#EF9F27",
        width=2
    ),
    name="Elevated Protocol Count"
))

apply_layout(
    fig3,
    "Elevated Protocol Load"
)

fig3.update_layout(
    yaxis_title="Protocol Count",
    xaxis_title="Date"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

st.divider()


# ============================================================
# RAW TABLE
# ============================================================

st.subheader("Observatory Data")

st.dataframe(
    df[
        [
            "date_key",
            "composite_pressure_score",
            "pressure_delta",
            "suppression_window_probability",
            "suppression_window_class",
            "elevated_protocol_count",
            "avg_sample_quality_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)
