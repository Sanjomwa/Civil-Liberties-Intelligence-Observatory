# core/theme.py

import plotly.graph_objects as go
import streamlit as st

from core.constants import (
    STRESS_LEVELS,
    PROTOCOL_STATES,
    CONFIDENCE_LEVELS,
    REGIME_STATES,
    CORRELATION_STATES,
    ALIGNMENT_STATES,
    DIVERGENCE_STATES,
)


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

def stress_color(level):
    return STRESS_LEVELS.get(level, PALETTE["muted"])


def protocol_color(state):
    return PROTOCOL_STATES.get(state, PALETTE["muted"])


def confidence_color(level):
    return CONFIDENCE_LEVELS.get(level, PALETTE["muted"])


def regime_color(regime):
    return REGIME_STATES.get(regime, PALETTE["muted"])


def correlation_color(state):
    return CORRELATION_STATES.get(state, PALETTE["muted"])


def alignment_color(state):
    return ALIGNMENT_STATES.get(state, PALETTE["muted"])


def divergence_color(state):
    return DIVERGENCE_STATES.get(state, PALETTE["muted"])


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
