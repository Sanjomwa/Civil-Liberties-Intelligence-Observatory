"""Reusable status and warning components for Streamlit pages."""

from __future__ import annotations

import streamlit as st


def render_data_status(label: str, value: str, help_text: str | None = None) -> None:
    """Render a compact status pill using Streamlit's built-in metric style."""

    st.metric(label, value, help=help_text)


def render_guardrail_warning(message: str) -> None:
    """Render a consistent warning for sparse or statistically weak windows."""

    st.warning(message)


def render_success_state(message: str) -> None:
    """Render a consistent success status for healthy data states."""

    st.success(message)
