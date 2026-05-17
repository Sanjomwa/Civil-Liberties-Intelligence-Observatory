# app.py

import streamlit as st

from core.constants import (
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    PAGES
)

from core.filters import render_sidebar
from core.state import init_state

from components.kpis import metric_row

from services.marts import (
    get_national_stress,
    get_protocol_trends,
    get_protocol_correlation,
    get_asn_profiles
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title=APP_NAME,
    page_icon="📡",
    layout="wide"
)


# ============================================================
# INIT
# ============================================================

init_state()
render_sidebar()


# ============================================================
# HEADER
# ============================================================

st.title(APP_NAME)

st.caption(
    f"{APP_TAGLINE} • {APP_VERSION}"
)

st.divider()


# ============================================================
# NAV PREVIEW
# ============================================================

st.subheader("Observatory Modules")

for page in PAGES:
    st.markdown(f"- {page}")


st.divider()


# ============================================================
# CONNECTIVITY SMOKE TEST
# ============================================================

st.subheader("System Health")


try:

    stress = get_national_stress(
        st.session_state.start_date,
        st.session_state.end_date
    )

    protocols = get_protocol_trends(
        st.session_state.start_date,
        st.session_state.end_date
    )

    corr = get_protocol_correlation(
        st.session_state.start_date,
        st.session_state.end_date
    )

    asns = get_asn_profiles()

    metric_row([
        ("National Stress Rows", f"{len(stress):,}"),
        ("Protocol Trend Rows", f"{len(protocols):,}"),
        ("Correlation Rows", f"{len(corr):,}"),
        ("ASN Profiles", f"{len(asns):,}")
    ])

    st.success("All marts connected successfully.")

except Exception as e:

    st.error("Connectivity test failed.")
    st.exception(e)


st.divider()


# ============================================================
# STATUS
# ============================================================

st.info(
    """
Shell build complete.

Next:
Step 6 → National Stress Observatory
"""
)
