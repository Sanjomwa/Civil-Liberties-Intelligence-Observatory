# core/state.py

import streamlit as st

from core.constants import DEFAULT_START, DEFAULT_END


def init_state():
    defaults = {
        "start_date": DEFAULT_START,
        "end_date": DEFAULT_END,
        "selected_protocols": [],
        "selected_asns": [],
        "selected_page": None,
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
