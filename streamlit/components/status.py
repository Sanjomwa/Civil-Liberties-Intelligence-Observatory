"""Reusable status and warning components for Streamlit pages."""

from __future__ import annotations

import streamlit as st


def render_data_status(label: str, value: str, help_text: str | None = None) -> None:
    """Render a compact status pill using Streamlit's built-in metric style."""

    st.metric(label, value, help=help_text)


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


# Confidence tiers are visually distinct in kind, not severity: a plain
# question mark for "we don't know" reads as neither reassuring nor
# alarming, which INSUFFICIENT_DATA's neutral gray is meant to convey.
_CONFIDENCE_ICONS = {
    "HIGH": "✓",  # check
    "MEDIUM": "~",
    "LOW": "!",
    "INSUFFICIENT_DATA": "?",
    "UNKNOWN": "?",
}


def render_state_badge(label: str, value, color: str) -> None:
    """
    Filled pill for a SEVERITY/state value (protocol state, regime,
    alignment state, correlation state, divergence state, suppression
    window class, pressure level) -- one of theme.py's *_color() helpers
    supplies `color`. Visually distinct from render_confidence_badge
    (filled vs. dashed outline) so severity and certainty never look
    like the same kind of claim just because they share a hue.
    """

    display = "—" if value is None or (isinstance(value, float) and value != value) else str(value)
    r, g, b = _hex_to_rgb(color)

    st.markdown(
        f"""
        <div class="clio-badge-row">
            <div class="clio-badge-label">{label}</div>
            <div class="clio-badge clio-badge-severity"
                 style="background: rgba({r},{g},{b},0.18);
                        color: {color};
                        border: 1px solid rgba({r},{g},{b},0.5);">
                {display}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_confidence_badge(label: str, value, color: str) -> None:
    """
    Dashed-outline pill for a CONFIDENCE/certainty value only (HIGH /
    MEDIUM / LOW / INSUFFICIENT_DATA) -- pass the color from
    theme.confidence_color(value). Deliberately never filled, so it
    cannot be mistaken for a severity reading at a glance.
    """

    display = "—" if value is None or (isinstance(value, float) and value != value) else str(value)
    icon = _CONFIDENCE_ICONS.get(display, "")
    r, g, b = _hex_to_rgb(color)

    st.markdown(
        f"""
        <div class="clio-badge-row">
            <div class="clio-badge-label">{label}</div>
            <div class="clio-badge clio-badge-confidence"
                 style="color: {color}; border-color: {color};">
                {icon + " " if icon else ""}{display}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_guardrail_warning(message: str) -> None:
    """Render a consistent warning for sparse or statistically weak windows."""

    st.warning(message)


def render_success_state(message: str) -> None:
    """Render a consistent success status for healthy data states."""

    st.success(message)
