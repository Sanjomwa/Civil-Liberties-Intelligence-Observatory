# core/theme.py

import logging

import plotly.graph_objects as go
import streamlit as st

from core.constants import (
    PRESSURE_LEVELS,
    PROTOCOL_STATES,
    CONFIDENCE_LEVELS,
    REGIME_STATES,
    CORRELATION_STATES,
    ALIGNMENT_STATES,
    DIVERGENCE_STATES,
)

log = logging.getLogger(__name__)


# ============================================================
# CORE PALETTE
# ============================================================

PALETTE = {
    "bg": "#0D0D0F",
    "panel": "#16161A",
    "text": "#E8E6DF",
    "muted": "#9CA3AF",
    "accent": "#E8593C",
    "amber": "#F0B34A",
    "green": "#2FA36B",
    "blue": "#5B8DEF",
}


# ============================================================
# SHARED CHART LAYOUT
# ============================================================

BASE_LAYOUT = dict(
    paper_bgcolor=PALETTE["bg"],
    plot_bgcolor=PALETTE["bg"],
    font=dict(color=PALETTE["text"]),
    margin=dict(l=40, r=40, t=60, b=40),
    hovermode="x unified",
)


def apply_layout(fig: go.Figure, title=None):
    fig.update_layout(**BASE_LAYOUT)

    if title:
        fig.update_layout(title=title)

    return fig


# ============================================================
# COLOR HELPERS
# ============================================================
# TD-96 fix (2026-08-17): all seven helpers below share the same silent-
# fallback pattern -- MAP.get(value, PALETTE["muted"]) -- which is exactly
# the mechanism that let the old STRESS_LEVELS drift bug (a since-retired
# color map that stopped matching any live value at both its callsites)
# render silent gray indefinitely instead of failing visibly. A hard raise
# is deliberately not used here -- this is a live public dashboard, and
# crashing a real visitor's page on any future unmapped value is worse than
# the current silent-gray behavior. Instead, log a WARNING at the moment of
# fallback so an unmapped value shows up in logs/monitoring; the visible
# behavior (gray fallback for the end user) is unchanged.

def _color_or_fallback(mapping, value, map_name):
    color = mapping.get(value)

    if color is None:
        log.warning(
            "%s: no color mapped for value %r -- falling back to PALETTE['muted']",
            map_name, value,
        )
        return PALETTE["muted"]

    return color


def pressure_level_color(level):
    return _color_or_fallback(PRESSURE_LEVELS, level, "PRESSURE_LEVELS")


def protocol_color(state):
    return _color_or_fallback(PROTOCOL_STATES, state, "PROTOCOL_STATES")


def confidence_color(level):
    return _color_or_fallback(CONFIDENCE_LEVELS, level, "CONFIDENCE_LEVELS")


def regime_color(regime):
    return _color_or_fallback(REGIME_STATES, regime, "REGIME_STATES")


def correlation_color(state):
    return _color_or_fallback(CORRELATION_STATES, state, "CORRELATION_STATES")


def alignment_color(state):
    return _color_or_fallback(ALIGNMENT_STATES, state, "ALIGNMENT_STATES")


def divergence_color(state):
    return _color_or_fallback(DIVERGENCE_STATES, state, "DIVERGENCE_STATES")


# ============================================================
# GLOBAL CSS
# ============================================================
# Visual-only: typography/spacing/status treatment, applied uniformly
# across all 9 pages. Adds no new information and changes no page
# structure, navigation, chart, table, or threshold -- purely how
# existing values are presented.

_CSS = """
<style>
/* Tighten and add breathing room around section headers */
h2, h3 {
    margin-top: 0.35rem !important;
    letter-spacing: -0.01em;
}

/* Metric labels/values: slightly calmer default treatment */
div[data-testid="stMetric"] {
    background: #16161A;
    border: 1px solid #232329;
    border-radius: 10px;
    padding: 0.85rem 1rem 0.7rem 1rem;
}

div[data-testid="stMetricLabel"] {
    opacity: 0.8;
}

/* Long categorical values (e.g. behavioral_class) truncate with an ellipsis
   by default -- wrap instead, same fix category as .clio-badge's overflow
   fix above. Short numeric values are unaffected since they never wrap.
   Streamlit sets white-space/text-overflow directly on the inner <p>, not
   the outer stMetricValue div -- overflow/white-space aren't inherited, so
   the override has to target the <p> itself or it silently does nothing. */
div[data-testid="stMetricValue"] {
    overflow-wrap: break-word;
    word-break: break-word;
    line-height: 1.25;
}

div[data-testid="stMetricValue"] p {
    white-space: normal !important;
    text-overflow: clip !important;
    overflow: visible !important;
    overflow-wrap: break-word;
    word-break: break-word;
}

/* Category/status badges -- filled pill, encodes SEVERITY/state */
.clio-badge-row {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
    max-width: 100%;
    min-width: 0;
}

.clio-badge-label {
    font-size: 0.8rem;
    color: #9CA3AF;
}

.clio-badge {
    display: inline-block;
    font-weight: 600;
    font-size: 1.05rem;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    width: fit-content;
    max-width: 100%;
    box-sizing: border-box;
    white-space: normal;
    overflow-wrap: break-word;
    word-break: break-word;
    line-height: 1.4;
}

/* Filled vs. outlined variants are applied via inline style (background/
   border/color computed per-value in Python -- see components/status.py)
   rather than CSS custom properties, to avoid depending on color-mix()
   browser support. The two variants exist so severity/state badges
   (filled) and confidence/certainty badges (dashed outline) stay
   distinguishable in SHAPE, not just color -- a shared hue (e.g. green)
   should never let "this is fine" (severity) and "we are sure"
   (confidence) read as the same kind of claim. */
.clio-badge-severity {
    font-weight: 700;
}

.clio-badge-confidence {
    background: transparent !important;
    border-style: dashed;
    border-width: 1.5px;
}

/* Shared attribution/provenance footer */
.clio-attribution {
    margin-top: 0.4rem;
    padding-top: 0.6rem;
    border-top: 1px solid #232329;
    color: #9CA3AF;
    font-size: 0.82rem;
    line-height: 1.5;
}

.clio-attribution a {
    color: #9CA3AF;
    text-decoration: underline;
}
</style>
"""


def inject_css():
    st.markdown(_CSS, unsafe_allow_html=True)
