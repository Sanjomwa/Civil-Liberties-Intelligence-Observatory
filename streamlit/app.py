# app.py

import streamlit as st

from core.state import init_state
from core.filters import render_sidebar

from services.marts import (
    get_national_stress,
    get_protocol_regimes
)

# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Kenya Civil Liberties Observatory",
    page_icon="🛰️",
    layout="wide"
)

# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()

# ============================================================
# LOAD SUMMARY DATA
# ============================================================

national = get_national_stress(
    st.session_state.start_date,
    st.session_state.end_date
)

protocols = get_protocol_regimes(
    st.session_state.start_date,
    st.session_state.end_date
)

# ============================================================
# LANDING PAGE
# ============================================================

st.title("🛰️ Kenya Civil Liberties Observatory")

st.caption(
    """
    Monitoring network interference, protocol suppression patterns,
    and digital civil-liberties stress signals across Kenya
    (June 2023 – June 2025).
    """
)

st.divider()

# ============================================================
# SYSTEM STATUS
# ============================================================

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "National Stress Records",
        len(national)
    )

with col2:
    st.metric(
        "Protocol Observations",
        len(protocols)
    )

st.divider()

# ============================================================
# NAVIGATION HELP
# ============================================================

st.subheader("Available Observatory Views")

st.markdown("""
### 📈 National Stress Observatory
Country-level pressure trends and suppression probability.

### 🌐 Protocol Regime Monitor
Protocol-by-protocol escalation states and confidence levels.

### 🔗 Protocol Stress Intelligence Observatory
Protocol-level anomaly pressure, escalation behavior, and statistical confidence.
            
### 📊 Protocol Repression Correllation Engine
Statistical linkages between protocol stress and national-level suppression.

### 🧠 ASN Behavioral Intelligence 
Network-level anomaly concentration detection.

### 🚨 Suppression Event Explorer 
Interactive investigation timelines.

### 📜 Finance Bill Incident Report 
Narrative reconstruction of June 2024 events.

### ⚖ Methodology & Statistical Guardrails 
Scientific thresholds, assumptions, and limitations.
""")

st.divider()

st.info(
    "Use the left sidebar filters to adjust analysis windows "
    "before opening observatory pages."
)
