# app.py

import streamlit as st

from core.config import COUNTRY
from core.state import init_state
from core.filters import render_sidebar

from services.marts import (
    get_national_stress,
    get_protocol_regimes,
)


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


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=f"{COUNTRY} Civil Liberties Observatory",
    page_icon="🛰️",
    layout="wide",
)

# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()

# ============================================================
# LANDING PAGE
# ============================================================

st.title(f"🛰️ {COUNTRY} Civil Liberties Observatory")

st.caption(
    f"""
    Monitoring network interference, protocol suppression patterns,
    and digital civil-liberties stress signals across {COUNTRY}
    (June 2023 – June 2025).
    """
)

st.divider()

# ============================================================
# LOAD SUMMARY DATA
# ============================================================

try:
    national = get_national_stress(
        st.session_state.start_date,
        st.session_state.end_date,
    )

    protocols = get_protocol_regimes(
        st.session_state.start_date,
        st.session_state.end_date,
    )
except Exception:
    national = []
    protocols = []

if _is_empty(national) or _is_empty(protocols):
    st.warning(
        "Dashboard summary data is currently unavailable. "
        "The landing page remains available while deployment credentials, "
        "BigQuery permissions, or reporting mart availability are checked."
    )

# ============================================================
# SYSTEM STATUS
# ============================================================

col1, col2 = st.columns(2)

with col1:
    st.metric(
        "National Stress Records",
        _safe_count(national),
    )

with col2:
    st.metric(
        "Protocol Observations",
        _safe_count(protocols),
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
