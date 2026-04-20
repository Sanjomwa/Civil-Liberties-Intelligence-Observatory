# streamlit/utils/bq_client.py

import os
import re
from typing import List, Optional, Sequence

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter
from google.oauth2 import service_account
from streamlit.errors import StreamlitSecretNotFoundError


PROJECT_ID = "encoded-joy-485413-k5"

_env = os.getenv("BRUIN_ENVIRONMENT")
DATASET = "reporting" if _env == "prod" else "marts"

ALLOWED_TABLES = {
    "civil_liberties_mart",
    "platform_censorship_mart",
}

# -----------------------------
# SAFETY LAYER
# -----------------------------

FORBIDDEN_SQL_PATTERNS = [
    r"\bdrop\b",
    r"\bdelete\b",
    r"\binsert\b",
    r"\bupdate\b",
    r"\balter\b",
    r"\btruncate\b",
    r"\bcreate\b",
]


def validate_sql(sql: str) -> None:
    """Ensures only safe SELECT queries are executed."""
    sql_lower = sql.strip().lower()

    if not sql_lower.startswith("select"):
        raise ValueError("Only SELECT queries are allowed.")

    for pattern in FORBIDDEN_SQL_PATTERNS:
        if re.search(pattern, sql_lower):
            raise ValueError(f"Unsafe SQL detected: {pattern}")


def enforce_limit(sql: str, limit: int = 1000) -> str:
    """Adds LIMIT if missing (prevents accidental full scans)."""
    if "limit" not in sql.lower():
        return sql.rstrip(";") + f"\nLIMIT {limit}"
    return sql


def sql_in(values: Sequence[str]) -> str:
    """Safe SQL IN clause builder."""
    cleaned = [v.replace("'", "''") for v in values if v is not None]
    if not cleaned:
        return "('')"
    return "(" + ",".join(f"'{v}'" for v in cleaned) + ")"


# -----------------------------
# CLIENT
# -----------------------------

@st.cache_resource(show_spinner=False)
def get_client() -> bigquery.Client:
    try:
        if "gcp_service_account" in st.secrets:
            creds = service_account.Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=["https://www.googleapis.com/auth/cloud-platform"],
            )
            return bigquery.Client(project=PROJECT_ID, credentials=creds)
    except StreamlitSecretNotFoundError:
        pass

    return bigquery.Client(project=PROJECT_ID)


# -----------------------------
# TABLE SAFETY
# -----------------------------

def table(name: str) -> str:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Table {name} is not allowed.")
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


# -----------------------------
# QUERY ENGINE
# -----------------------------

@st.cache_data(ttl=1800, show_spinner=False)
def run_query(
    sql: str,
    params: Optional[List] = None,
    limit: Optional[int] = None,
) -> pd.DataFrame:

    validate_sql(sql)

    if limit is not None:
        sql = enforce_limit(sql, limit)

    client = get_client()
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])

    return client.query(sql, job_config=job_config).to_dataframe()


# -----------------------------
# MART HELPERS (SAFE)
# -----------------------------

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
    """

    params = [
        ScalarQueryParameter("start_date", "DATE", start_date),
        ScalarQueryParameter("end_date", "DATE", end_date),
    ]

    if platforms:
        sql += " AND platform IN UNNEST(@platforms)"
        params.append(
            ArrayQueryParameter("platforms", "STRING", platforms)
        )

    sql += "\nORDER BY measurement_date"

    return run_query(sql, params)


# -----------------------------
# UI CONSTANTS
# -----------------------------

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
