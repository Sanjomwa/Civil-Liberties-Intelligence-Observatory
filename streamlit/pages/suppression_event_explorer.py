import streamlit as st
import plotly.express as px

from core.state import init_state
from core.config import COUNTRY
from core.filters import render_sidebar
from core.theme import apply_layout, inject_css
from services.marts import get_event_explorer
from components.trust import render_trust_strip, attribution_footer


# ============================================================
# PAGE CONFIG
# ============================================================

inject_css()


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# DATA
# ============================================================

df = get_event_explorer(
    st.session_state.start_date,
    st.session_state.end_date
)

if df.empty:
    st.warning("No event intelligence available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("🧭 Suppression Event Explorer")

st.caption(f"""
Investigate synchronized censorship escalation windows
across {COUNTRY}'s protocol surface.

This page reconstructs suppression episodes by aligning:

• protocol anomaly transitions  
• national pressure shifts  
• statistical synchronization  
• divergence and recovery behavior
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# EVENT DATE
# ============================================================

event_date = st.selectbox(
    "Select Event Date",
    sorted(df["measurement_date"].unique(), reverse=True)
)

event_df = df[df["measurement_date"] == event_date]


# ============================================================
# EVENT KPIs
# ============================================================

c1, c2, c3, c4, c5 = st.columns(5)

c1.metric(
    "Protocols Monitored",
    len(event_df)
)

c2.metric(
    "Avg Correlation",
    f"{event_df['rolling_pressure_corr'].mean():.2f}"
)

c3.metric(
    "Avg Pressure",
    f"{event_df['composite_pressure_score'].mean():.2f}"
)

c4.metric(
    "Elevated Protocols",
    int((event_df["protocol_state"] == "ELEVATED").sum())
)

c5.metric(
    "Critical Shifts",
    int((event_df["protocol_state"] == "SEVERE_ELEVATION").sum())
)

st.divider()


# ============================================================
# EVENT HEATMAP
# ============================================================

heat = px.density_heatmap(
    event_df,
    x="protocol",
    y="alignment_state",
    z="rolling_pressure_corr",
    # Fixed to the full possible range of this value, not auto-scaled to
    # this selection's own min/max -- auto-scaling manufactures visual
    # contrast out of a narrow, weak range of real values.
    range_color=[-1, 1],
)

apply_layout(
    heat,
    "Protocol Alignment Heatmap"
)

st.plotly_chart(
    heat,
    use_container_width=True
)

_heat_min = event_df["rolling_pressure_corr"].min()
_heat_max = event_df["rolling_pressure_corr"].max()

st.markdown(f"""
Color scale fixed to [-1, 1]. Each cell is one protocol's own correlation
with national pressure on this date, computed independently -- this does not
measure cross-protocol coordination. Values shown here run
**{_heat_min:.2f} to {_heat_max:.2f}**, against a 0.55 MODERATE-relationship
threshold on the same scale.
""")

st.divider()


# ============================================================
# CORRELATION RANKING
# ============================================================

rank = event_df.sort_values(
    "rolling_pressure_corr",
    key=lambda s: s.abs(),
    ascending=False
)

fig2 = px.bar(
    rank,
    x="protocol",
    y="rolling_pressure_corr",
    color="correlation_state"
)

apply_layout(
    fig2,
    "Protocol Correlation Ranking"
)

st.plotly_chart(
    fig2,
    use_container_width=True
)

_any_qualifying_in_range = bool(
    df["correlation_state"].isin(["STRONG_RELATIONSHIP", "MODERATE_RELATIONSHIP"]).any()
)
_range_max_abs_corr = df["rolling_pressure_corr"].abs().max()

st.markdown(f"""
Bar height is signed correlation magnitude; ranking (left to right) is by
`ABS(rolling_pressure_corr)`, matching the mart's own STRONG/MODERATE
threshold definition -- a strong inverse relationship ranks as high as a
strong positive one. {"At least one protocol-day row in the selected date range reaches the MODERATE or STRONG threshold." if _any_qualifying_in_range else f"No protocol-day row in the selected date range reaches the MODERATE (0.55) or STRONG (0.82) threshold -- the largest magnitude observed is {_range_max_abs_corr:.2f}."}
See **Methodology & Statistical Guardrails** for the full, dashboard-wide
disclosure of how often these thresholds have been reached historically.
""")

st.divider()


# ============================================================
# DIVERGENCE
# ============================================================

fig3 = px.scatter(
    event_df,
    x="protocol_stress_score",
    y="composite_pressure_score",
    color="divergence_state",
    size="regime_confidence",
    hover_data=["protocol"]
)

apply_layout(
    fig3,
    "Stress vs Pressure Divergence"
)

st.plotly_chart(
    fig3,
    use_container_width=True
)

st.markdown("""
Large divergence suggests protocol-specific interference
that national pressure context alone cannot explain.
""")

st.divider()


# ============================================================
# RAW EVENT TABLE
# ============================================================

st.subheader("Event Intelligence Table")

st.dataframe(
    event_df[
        [
            "protocol",
            "protocol_state",
            "rolling_pressure_corr",
            "alignment_state",
            "correlation_state",
            "divergence_state",
            "protocol_stress_score",
            "composite_pressure_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

st.divider()

attribution_footer(["ACLED", "OONI"], snapshot_at=latest["snapshot_at"])
