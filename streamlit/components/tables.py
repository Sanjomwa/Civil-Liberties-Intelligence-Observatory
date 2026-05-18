"""Reusable table helpers for dashboard pages."""

from __future__ import annotations

from collections.abc import Sequence

import pandas as pd
import streamlit as st


def render_table(
    df: pd.DataFrame,
    columns: Sequence[str] | None = None,
    *,
    empty_message: str = "No records match the current filters.",
) -> None:
    """Render a dataframe with a consistent empty state."""

    if df.empty:
        st.info(empty_message)
        return

    view = df[list(columns)] if columns else df
    st.dataframe(view, use_container_width=True, hide_index=True)


def latest_by_group(
    df: pd.DataFrame,
    group_col: str,
    date_col: str,
) -> pd.DataFrame:
    """Return the latest row per group for ranking tables."""

    if df.empty:
        return df

    return df.sort_values(date_col).groupby(group_col, as_index=False).tail(1)
