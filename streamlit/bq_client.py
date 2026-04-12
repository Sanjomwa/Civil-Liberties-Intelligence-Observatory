"""
utils/bq_client.py
Shared BigQuery connection and query helpers used by all dashboard pages.
Reads credentials from Streamlit secrets or environment variable.
"""

import os
import streamlit as st
from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd


PROJECT_ID = "encoded-joy-485413-k5"

# Dataset switches with environment variable fallback
_env = os.getenv("BRUIN_ENVIRONMENT", "staging")
DATASET = "civil_liberties_prod" if _env == "prod" else "civil_liberties_staging"


@st.cache_resource(show_spinner=False)
def get_client() -> bigquery.Client:
    """Return a cached BigQuery client."""
    if "gcp_service_account" in st.secrets:
        creds = service_account.Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        return bigquery.Client(project=PROJECT_ID, credentials=creds)
    # Fall back to ADC (works in Codespace with gcloud auth application-default login)
    return bigquery.Client(project=PROJECT_ID)


@st.cache_data(ttl=3600, show_spinner=False)
def run_query(sql: str) -> pd.DataFrame:
    """Execute a BigQuery SQL string and return a DataFrame. Cached for 1 hour."""
    client = get_client()
    return client.query(sql).to_dataframe()


def table(name: str) -> str:
    """Return a fully qualified BigQuery table path."""
    return f"`{PROJECT_ID}.{DATASET}.{name}`"


# ── Colour palette shared across all pages ──────────────────────────────────
PALETTE = {
    "coral":    "#E8593C",
    "amber":    "#EF9F27",
    "teal":     "#1D9E75",
    "purple":   "#7F77DD",
    "blue":     "#378ADD",
    "gray":     "#888780",
    "bg":       "#0D0D0F",
    "bg2":      "#16161A",
    "text":     "#E8E6DF",
    "muted":    "#6B6966",
}

STATUS_COLORS = {
    "confirmed":    "#E8593C",
    "anomaly":      "#EF9F27",
    "failure":      "#7F77DD",
    "ok":           "#1D9E75",
}

SUPPRESSION_COLORS = {
    "Full Suppression Window":          "#E8593C",
    "Blocking + Protest Day":           "#EF9F27",
    "Blocking + Removal Activity":      "#7F77DD",
    "Blocking Only":                    "#378ADD",
    "No Suppression Signal":            "#1D9E75",
}
