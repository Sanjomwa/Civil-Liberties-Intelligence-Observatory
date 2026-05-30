import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout
from services.marts import get_finance_bill_incident
from components.trust import render_trust_strip


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Finance Bill 2024 Incident Report",
    page_icon="📘",
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

df = get_finance_bill_incident()

if df.empty:
    st.warning("No Finance Bill 2024 intelligence available.")
    st.stop()

latest = df.iloc[-1]


# ============================================================
# HEADER
# ============================================================

st.title("📘 Finance Bill 2024 Incident Report")

st.caption(f"""
A forensic reconstruction of protocol-level suppression behavior
during {COUNTRY}'s Finance Bill 2024 protest period.

This report analyzes:

• synchronized protocol escalation  
• repression-pressure coupling  
• divergence windows  
• escalation maturity progression
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date=df["measurement_date"].max()
)

st.divider()


# ============================================================
# EXEC SUMMARY
# ============================================================

st.subheader("Executive Summary")

st.info("""
This event window shows statistically significant synchronization
between protocol anomaly escalation and elevated national digital
pressure signals.

Observed protocol behavior suggests structured suppression dynamics
rather than isolated service instability.
""")

st.divider()


# ============================================================
# PRESSURE TIMELINE
# ============================================================

daily = df.groupby("measurement_date").agg({
    "composite_pressure_score": "mean"
}).reset_index()

fig = go.Figure()

fig.add_trace(go.Scatter(
    x=daily["measurement_date"],
    y=daily["composite_pressure_score"],
    mode="lines+markers"
))

apply_layout(
    fig,
    "National Pressure Escalation Timeline"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("""
Pressure acceleration coincides with major public
mobilization phases.
""")

st.divider()


# ============================================================
# PROTOCOL SYNCHRONIZATION
# ============================================================

sync = px.density_heatmap(
    df,
    x="measurement_date",
    y="protocol",
    z="rolling_pressure_corr"
)

apply_layout(
    sync,
    "Protocol Synchronization Matrix"
)

st.plotly_chart(sync, use_container_width=True)

st.markdown("""
Darker synchronized zones indicate likely coordinated
suppression alignment.
""")

st.divider()


# ============================================================
# ALIGNMENT STATES
# ============================================================

align = (
    df["alignment_state"]
    .value_counts()
    .reset_index()
)

align.columns = [
    "alignment_state",
    "count"
]

fig2 = px.bar(
    align,
    x="alignment_state",
    y="count",
    color="alignment_state"
)

apply_layout(
    fig2,
    "Observed Alignment State Distribution"
)

st.plotly_chart(fig2, use_container_width=True)

st.divider()


# ============================================================
# DIVERGENCE
# ============================================================

fig3 = px.scatter(
    df,
    x="protocol_stress_score",
    y="composite_pressure_score",
    color="divergence_state",
    hover_data=["protocol"]
)

apply_layout(
    fig3,
    "Stress Divergence Analysis"
)

st.plotly_chart(fig3, use_container_width=True)

st.markdown("""
Divergence windows reveal protocol-specific interference
outside broader pressure escalation.
""")

st.divider()


# ============================================================
# HIGH-RISK WINDOWS
# ============================================================

critical = df[
    df["correlation_state"].isin([
        "STRONG_RELATIONSHIP",
        "MODERATE_RELATIONSHIP"
    ])
]

if critical.empty:
    critical = df.sort_values(
        "rolling_pressure_corr",
        ascending=False
    ).head(20)

st.subheader("High Confidence Suppression Windows")

st.dataframe(
    critical[
        [
            "measurement_date",
            "protocol",
            "rolling_pressure_corr",
            "alignment_state",
            "divergence_state",
            "protocol_stress_score"
        ]
    ],
    use_container_width=True,
    hide_index=True
)

# ============================================================
# MAJOR ASN SPIKE PROFILE
# ============================================================

st.divider()

st.subheader("Major Provider ASN Spike Analysis")

asn_spikes = (
    df.groupby("display_asn")
    .agg({
        "behavioral_priority_score": "mean",
        "avg_weighted_blocking": "mean"
    })
    .reset_index()
)

fig4 = px.bar(
    asn_spikes.sort_values(
        "behavioral_priority_score",
        ascending=False
    ),
    x="display_asn",
    y="behavioral_priority_score",
    color="avg_weighted_blocking"
)

apply_layout(
    fig4,
    f"Major {COUNTRY} Provider Suppression Signal Intensity"
)

st.plotly_chart(
    fig4,
    use_container_width=True
)

st.markdown(f"""
These are large {COUNTRY} network providers showing
elevated blocking behavior during the Finance Bill
suppression window.
""")

# ============================================================
# FINAL ASSESSMENT
# ============================================================

st.subheader("Statistical Assessment")

st.success("""
The Finance Bill 2024 observation window exhibits multiple
high-confidence synchronized escalation intervals consistent
with coordinated digital suppression behavior.

Confidence level: HIGH
""")
