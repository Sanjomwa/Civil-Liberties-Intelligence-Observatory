# streamlit/services/marts.py

import streamlit as st
from services.bq import run_query


# ============================================================
# PAGE 1
# NATIONAL STRESS OBSERVATORY
# ============================================================

@st.cache_data(ttl=3600)
def get_national_stress(start_date, end_date):

    sql = f"""
        SELECT
            date_key,
            composite_pressure_score,
            rolling_baseline_pressure,
            pressure_delta,
            suppression_window_probability,
            suppression_window_class,
            elevated_protocol_count,
            avg_sample_quality_score,
            baseline_days_30d,
            reporting_version,
            snapshot_at
        FROM
        `encoded-joy-485413-k5.reporting.mart_political_stress_windows`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key
    """

    return run_query(sql)


# ============================================================
# PAGE 2
# PROTOCOL REGIME MONITOR
# ============================================================

@st.cache_data(ttl=3600)
def get_protocol_regimes(start_date, end_date):

    sql = f"""
        SELECT
            date_key,
            protocol,
            protocol_stress_score,
            protocol_state,
            trend_state,
            anomaly_score,
            confidence_level,
            regime_confidence,
            severe_obs_share,
            elevated_obs_share,
            insufficient_obs_share,
            sample_quality_score,
            reporting_version,
            feature_version,
            intelligence_version,
            snapshot_at
        FROM
        `encoded-joy-485413-k5.reporting.mart_protocol_interference_trends`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key, protocol
    """

    return run_query(sql)


# ============================================================
# PAGE 3
# PROTOCOL STRESS INTELLIGENCE
# ============================================================

@st.cache_data(ttl=3600)
def get_protocol_correlation(start_date, end_date):

    sql = f"""
        SELECT
            date_key,
            protocol,
            protocol_stress_score,
            protocol_state,
            confidence_level,
            regime_confidence,
            severe_obs_share,
            elevated_obs_share,
            insufficient_obs_share,
            reporting_version,
            feature_version,
            intelligence_version,
            snapshot_at
        FROM
        `encoded-joy-485413-k5.reporting.mart_protocol_interference_trends`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key, protocol
    """

    return run_query(sql)
