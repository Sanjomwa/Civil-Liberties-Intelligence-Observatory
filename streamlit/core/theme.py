# core/theme.py

import plotly.graph_objects as go

from core.constants import (
    STRESS_LEVELS,
    PROTOCOL_STATES,
    CONFIDENCE_LEVELS
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
