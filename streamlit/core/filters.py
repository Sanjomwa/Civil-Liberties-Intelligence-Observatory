# core/filters.py

import streamlit as st

from core.state import init_state


def render_sidebar(show_date_filter=True):
    """
    TD-99 (F6): show_date_filter=False for pages whose data has no date
    dimension (ASN Behavioral Intelligence's asn_behavior_profile_mart is a
    full-history snapshot per TD-02; Methodology & Statistical Guardrails
    never queries a date-filtered mart) -- those pages were previously
    showing Start/End date controls that silently did nothing, with no
    indication to the visitor that the control had no effect.
    """

    init_state()

    with st.sidebar:

        st.title("Observatory Controls")

        st.divider()

        if show_date_filter:

            st.session_state.start_date = st.date_input(
                "Start date",
                st.session_state.start_date
            )

            st.session_state.end_date = st.date_input(
                "End date",
                st.session_state.end_date
            )

            st.divider()

            st.caption(
                "Global filters persist across pages."
            )

        else:

            st.caption(
                "This page's data has no date dimension -- the date filter "
                "used on other pages does not apply here."
            )
