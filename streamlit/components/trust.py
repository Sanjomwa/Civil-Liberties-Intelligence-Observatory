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


def synthetic_data_notice(sources):
    """
    TD-01: sources is a list of source names (e.g. ["Lumen"]) currently
    contributing synthetic/fabricated data to what's displayed. Callers
    gate this on a real per-row/per-date flag from the dataframe, not a
    hardcoded True -- it stops firing on its own once real data replaces
    the fabricated set.
    """

    if not sources:
        return

    joined = ", ".join(sources)

    st.warning(
        f"Contains fabricated data: {joined} figures on this page are "
        "synthetic (generated for development, not sourced from a real "
        "export) and should not be cited as evidence."
    )
