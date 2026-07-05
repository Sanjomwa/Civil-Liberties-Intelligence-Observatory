# streamlit/services/marts.py

from __future__ import annotations

import streamlit as st

from core.constants import REPORTING
from core.contracts import guard_dataframe_schema
from services.bq import run_query


def _validate_mart_response(
    df,
    required_columns,
    dtype_hints=None,
    non_nullable=None,
    title="mart query",
):
    return guard_dataframe_schema(
        df,
        required_columns=required_columns,
        dtype_hints=dtype_hints,
        non_nullable=non_nullable,
        title=title,
    )


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

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "date_key",
            "composite_pressure_score",
            "rolling_baseline_pressure",
            "pressure_delta",
            "suppression_window_probability",
            "suppression_window_class",
            "elevated_protocol_count",
            "avg_sample_quality_score",
            "baseline_days_30d",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "date_key": "datetime",
            "composite_pressure_score": "numeric",
            "rolling_baseline_pressure": "numeric",
            "pressure_delta": "numeric",
            "suppression_window_probability": "numeric",
            "suppression_window_class": "string",
            "elevated_protocol_count": "numeric",
            "avg_sample_quality_score": "numeric",
            "baseline_days_30d": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "date_key",
            "composite_pressure_score",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_national_stress",
    )


@st.cache_data(ttl=3600)
def get_regime_classification(start_date, end_date):
    """ACLED path A (intelligence.acled_pressure_regimes) classification,
    surfaced additively via mart_political_stress_windows (ADR-0002 step (e)).
    Weekly-grain values repeat across each day of their week; regime_*
    columns are nullable where no classification exists for that date.
    """
    sql = f"""
        SELECT
            date_key,
            regime_primary_regime,
            regime_confidence_level,
            regime_transition_detected,
            regime_transition_type,
            regime_previous_regime,
            regime_protest_band,
            regime_violence_band,
            regime_suppression_band,
            regime_disorder_band,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.mart_political_stress_windows`
        WHERE date_key BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY date_key
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "date_key",
            "regime_primary_regime",
            "regime_confidence_level",
            "regime_transition_detected",
            "regime_transition_type",
            "regime_previous_regime",
            "regime_protest_band",
            "regime_violence_band",
            "regime_suppression_band",
            "regime_disorder_band",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "date_key": "datetime",
            "regime_primary_regime": "string",
            "regime_confidence_level": "string",
            "regime_transition_detected": "any",
            "regime_transition_type": "string",
            "regime_previous_regime": "string",
            "regime_protest_band": "string",
            "regime_violence_band": "string",
            "regime_suppression_band": "string",
            "regime_disorder_band": "string",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "date_key",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_regime_classification",
    )


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

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "date_key",
            "protocol",
            "protocol_stress_score",
            "protocol_state",
            "trend_state",
            "anomaly_score",
            "confidence_level",
            "regime_confidence",
            "severe_obs_share",
            "elevated_obs_share",
            "insufficient_obs_share",
            "sample_quality_score",
            "reporting_version",
            "feature_version",
            "intelligence_version",
            "snapshot_at",
        ],
        dtype_hints={
            "date_key": "datetime",
            "protocol": "string",
            "protocol_stress_score": "numeric",
            "protocol_state": "string",
            "trend_state": "string",
            "anomaly_score": "numeric",
            "confidence_level": "string",
            "regime_confidence": "numeric",
            "severe_obs_share": "numeric",
            "elevated_obs_share": "numeric",
            "insufficient_obs_share": "numeric",
            "sample_quality_score": "numeric",
            "reporting_version": "string",
            "feature_version": "string",
            "intelligence_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "date_key",
            "protocol",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_protocol_regimes",
    )


@st.cache_data(ttl=3600)
def get_protocol_stress_intelligence(start_date, end_date):
    return get_protocol_regimes(start_date, end_date)


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

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "measurement_date",
            "protocol",
            "rolling_pressure_corr",
            "raw_corr",
            "synchronized_stress",
            "stress_divergence",
            "protocol_stress_score",
            "protocol_state",
            "final_confidence_score",
            "final_confidence_level",
            "correlation_state",
            "alignment_state",
            "divergence_state",
            "pressure_level",
            "composite_pressure_score",
            "reporting_version",
            "intelligence_version",
            "snapshot_at",
        ],
        dtype_hints={
            "measurement_date": "datetime",
            "protocol": "string",
            "rolling_pressure_corr": "numeric",
            "raw_corr": "numeric",
            "synchronized_stress": "numeric",
            "stress_divergence": "numeric",
            "protocol_stress_score": "numeric",
            "protocol_state": "string",
            "final_confidence_score": "numeric",
            "final_confidence_level": "string",
            "correlation_state": "string",
            "alignment_state": "string",
            "divergence_state": "string",
            "pressure_level": "string",
            "composite_pressure_score": "numeric",
            "reporting_version": "string",
            "intelligence_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "protocol",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_protocol_correlation",
    )


@st.cache_data(ttl=3600)
def get_asn_behavior():
    sql = f"""
        SELECT
            CAST(asn AS STRING) AS asn,
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

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "asn",
            "display_asn",
            "network_class",
            "dominant_protocol",
            "behavioral_priority_score",
            "behavioral_class",
            "censorship_intensity_tier",
            "maturity_adjusted_signal",
            "data_reliability_score",
            "avg_weighted_blocking",
            "coverage_ratio",
            "coupled_escalation_days",
            "isolated_escalation_days",
            "latest_protocol",
            "latest_intelligence_state",
            "latest_confidence_level",
            "summary_insight",
            "reporting_version",
            "intelligence_version",
            "snapshot_at",
        ],
        dtype_hints={
            "asn": "string",
            "display_asn": "string",
            "network_class": "string",
            "dominant_protocol": "string",
            "behavioral_priority_score": "numeric",
            "behavioral_class": "string",
            "censorship_intensity_tier": "string",
            "maturity_adjusted_signal": "numeric",
            "data_reliability_score": "numeric",
            "avg_weighted_blocking": "numeric",
            "coverage_ratio": "numeric",
            "coupled_escalation_days": "numeric",
            "isolated_escalation_days": "numeric",
            "latest_protocol": "string",
            "latest_intelligence_state": "string",
            "latest_confidence_level": "string",
            "summary_insight": "string",
            "reporting_version": "string",
            "intelligence_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "asn",
            "display_asn",
            "network_class",
            "behavioral_priority_score",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_asn_behavior",
    )


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

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "measurement_date",
            "protocol",
            "rolling_pressure_corr",
            "alignment_state",
            "correlation_state",
            "divergence_state",
            "protocol_stress_score",
            "composite_pressure_score",
            "pressure_level",
            "protocol_state",
            "regime_confidence",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "measurement_date": "datetime",
            "protocol": "string",
            "rolling_pressure_corr": "numeric",
            "alignment_state": "string",
            "correlation_state": "string",
            "divergence_state": "string",
            "protocol_stress_score": "numeric",
            "composite_pressure_score": "numeric",
            "pressure_level": "string",
            "protocol_state": "string",
            "regime_confidence": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "protocol",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_event_explorer",
    )


@st.cache_data(ttl=3600)
def get_finance_bill_incident():
    """
    Returns (correlation_df, asn_df).

    TD-02: protocol_repression_correlation_mart (real measurement_date x
    protocol grain) and asn_behavior_profile_mart (one row per ASN,
    full-history snapshot, no date dimension at all) do not share a join
    key -- the mart has nothing to join a specific date/protocol row to.
    The former CROSS JOIN fabricated one, silently multiplying every
    correlation row once per qualifying ASN (3x at last count). Returned
    as two separate, ungrouped dataframes instead of one fabricated join.
    """
    correlation_sql = f"""
        SELECT
            measurement_date,
            protocol,
            rolling_pressure_corr,
            alignment_state,
            correlation_state,
            divergence_state,
            protocol_stress_score,
            composite_pressure_score,
            pressure_level,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.protocol_repression_correlation_mart`
        WHERE measurement_date BETWEEN
            DATE('2024-06-15')
            AND DATE('2024-07-15')
        ORDER BY measurement_date, protocol
    """

    correlation_df = _validate_mart_response(
        run_query(correlation_sql),
        required_columns=[
            "measurement_date",
            "protocol",
            "rolling_pressure_corr",
            "alignment_state",
            "correlation_state",
            "divergence_state",
            "protocol_stress_score",
            "composite_pressure_score",
            "pressure_level",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "measurement_date": "datetime",
            "protocol": "string",
            "rolling_pressure_corr": "numeric",
            "alignment_state": "string",
            "correlation_state": "string",
            "divergence_state": "string",
            "protocol_stress_score": "numeric",
            "composite_pressure_score": "numeric",
            "pressure_level": "string",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "protocol",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_finance_bill_incident.correlation",
    )

    # asn_behavior_profile_mart has no date dimension (TD-28, confirmed
    # during TD-02's investigation) -- no WHERE on measurement_date is
    # possible or appropriate here, only its own network_class filter.
    asn_sql = f"""
        SELECT
            display_asn,
            network_class,
            behavioral_priority_score,
            avg_weighted_blocking,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.asn_behavior_profile_mart`
        WHERE network_class = 'MAJOR_KENYA_PROVIDER'
        ORDER BY behavioral_priority_score DESC
    """

    asn_df = _validate_mart_response(
        run_query(asn_sql),
        required_columns=[
            "display_asn",
            "network_class",
            "behavioral_priority_score",
            "avg_weighted_blocking",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "display_asn": "string",
            "network_class": "string",
            "behavioral_priority_score": "numeric",
            "avg_weighted_blocking": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "display_asn",
            "network_class",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_finance_bill_incident.asn",
    )

    return correlation_df, asn_df
