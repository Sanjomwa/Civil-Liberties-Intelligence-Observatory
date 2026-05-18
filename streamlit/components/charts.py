"""Reusable Streamlit chart helpers.

The current dashboard pages mostly build Plotly figures inline. Keep shared
chart formatting here as repeated visuals stabilize.
"""

from __future__ import annotations

import plotly.graph_objects as go


def add_threshold_lines(
    fig: go.Figure,
    values: list[float],
    *,
    opacity: float = 0.45,
    line_dash: str = "dot",
) -> go.Figure:
    """Add horizontal reference lines to a Plotly figure."""

    for value in values:
        fig.add_hline(y=value, opacity=opacity, line_dash=line_dash)

    return fig


def empty_figure(title: str = "No data available") -> go.Figure:
    """Return a consistent empty-state figure for dashboard pages."""

    fig = go.Figure()
    fig.update_layout(
        title=title,
        xaxis={"visible": False},
        yaxis={"visible": False},
        annotations=[
            {
                "text": "No records match the current filters.",
                "xref": "paper",
                "yref": "paper",
                "showarrow": False,
                "x": 0.5,
                "y": 0.5,
            }
        ],
    )
    return fig
