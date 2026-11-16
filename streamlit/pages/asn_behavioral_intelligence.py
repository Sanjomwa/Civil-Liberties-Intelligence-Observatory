import streamlit as st
import plotly.graph_objects as go

from core.state import init_state
from core.config import COUNTRY
from core.filters import render_sidebar
from core.theme import apply_layout, inject_css
from services.marts import get_asn_behavior
from components.trust import render_trust_strip, attribution_footer


# ============================================================
# PAGE CONFIG
# ============================================================

inject_css()


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar(show_date_filter=False)


# ============================================================
# DATA
# ============================================================

df = get_asn_behavior()

if df.empty:
    st.warning("No ASN behavioral intelligence available.")
    st.stop()

latest = df.iloc[0]

# Item 32 (2026-11-16): display-only labels for the mart's behavioral_class
# values (asn_behavior_profile_mart.sql bands behavioral_priority_score at
# 1.00 / 0.35 / 0.05). The raw values ("..._SIGNAL_PROVIDER") read as a
# statement about the operator; these describe the score band only.
SCORE_BAND_LABELS = {
    "HIGH_SIGNAL_PROVIDER": "High (score ≥ 1.00)",
    "ELEVATED_SIGNAL_PROVIDER": "Elevated (score ≥ 0.35)",
    "VARIABLE_BEHAVIOR": "Moderate (score ≥ 0.05)",
    "STABLE": "Low (score < 0.05)",
}


def score_band_label(value):
    return SCORE_BAND_LABELS.get(value, value)


# ============================================================
# HEADER
# ============================================================

st.title("🛰️ ASN Behavioral Intelligence")

st.warning(
    "Scores on this page describe OONI measurements taken from probes on "
    "each network: how often tests from those probes looked anomalous. They "
    "do not show what a network operator did. Blocking seen from a network "
    "can come from upstream or transit networks, or from the destination "
    "service itself. The scores are experimental and have not been validated."
)

st.caption(f"""
Measurement profiles for OONI probes on {COUNTRY} networks.

Each profile summarizes:

• how often tests from probes on the network were measured as anomalous
• which protocol's tests were most often anomalous
• how much measurement coverage the network has (evidence reliability)
• how many protocol-days a protocol's anomaly rate was elevated alongside, or apart from, other protocols

**ASN here is the network OONI probes measured from, not a confirmed
location of interference (TD-95).** These profiles reflect what was
observed as unreachable from probes on that network — not that the
named ASN itself performed the blocking, as opposed to upstream/transit
interference or a destination service's own geoblocking. See
Methodology & Statistical Guardrails for detail.
""")


render_trust_strip(
    reporting_version=latest["reporting_version"],
    snapshot_at=latest["snapshot_at"],
    max_date="Latest Profile Snapshot"
)

st.divider()


# ============================================================
# ASN FILTER
# ============================================================

asn = st.selectbox(
    "Select ASN",
    df["display_asn"].unique()
)

asn_df = df[df["display_asn"] == asn]
row = asn_df.iloc[0]


# ============================================================
# KPI ROW
# ============================================================

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Measurement anomaly score (experimental)",
    f"{row['behavioral_priority_score']:.3f}"
)

c2.metric(
    "Evidence Reliability",
    f"{row['data_reliability_score']:.2f}"
)

c3.metric(
    "Dominant Protocol",
    row["dominant_protocol"]
)

c4.metric(
    "Anomaly score band (experimental)",
    score_band_label(row["behavioral_class"])
)

st.divider()


# Item 29 (2026-11-16): the per-ASN "Behavioral Signal Profile" chart
# (with "Blocking Signal Intensity") and the "Top ASN Behavioral Priority
# Ranking" chart were removed from public view: both put an ASN beside a
# blocking/censorship-evidence score.


# ============================================================
# ESCALATION PROFILE
# ============================================================

st.subheader("Escalation Relationship Profile")

coupled_days = row["coupled_escalation_days"]
isolated_days = row["isolated_escalation_days"]

if not coupled_days and not isolated_days:
    st.info(
        f"{asn} recorded zero coupled and zero isolated escalation days "
        "in the observed window -- a real reading, not missing data."
    )
else:
    fig3 = go.Figure()

    fig3.add_trace(go.Bar(
        name="Coupled Escalation",
        x=["Escalation"],
        y=[coupled_days]
    ))

    fig3.add_trace(go.Bar(
        name="Isolated Escalation",
        x=["Escalation"],
        y=[isolated_days]
    ))

    apply_layout(
        fig3,
        "Escalation Relationship Profile"
    )

    st.plotly_chart(fig3, use_container_width=True)

st.markdown("""
Counts are protocol-days. A coupled escalation day is a protocol-day when that
protocol's anomaly rate, measured from probes on this network, was above its
baseline and moved together with another protocol's anomaly rate. An isolated
escalation day is one when it was above baseline without that co-movement. Both describe measurements, not
what any network operator did.
""")

st.divider()


# Item 32 (2026-11-16): the "Network Intelligence Summary" card, which
# displayed the mart's auto-generated summary_insight sentences, was
# removed from public view (the sentences asserted blocking behavior the
# measurements do not establish). get_asn_behavior() still returns the
# column; it is just no longer displayed here or in the table below.


# ============================================================
# FULL TABLE
# ============================================================

st.subheader("ASN Measurement Table")

table_df = df[
    [
        "display_asn",
        "network_class",
        "dominant_protocol",
        "behavioral_priority_score",
        "behavioral_class",
        "data_reliability_score",
    ]
].copy()
table_df["behavioral_class"] = table_df["behavioral_class"].map(score_band_label)

st.dataframe(
    table_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "display_asn": "ASN",
        "network_class": "Network class",
        "dominant_protocol": "Most often anomalous protocol",
        "behavioral_priority_score": "Measurement anomaly score (experimental)",
        "behavioral_class": "Anomaly score band (experimental)",
        "data_reliability_score": "Evidence reliability",
    },
)

st.divider()

attribution_footer(["OONI"], snapshot_at=latest["snapshot_at"])
