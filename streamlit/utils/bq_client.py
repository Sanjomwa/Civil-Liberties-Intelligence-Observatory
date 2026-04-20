# streamlit/utils/bq_client.py

import os
from typing import List, Optional

import pandas as pd
import streamlit as st
from google.cloud import bigquery
from google.cloud.bigquery import ScalarQueryParameter, ArrayQueryParameter
from google.oauth2 import service_account
from streamlit.errors import StreamlitSecretNotFoundError


PROJECT_ID = "encoded-joy-485413-k5"

_env = os.getenv("BRUIN_ENVIRONMENT")

# safer fallback
if _env is None:
    _env = "dev"

DATASET = "reporting" if _env == "prod" else "marts"


ALLOWED_TABLES = {
    "civil_liberties_mart",
    "platform_censorship_mart",
}


# ─────────────────────────────────────────────
# CLIENT
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

    except StreamlitSecretNotFoundError:
        pass

    return bigquery.Client(project=PROJECT_ID)


# ─────────────────────────────────────────────
# TABLE SAFETY
# ─────────────────────────────────────────────

def table(name: str) -> str:
    if name not in ALLOWED_TABLES:
        raise ValueError(f"Table {name} is not allowed.")
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


# ─────────────────────────────────────────────
# QUERY SAFETY
# ─────────────────────────────────────────────

def ensure_limit(sql: str, limit: int = 1000) -> str:
    clean = sql.strip().rstrip(";")
    if " limit " in clean.lower():
        return clean
    return f"{clean}\nLIMIT {limit}"


def sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame()

    df = df.copy()

    # normalize column names
    df.columns = [c.lower() for c in df.columns]

    # safe date parsing
    for col in df.columns:
        if "date" in col:
            try:
                df[col] = pd.to_datetime(df[col], errors="ignore")
            except Exception:
                pass

    return df


def safe_metric(val):
    if val is None:
        return "—"
    try:
        if pd.isna(val):
            return "—"
    except Exception:
        pass
    return val


# ─────────────────────────────────────────────
# CORE QUERY ENGINE
# ─────────────────────────────────────────────

@st.cache_data(ttl=1800, show_spinner=False)
def run_query(
    sql: str,
    params: Optional[List] = None,
    limit_fallback: int = 1000,
) -> pd.DataFrame:

    client = get_client()

    sql = ensure_limit(sql, limit_fallback)

    job_config = bigquery.QueryJobConfig(
        query_parameters=params or []
    )

    df = client.query(sql, job_config=job_config).to_dataframe()

    return sanitize_df(df)


# ─────────────────────────────────────────────
# MART HELPERS
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

    platform_filter = ""
    params = [
        ScalarQueryParameter("start_date", "DATE", start_date),
        ScalarQueryParameter("end_date", "DATE", end_date),
    ]

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
# UI CONSTANTS
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
