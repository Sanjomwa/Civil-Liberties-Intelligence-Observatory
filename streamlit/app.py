# app.py
#
# Thin st.navigation entrypoint. Page content lives in pages/*.py; each page
# owns its title/icon via st.Page() below rather than its own
# st.set_page_config() call (Streamlit only allows one call per run).

import streamlit as st

st.set_page_config(
    page_title="CLIO — Civil Liberties Intelligence Observatory",
    page_icon="🛰️",
    layout="wide",
)

pages = st.navigation([
    st.Page("pages/welcome.py", title="Welcome", icon="🛰️", default=True),
    st.Page("pages/national_stress_observatory.py", title="National Stress Observatory", icon="📈"),
    st.Page("pages/protocol_intelligence.py", title="Protocol Intelligence", icon="🔗"),
    st.Page("pages/protocol_repression_correlation_engine.py", title="Protocol ↔ Repression Correlation Engine", icon="📡"),
    st.Page("pages/asn_behavioral_intelligence.py", title="ASN Behavioral Intelligence", icon="🧬"),
    st.Page("pages/suppression_event_explorer.py", title="Suppression Event Explorer", icon="🧭"),
    st.Page("pages/finance_bill_2024_incident_report.py", title="Finance Bill 2024 Incident Report", icon="📘"),
    st.Page("pages/methodology_statistical_guardrails.py", title="Methodology & Statistical Guardrails", icon="🧠"),
    st.Page("pages/pressure_attribution.py", title="Pressure Attribution", icon="🧾"),
])

pages.run()
