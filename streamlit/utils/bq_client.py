# streamlit/utils/bq_client.py

import os
from typing import List, Optional

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter
from google.oauth2 import service_account

PROJECT_ID = "encoded-joy-485413-k5"

_env = os.getenv("BRUIN_ENVIRONMENT")
DATASET = "reporting"


# ─────────────────────────────────────────────
# EXPANDED TABLE WHITELIST (FIX FOR PAGES 6–8)
# ─────────────────────────────────────────────

ALLOWED_TABLES = {
    # core marts
    "civil_liberties_mart",
    "platform_censorship_mart",

    # used in Page 8 explorer
    "fact_takedown_trends",
    "fact_conflict_events",
    "fact_platform_blocking_summary",
    "fact_censorship_measurements",
    "fact_censorship_impact",
    "fact_takedown_requests",

    # dims
    "dim_dates",
    "dim_regions",
    "dim_platforms",
    "dim_test_categories",
    "dim_reasons",
    "dim_event_types",
    "dim_requestors",
}

# BELOW ALLOWED_TABLES

ALLOWED_COLUMNS = {
    "civil_liberties_mart": {
        "measurement_date",
        "block_rate",
        "blocked_tests",
        "conflict_events",
        "fatalities",
        "takedown_requests",
        "items_removed",
        "google_requests",
        "civil_liberties_pressure_index",
        "suppression_window",
        "has_blocking",
        "has_conflict",
        "conflict_block_overlap",
        "ooni_tests",
        "network_block_signals",
    }    
}

# ─────────────────────────────────────────────
# BIGQUERY CLIENT
# ─────────────────────────────────────────────

@st.cache_resource(show_spinner=False)
def get_client() -> bigquery.Client:
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(project=PROJECT_ID, credentials=creds)
    except Exception:
        pass

    return bigquery.Client(project=PROJECT_ID)


# ─────────────────────────────────────────────
# SAFE TABLE ACCESS
# ─────────────────────────────────────────────

def table(name: str) -> str:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Table not allowed: {name}")
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


# ─────────────────────────────────────────────
# QUERY ENGINE (HARDENED)
# ─────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def run_query(
    sql: str,
    params: Optional[List] = None
) -> pd.DataFrame:
    client = get_client()

    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=params or []
        )

        query_job = client.query(sql, job_config=job_config)
        df = query_job.to_dataframe()

        return df

    except Exception as e:
        # IMPORTANT: expose error cleanly to Streamlit pages
        st.error(f"BigQuery error: {str(e)}")
        return pd.DataFrame()


# ─────────────────────────────────────────────
# MART HELPERS (FIXED PARAM TYPES)
# ─────────────────────────────────────────────

def get_civil_liberties_data(start_date: str, end_date: str) -> pd.DataFrame:
    sql = f"""
        SELECT
            measurement_date,
            block_rate,
            blocked_tests,
            conflict_events,
            takedown_requests,
            items_removed,
            civil_liberties_pressure_index,
            suppression_window
        FROM {table("civil_liberties_mart")}
        WHERE measurement_date BETWEEN @start_date AND @end_date
        ORDER BY measurement_date
    """

    params = [
        ScalarQueryParameter("start_date", "DATE", start_date),
        ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    return run_query(sql, params)


def get_platform_censorship_data(
    start_date: str,
    end_date: str,
    platforms: Optional[List[str]] = None,
) -> pd.DataFrame:

    params = [
        ScalarQueryParameter("start_date", "DATE", start_date),
        ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    platform_filter = ""

    if platforms:
        platform_filter = "AND platform IN UNNEST(@platforms)"
        params.append(
            ArrayQueryParameter("platforms", "STRING", platforms)
        )

    sql = f"""
        SELECT
            measurement_date,
            platform,
            block_rate,
            blocked,
            tests,
            takedown_requests,
            items_removed,
            platform_pressure_score
        FROM {table("platform_censorship_mart")}
        WHERE measurement_date BETWEEN @start_date AND @end_date
        {platform_filter}
        ORDER BY measurement_date
    """

    return run_query(sql, params)


# ─────────────────────────────────────────────
# UI CONSTANTS (UNCHANGED)
# ─────────────────────────────────────────────

PALETTE = {
    "coral": "#E8593C",
    "amber": "#EF9F27",
    "teal": "#1D9E75",
    "purple": "#7F77DD",
    "blue": "#378ADD",
    "gray": "#888780",
    "bg": "#0D0D0F",
    "bg2": "#16161A",
    "text": "#E8E6DF",
    "muted": "#6B6966",
}

STATUS_COLORS = {
    "confirmed": "#E8593C",
    "anomaly": "#EF9F27",
    "failure": "#7F77DD",
    "ok": "#1D9E75",
}

SUPPRESSION_COLORS = {
    "Full Suppression Window": "#E8593C",
    "Blocking + Protest Day": "#EF9F27",
    "Blocking + Removal Activity": "#7F77DD",
    "Blocking Only": "#378ADD",
    "No Suppression Signal": "#1D9E75",
}
