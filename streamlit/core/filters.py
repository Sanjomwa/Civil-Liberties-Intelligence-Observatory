# core/filters.py

import streamlit as st

from core.state import init_state


def render_sidebar():

    init_state()

    with st.sidebar:

        st.title("Observatory Controls")

        st.divider()

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
