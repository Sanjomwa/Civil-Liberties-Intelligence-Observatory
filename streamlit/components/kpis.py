# components/kpis.py

import streamlit as st


def metric_row(metrics):
    """
    metrics format:

    [
        ("Label", "Value"),
        ("Label", "Value"),
        ...
    ]
    """

    cols = st.columns(len(metrics))

    for col, (label, value) in zip(cols, metrics):
        col.metric(label, value)
