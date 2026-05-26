# services/bq.py

"""
Centralized BigQuery client + cached query execution.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.auth.exceptions import DefaultCredentialsError, GoogleAuthError
from google.cloud import bigquery
from google.oauth2 import service_account

from core.config import PROJECT_ID


def _get_streamlit_service_account_info() -> dict[str, Any] | None:
    """Return Streamlit Cloud service-account credentials when configured."""

    try:
        service_account_info = st.secrets["gcp_service_account"]
    except (KeyError, FileNotFoundError):
        return None
    except Exception:
        return None

    if not service_account_info:
        return None

    return dict(service_account_info)


@st.cache_resource
def get_client() -> bigquery.Client:
    service_account_info = _get_streamlit_service_account_info()

    if service_account_info:
        credentials = service_account.Credentials.from_service_account_info(
            service_account_info
        )
        return bigquery.Client(project=PROJECT_ID, credentials=credentials)

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
                normalized[column], errors="coerce"
            )

        if (
            lower_name.endswith("_at")
            or lower_name.endswith("_timestamp")
            or "timestamp" in dtype_name
        ):
            normalized[column] = pd.to_datetime(
                normalized[column], errors="coerce"
            )

    return normalized


def _empty_dataframe_with_error(message: str) -> pd.DataFrame:
    st.error(message)
    return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:
    try:
        client = get_client()
        df = client.query(query).to_dataframe()
    except (DefaultCredentialsError, GoogleAuthError):
        return _empty_dataframe_with_error(
            "BigQuery credentials are not configured for this deployment. "
            "Add a Streamlit Cloud gcp_service_account secret or configure "
            "local Google Application Default Credentials."
        )
    except GoogleAPIError:
        return _empty_dataframe_with_error(
            "Dashboard data is temporarily unavailable from BigQuery. "
            "Check dataset permissions, table availability, and query access."
        )
    except Exception as exc:
        st.error(
            "Dashboard data could not be loaded. "
            "Check deployment credentials, BigQuery access, and mart availability."
        )
        st.exception(exc)
        return pd.DataFrame()

    return _normalize_bigquery_dataframe(df)
