# services/bq.py

"""
Centralized BigQuery client + cached query execution
"""

import streamlit as st
import pandas as pd

from google.cloud import bigquery

from core.constants import PROJECT_ID


# ============================================================
# CLIENT
# ============================================================

@st.cache_resource
def get_client():
    return bigquery.Client(project=PROJECT_ID)


# ============================================================
# QUERY EXECUTION
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def run_query(query: str) -> pd.DataFrame:

    client = get_client()

    return client.query(query).to_dataframe()
