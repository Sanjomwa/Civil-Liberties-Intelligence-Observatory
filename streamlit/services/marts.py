# streamlit/services/marts.py

import streamlit as st
from services.bq import run_query


PROJECT = "encoded-joy-485413-k5"
REPORTING = f"{PROJECT}.reporting"


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
        FROM `{REPORTING}.mart_political_stress_windows`
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
        FROM `{REPORTING}.mart_protocol_interference_trends`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key, protocol
    """

    return run_query(sql)


# ============================================================
# PAGE 3
# PROTOCOL STRESS INTELLIGENCE OBSERVATORY
# ============================================================

@st.cache_data(ttl=3600)
def get_protocol_stress_intelligence(start_date, end_date):

    return get_protocol_regimes(start_date, end_date)


# ============================================================
# PAGE 4
# PROTOCOL ↔ REPRESSION CORRELATION ENGINE
# ============================================================

@st.cache_data(ttl=3600)
def get_protocol_correlation(start_date, end_date):

    sql = f"""
        SELECT
            measurement_date,
            protocol,

            rolling_pressure_corr,
            raw_corr,
            synchronized_stress,
            stress_divergence,

            protocol_stress_score,
            protocol_state,

            final_confidence_score,
            final_confidence_level,

            correlation_state,
            alignment_state,
            divergence_state,

            pressure_level,
            composite_pressure_score,

            reporting_version,
            intelligence_version,
            snapshot_at

        FROM `{REPORTING}.protocol_repression_correlation_mart`

        WHERE measurement_date BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')

        ORDER BY measurement_date, protocol
    """

    return run_query(sql)


# ============================================================
# PAGE 5
# ASN BEHAVIORAL INTELLIGENCE
# ============================================================

@st.cache_data(ttl=3600)
def get_asn_behavior(start_date, end_date):

    sql = f"""
        SELECT *
        FROM `{REPORTING}.asn_behavior_profile_mart`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key
    """

    return run_query(sql)
