# services/bq.py

"""
Centralized BigQuery client + cached query execution.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st
from google.cloud import bigquery

from core.config import PROJECT_ID


@st.cache_resource
def get_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def _normalize_bigquery_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize BigQuery extension dtypes that confuse dashboard contracts."""

    if df.empty:
        return df

    normalized = df.copy()

    for column in normalized.columns:
        lower_name = column.lower()
        dtype_name = str(normalized[column].dtype).lower()

        if (
            lower_name.endswith("_date")
            or lower_name == "date_key"
            or "dbdate" in dtype_name
        ):
            normalized[column] = pd.to_datetime(
                normalized[column], errors="coerce")

        if (
            lower_name.endswith("_at")
            or lower_name.endswith("_timestamp")
            or "timestamp" in dtype_name
        ):
            normalized[column] = pd.to_datetime(
                normalized[column], errors="coerce")

    return normalized


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    client = get_client()
    df = client.query(query).to_dataframe()
    return _normalize_bigquery_dataframe(df)
