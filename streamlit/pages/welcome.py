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
    f"Historical network-measurement anomalies, aggregated conflict data, "
    f"and derived civil-liberties pressure indicators. {COUNTRY} is the "
    f"current pilot country."
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
CLIO shows three kinds of evidence side by side: network-measurement
results from OONI probes, ACLED's weekly aggregated conflict and protest
data, and platform takedown-request counts from the Google Transparency
Report. From these it derives confidence-qualified indicators of
civil-liberties pressure, some of them experimental or retired. The data is
historical: OONI measurements run to June 2025, and ACLED weeks run to the
week of 2026-03-14. Kenya is the current pilot country — the methodology is
built to generalize, not to stay Kenya-only.

Each page names its data sources. Several measures are experimental or
retired and are labelled as such on the page. Where evidence is sparse or a statistical window
is unreliable, the platform says so rather than manufacturing false
precision.
"""
)

st.subheader("What CLIO isn't")

st.markdown(
    """
CLIO is **observational and historical, not operational**. It does not
identify individuals, track users, exploit networks, or provide real-time
operational surveillance. It derives civil-liberties pressure indicators
from historical data — it is not a live alerting system, and its
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
     "Country-level composite pressure index (experimental), protocol escalation load, and the ACLED regime classification."),
    ("🔗 Protocol Intelligence",
     "Protocol-level (DNS/TCP/TLS/HTTP) regime classification, stress heatmap, and per-app blocking breakdown."),
    ("📡 Protocol ↔ Repression Correlation Engine",
     "Protocol anomaly measures compared with the composite pressure index, using a correlation method that is "
     "labelled as retired -- two tabs: Protocol Drill-Down (one protocol over time) and Date Snapshot (every "
     "protocol's values on one date; merged from a former separate page, TD-98)."),
    ("🧬 ASN Behavioral Intelligence",
     "Per-network (ASN) measurement profiles: an experimental measurement anomaly score and evidence "
     "reliability for OONI probes on each network. Not a ranking of operators."),
    ("📘 Finance Bill 2024: what the retired correlation method showed",
     "A case study of the old correlation method's null result for the June–July 2024 protest period, and why the method was retired."),
    ("🧠 Methodology & Statistical Guardrails",
     "How each signal is checked, weighted, and guarded against overstatement before it reaches a score, and what has not been validated."),
    ("🧾 Pressure Attribution",
     "Splits the composite pressure index for a chosen date into its two arithmetic inputs (ACLED weekly conflict intensity and Google Transparency platform pressure), with that day's OONI measurements shown alongside."),
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
        1. 🧾 Pressure Attribution — see which inputs make up the composite index on a date
        2. 📘 Finance Bill 2024 (retired method) — the Finance Bill 2024 case study (a null result for a retired method)
        3. 🧠 Methodology & Statistical Guardrails — how to responsibly cite a finding
        """
    )
    st.caption(
        "These are CLIO's two identified primary users — both need to know "
        "what a number was derived from and what it does not show, not just "
        "a raw score."
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
    **Data coverage is uneven across sources.** ACLED weekly aggregated
    conflict data spans 1997 to the week of 2026-03-14. OONI/Google-Transparency-driven
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
