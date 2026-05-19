# utils/validate.py

import pandas as pd
import streamlit as st
from typing import Dict, List


# ─────────────────────────────────────────────
# CORE VALIDATION ENGINE
# ─────────────────────────────────────────────

def validate_schema(
    df: pd.DataFrame,
    expected_schema: Dict[str, str],
    context: str = "dataset",
    strict: bool = False
) -> bool:
    """
    Validates dataframe columns against expected schema.

    Args:
        df: DataFrame to validate
        expected_schema: dict of {column_name: type}
        context: label for error messages
        strict: if True, raises error on mismatch

    Returns:
        bool: True if valid
    """

    if df is None or df.empty:
        st.warning(f"[{context}] Empty dataset returned")
        return False

    actual_cols = set(df.columns)
    expected_cols = set(expected_schema.keys())

    missing = expected_cols - actual_cols
    extra = actual_cols - expected_cols

    # ─────────────────────────────────────────
    # WARNINGS (SAFE MODE)
    # ─────────────────────────────────────────

    if missing:
        msg = f"[{context}] Missing columns: {sorted(missing)}"
        if strict:
            raise ValueError(msg)
        st.warning(msg)

    if extra:
        st.info(f"[{context}] Extra columns ignored: {sorted(extra)}")

    # ─────────────────────────────────────────
    # TYPE CHECK (LIGHTWEIGHT)
    # ─────────────────────────────────────────

    type_mismatches = []

    for col, expected_type in expected_schema.items():
        if col not in df.columns:
            continue

        actual_dtype = str(df[col].dtype)

        # relaxed matching (avoid false positives)
        if expected_type == "date":
            if not pd.api.types.is_datetime64_any_dtype(df[col]):
                type_mismatches.append((col, actual_dtype, "datetime"))

        elif expected_type == "numeric":
            if not pd.api.types.is_numeric_dtype(df[col]):
                type_mismatches.append((col, actual_dtype, "numeric"))

    if type_mismatches:
        msg = f"[{context}] Type mismatches: {type_mismatches}"
        if strict:
            raise TypeError(msg)
        st.warning(msg)

    return True


# ─────────────────────────────────────────────
# SAFE FALLBACK HELPERS
# ─────────────────────────────────────────────

def ensure_columns(df: pd.DataFrame, required: List[str]) -> pd.DataFrame:
    """
    Ensures required columns exist (fills with NaN if missing)
    Prevents Streamlit crash loops.
    """

    for col in required:
        if col not in df.columns:
            df[col] = pd.NA

    return df


def safe_date_range(df: pd.DataFrame, column: str, min_date=None, max_date=None):
    """
    Optional hard guard for broken timelines (fixes 1997–2026 bug)
    """

    if column not in df.columns:
        return df

    df[column] = pd.to_datetime(df[column], errors="coerce")

    if min_date:
        df = df[df[column] >= pd.to_datetime(min_date)]

    if max_date:
        df = df[df[column] <= pd.to_datetime(max_date)]

    return df


# ─────────────────────────────────────────────
# PREDEFINED SCHEMAS (OPTIONAL CENTRAL SOURCE)
# ─────────────────────────────────────────────

CIVIL_LIBERTIES_MART_SCHEMA = {
    "measurement_date": "date",
    "block_rate": "numeric",
    "conflict_events": "numeric",
    "fatalities": "numeric",
    "takedown_requests": "numeric",
    "items_removed": "numeric",
    "civil_liberties_pressure_index": "numeric",
    "suppression_window": "string",
}


TAKEDOWN_SCHEMA = {
    "source": "string",
    "platform": "string",
    "reason": "string",
    "requestor_name": "string",
    "requestor_type": "string",
    "number_of_requests": "numeric",
    "items_requested_removal": "numeric",
}
