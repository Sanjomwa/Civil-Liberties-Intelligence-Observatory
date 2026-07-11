import streamlit as st
import plotly.express as px

from core.state import init_state
from core.config import COUNTRY
from core.filters import render_sidebar
from core.theme import apply_layout
from services.marts import get_event_explorer
from components.trust import render_trust_strip, attribution_footer


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Suppression Event Explorer",
    page_icon="🧭",
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

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Protocols Affected",
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
    (event_df["protocol_state"] == "ELEVATED").sum()
)

st.divider()


# ============================================================
# EVENT HEATMAP
# ============================================================

heat = px.density_heatmap(
    event_df,
    x="protocol",
    y="alignment_state",
    z="rolling_pressure_corr"
)

apply_layout(
    heat,
    "Protocol Alignment Heatmap"
)

st.plotly_chart(
    heat,
    use_container_width=True
)

st.markdown("""
Shows which protocols moved in lockstep with national
digital repression pressure.
""")

st.divider()


# ============================================================
# CORRELATION RANKING
# ============================================================

rank = event_df.sort_values(
    "rolling_pressure_corr",
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

st.markdown("""
Higher values mean stronger synchronization between
protocol disruption and national pressure escalation.
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
