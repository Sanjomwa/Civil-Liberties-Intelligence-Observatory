import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from core.state import init_state
from core.filters import render_sidebar
from core.theme import apply_layout
from services.marts import get_asn_behavior
from components.trust import render_trust_strip


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="ASN Behavioral Intelligence",
    page_icon="🛰️",
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

df = get_asn_behavior()

if df.empty:
    st.warning("No ASN behavioral intelligence available.")
    st.stop()

latest = df.iloc[0]


# ============================================================
# HEADER
# ============================================================

st.title("🛰️ ASN Behavioral Intelligence")

st.caption("""
Behavioral observability profiles across Kenyan networks.

This reveals:

• which ASNs emit strongest censorship evidence  
• dominant protocol pressure signatures  
• network reliability maturity  
• escalation coupling behavior  
• observability concentration across providers
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
    "Behavior Priority",
    f"{row['behavioral_priority_score']:.3f}"
)

c2.metric(
    "Reliability",
    f"{row['data_reliability_score']:.2f}"
)

c3.metric(
    "Dominant Protocol",
    row["dominant_protocol"]
)

c4.metric(
    "Behavior Class",
    row["behavioral_class"]
)

st.divider()


# ============================================================
# SIGNAL PROFILE
# ============================================================

fig = go.Figure()

fig.add_trace(go.Bar(
    x=[
        "Maturity Signal",
        "Reliability",
        "Coverage",
        "Blocking Intensity"
    ],
    y=[
        row["maturity_adjusted_signal"],
        row["data_reliability_score"],
        row["coverage_ratio"],
        row["avg_weighted_blocking"]
    ]
))

apply_layout(
    fig,
    f"{asn} Behavioral Signal Profile"
)

st.plotly_chart(fig, use_container_width=True)

st.markdown("""
**Plain English**

Higher values indicate stronger and more statistically trustworthy
censorship evidence from this network.
""")

st.divider()


# ============================================================
# ASN RANKING
# ============================================================

fig2 = px.bar(
    df.head(20),
    x="display_asn",
    y="behavioral_priority_score",
    color="behavioral_class"
)

apply_layout(
    fig2,
    "Top ASN Behavioral Priority Ranking"
)

st.plotly_chart(fig2, use_container_width=True)

st.markdown("""
This ranks Kenyan networks by strategic censorship signal importance.
""")

st.divider()


# ============================================================
# ESCALATION PROFILE
# ============================================================

fig3 = go.Figure()

fig3.add_trace(go.Bar(
    name="Coupled Escalation",
    x=["Escalation"],
    y=[row["coupled_escalation_days"]]
))

fig3.add_trace(go.Bar(
    name="Isolated Escalation",
    x=["Escalation"],
    y=[row["isolated_escalation_days"]]
))

apply_layout(
    fig3,
    "Escalation Relationship Profile"
)

st.plotly_chart(fig3, use_container_width=True)

st.markdown("""
Coupled escalation means this ASN participates in wider synchronized
multi-protocol suppression behavior.
""")

st.divider()


# ============================================================
# INSIGHT CARD
# ============================================================

st.subheader("Network Intelligence Summary")

st.info(row["summary_insight"])

st.divider()


# ============================================================
# FULL TABLE
# ============================================================

st.subheader("ASN Intelligence Table")

st.dataframe(
    df[
        [
            "display_asn",
            "network_class",
            "dominant_protocol",
            "behavioral_priority_score",
            "behavioral_class",
            "data_reliability_score",
            "summary_insight"
        ]
    ],
    use_container_width=True,
    hide_index=True
)
