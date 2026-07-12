import streamlit as st

from core.config import COUNTRY
from core.filters import render_sidebar
from core.state import init_state
from core.theme import inject_css
from services.marts import get_national_stress, get_protocol_regimes


def _safe_count(records) -> int:
    try:
        return len(records)
    except TypeError:
        return 0


def _is_empty(records) -> bool:
    if records is None:
        return True
    if hasattr(records, "empty"):
        return bool(records.empty)
    return _safe_count(records) == 0


inject_css()
init_state()
render_sidebar()


st.title("🛰️ CLIO — Civil Liberties Intelligence Observatory")

st.caption(
    f"Monitoring network interference, protocol suppression patterns, and "
    f"digital civil-liberties stress signals. {COUNTRY} is the current pilot "
    f"country."
)

st.divider()


# ============================================================
# SYSTEM STATUS
# ============================================================

try:
    national = get_national_stress(st.session_state.start_date, st.session_state.end_date)
    protocols = get_protocol_regimes(st.session_state.start_date, st.session_state.end_date)
except Exception:
    national = []
    protocols = []

if _is_empty(national) or _is_empty(protocols):
    st.warning(
        "Dashboard summary data is currently unavailable. This page remains "
        "available while deployment credentials, BigQuery permissions, or "
        "reporting mart availability are checked."
    )

status_col1, status_col2 = st.columns(2)
with status_col1:
    st.metric("National Stress Records", _safe_count(national))
with status_col2:
    st.metric("Protocol Observations", _safe_count(protocols))

st.divider()


# ============================================================
# WHAT CLIO IS AND ISN'T
# ============================================================

st.subheader("What CLIO is")

st.markdown(
    """
CLIO fuses internet-censorship measurement (OONI), conflict and protest
event data (ACLED), and platform/legal takedown-pressure signals (Google
Transparency Report) into attributed, confidence-qualified findings about
civil-liberties pressure. Kenya is the current pilot country — the
methodology is built to generalize, not to stay Kenya-only.

Every score on this dashboard traces back to named, sourced evidence with an
explicit confidence level. Where evidence is sparse or a statistical window
is unreliable, the platform says so rather than manufacturing false
precision.
"""
)

st.subheader("What CLIO isn't")

st.markdown(
    """
CLIO is **observational and historical, not operational**. It does not
identify individuals, track users, exploit networks, or provide real-time
operational surveillance. It reconstructs civil-liberties pressure from
historical and ongoing evidence — it is not a live alerting system, and its
outputs are evidence-weighted indicators, not definitive proof of intent or
causality. See the Methodology page's "Responsible Use" guidance before
citing any finding.
"""
)

st.divider()


# ============================================================
# PAGE GUIDE
# ============================================================

st.subheader("What's on each page")

page_guide = [
    ("📈 National Stress Observatory",
     "Country-level composite pressure trend, baseline divergence, and suppression-window probability."),
    ("🔗 Protocol Intelligence",
     "Protocol-level (DNS/TCP/TLS/HTTP) regime classification, stress heatmap, and per-app blocking breakdown."),
    ("📡 Protocol ↔ Repression Correlation Engine",
     "Statistical alignment between protocol anomalies and national pressure, per protocol, over rolling windows."),
    ("🧬 ASN Behavioral Intelligence",
     "Network-level (ASN) ranking by blocking intensity, behavioral priority, and evidence maturity."),
    ("🧭 Suppression Event Explorer",
     "Investigate synchronized escalation windows and divergence patterns across the protocol surface."),
    ("📘 Finance Bill 2024 Incident Report",
     "CLIO's flagship validated case study — a forensic reconstruction of the June–July 2024 protest period."),
    ("🧠 Methodology & Statistical Guardrails",
     "How every signal is validated, weighted, and guarded against overstatement before it reaches a score."),
    ("🧾 Pressure Attribution",
     "Decomposes the composite pressure score into its named, sourced drivers for any date — why pressure is elevated, specifically."),
]

for label, desc in page_guide:
    st.markdown(f"**{label}** — {desc}")

st.divider()


# ============================================================
# SUGGESTED READING ORDER
# ============================================================

st.subheader("Suggested reading order")

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**If you're a journalist or NGO / human-rights / legal reader**")
    st.markdown(
        """
        1. 🧾 Pressure Attribution — see *why* pressure is elevated right now
        2. 📘 Finance Bill 2024 Incident Report — the flagship validated case
        3. 🧠 Methodology & Statistical Guardrails — how to responsibly cite a finding
        """
    )
    st.caption(
        "These are CLIO's two identified primary users — both need a citable, "
        "attributed finding, not a raw score."
    )

with col_b:
    st.markdown("**If you're evaluating the methodology itself**")
    st.markdown(
        """
        1. 🧠 Methodology & Statistical Guardrails — start with the guardrails
        2. 🔗 Protocol Intelligence — see the underlying signal quality
        3. 🧾 Pressure Attribution — see how signals combine into a score
        """
    )

st.divider()


# ============================================================
# CAVEATS, UPFRONT
# ============================================================

st.subheader("Before you rely on a finding")

st.warning(
    """
    **Data coverage is uneven across sources.** ACLED conflict-event history
    spans 1997–2026 and continues to extend. OONI/Google-Transparency-driven
    daily marts (behind the composite pressure score) are currently bounded
    to June 2023 – June 2025, pending a data-spine widening. This is a real,
    disclosed limitation — see the Methodology page for detail.
    """
)

st.info(
    """
    **CLIO's OONI- and ACLED-derived intelligence layer is non-commercial and
    grant/public-interest-funded** for the foreseeable term, not a product
    for sale — see the project README's "Data Licensing & Attribution"
    section before using any finding commercially.
    """
)
