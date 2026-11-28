# app.py
#
# Thin st.navigation entrypoint. Page content lives in pages/*.py; each page
# owns its title/icon via st.Page() below rather than its own
# st.set_page_config() call (Streamlit only allows one call per run).

import streamlit as st

from content_flags import ACLED_CONTENT_ENABLED

st.set_page_config(
    page_title="CLIO — Civil Liberties Intelligence Observatory",
    page_icon="🛰️",
    layout="wide",
)

# WITHDRAWN 2026-11 (item 48): these three pages are ACLED-based and are
# listed only while ACLED_CONTENT_ENABLED is True (content_flags.py). With
# st.navigation, a page that is not in the list cannot be reached by URL.
# Do not re-list without the owner's decision.
_ACLED_PAGES = [
    # TD-98: merged with the former separate "Suppression Event Explorer"
    # page (pages/suppression_event_explorer.py, deleted) as a second tab --
    # both queried the same reporting.protocol_repression_correlation_mart
    # and told the same weak-correlation story in two separate nav entries.
    st.Page("pages/protocol_repression_correlation_engine.py", title="Protocol Anomalies vs. Composite Index", icon="📡"),
    st.Page("pages/finance_bill_2024_incident_report.py", title="Finance Bill 2024 (retired method)", icon="📘"),
    st.Page("pages/pressure_attribution.py", title="Pressure Attribution", icon="🧾"),
]

pages = st.navigation([
    st.Page("pages/welcome.py", title="Welcome", icon="🛰️", default=True),
    st.Page("pages/national_stress_observatory.py", title="National Stress Observatory", icon="📈"),
    st.Page("pages/protocol_intelligence.py", title="Protocol Intelligence", icon="🔗"),
    st.Page("pages/asn_behavioral_intelligence.py", title="Network Measurement Profiles (ASN)", icon="🧬"),
    st.Page("pages/methodology_statistical_guardrails.py", title="Methodology & Statistical Guardrails", icon="🧠"),
] + (_ACLED_PAGES if ACLED_CONTENT_ENABLED else []))

pages.run()
