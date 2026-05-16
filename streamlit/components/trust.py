# components/trust.py

import streamlit as st


def render_trust_strip(
    reporting_version=None,
    feature_version=None,
    intelligence_version=None,
    snapshot_at=None,
    max_date=None
):

    with st.container():

        st.caption(
            f"""
Reporting: {reporting_version or "—"} |
Features: {feature_version or "—"} |
Intelligence: {intelligence_version or "—"} |
Snapshot: {snapshot_at or "—"} |
Data through: {max_date or "—"}
"""
        )


def insufficient_history_notice():

    st.warning(
        "Insufficient historical baseline for statistical reliability."
    )


def zero_variance_notice():

    st.info(
        "Signal variance too low for correlation inference."
    )
