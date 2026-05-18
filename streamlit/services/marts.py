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
def get_asn_behavior():

    sql = f"""
        SELECT
            asn,
            display_asn,
            network_class,
            dominant_protocol,

            behavioral_priority_score,
            behavioral_class,
            censorship_intensity_tier,

            maturity_adjusted_signal,
            data_reliability_score,
            avg_weighted_blocking,
            coverage_ratio,

            coupled_escalation_days,
            isolated_escalation_days,

            latest_protocol,
            latest_intelligence_state,
            latest_confidence_level,

            summary_insight,

            reporting_version,
            intelligence_version,
            snapshot_at

        FROM `{REPORTING}.asn_behavior_profile_mart`

        ORDER BY behavioral_priority_score DESC
    """

    return run_query(sql)

# ============================================================
# PAGE 6
# SUPPRESSION EVENT EXPLORER
# ============================================================


@st.cache_data(ttl=3600)
def get_event_explorer(start_date, end_date):

    sql = f"""
        SELECT
            c.measurement_date,
            c.protocol,
            c.rolling_pressure_corr,
            c.alignment_state,
            c.correlation_state,
            c.divergence_state,
            c.protocol_stress_score,
            c.composite_pressure_score,
            c.pressure_level,

            p.protocol_state,
            p.regime_confidence,

            c.reporting_version,
            c.snapshot_at

        FROM `{REPORTING}.protocol_repression_correlation_mart` c

        LEFT JOIN `{REPORTING}.mart_protocol_interference_trends` p
            ON c.measurement_date = p.date_key
            AND c.protocol = p.protocol

        WHERE c.measurement_date BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')

        ORDER BY c.measurement_date, c.protocol
    """

    return run_query(sql)

# ============================================================
# PAGE 7
# FINANCE BILL 2024 INCIDENT REPORT
# ============================================================


@st.cache_data(ttl=3600)
def get_finance_bill_incident():

    sql = f"""
        SELECT
            c.measurement_date,
            c.protocol,
            c.rolling_pressure_corr,
            c.alignment_state,
            c.correlation_state,
            c.divergence_state,
            c.protocol_stress_score,
            c.composite_pressure_score,
            c.pressure_level,

            a.display_asn,
            a.network_class,
            a.behavioral_priority_score,
            a.avg_weighted_blocking,

            c.reporting_version,
            c.snapshot_at

        FROM `{REPORTING}.protocol_repression_correlation_mart` c

        LEFT JOIN `{REPORTING}.asn_behavior_profile_mart` a
            ON TRUE

        WHERE c.measurement_date BETWEEN
            DATE('2024-06-15')
            AND DATE('2024-07-15')

        AND a.network_class = 'MAJOR_KENYA_PROVIDER'

        ORDER BY c.measurement_date, c.protocol
    """

    return run_query(sql)
