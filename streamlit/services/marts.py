# streamlit/services/marts.py

from __future__ import annotations

import streamlit as st

from core.constants import MARTS, REPORTING
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
            legal_pressure_is_synthetic,
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
            "legal_pressure_is_synthetic",
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
            "legal_pressure_is_synthetic": "any",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "date_key",
            "composite_pressure_score",
            "legal_pressure_is_synthetic",
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
            state_driving_family,
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
            "state_driving_family",
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
            "state_driving_family": "string",
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
            c.legal_pressure_is_synthetic,
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
            "legal_pressure_is_synthetic",
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
            "legal_pressure_is_synthetic": "any",
            "protocol_state": "string",
            "regime_confidence": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "protocol",
            "legal_pressure_is_synthetic",
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
            legal_pressure_is_synthetic,
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
            "legal_pressure_is_synthetic",
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
            "legal_pressure_is_synthetic": "any",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "protocol",
            "legal_pressure_is_synthetic",
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


@st.cache_data(ttl=3600)
def get_protocol_blocking_summary(start_date, end_date):
    """marts.fact_protocol_blocking_summary (TD-51): the one asset in the
    pipeline where per-app (test_name) attribution survives uncoarsened,
    alongside protocol layer, at monthly grain. Has no reporting_version /
    intelligence_version (it's a marts.facts table, not a reporting mart) --
    callers should pass its own extracted_at to render_trust_strip instead.
    """
    sql = f"""
        SELECT
            month_date,
            test_name,
            protocol,
            total_experiment_results,
            blocking_signal_count,
            dns_blocking_events,
            tcp_blocking_events,
            tls_blocking_events,
            http_blocking_events,
            high_confidence_events,
            medium_confidence_events,
            low_confidence_events,
            blocking_signal_rate,
            protocol_interference_intensity,
            extracted_at
        FROM `{MARTS}.fact_protocol_blocking_summary`
        WHERE month_date BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY month_date, test_name, protocol
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "month_date",
            "test_name",
            "protocol",
            "total_experiment_results",
            "blocking_signal_count",
            "dns_blocking_events",
            "tcp_blocking_events",
            "tls_blocking_events",
            "http_blocking_events",
            "high_confidence_events",
            "medium_confidence_events",
            "low_confidence_events",
            "blocking_signal_rate",
            "protocol_interference_intensity",
            "extracted_at",
        ],
        dtype_hints={
            "month_date": "datetime",
            "test_name": "string",
            "protocol": "string",
            "total_experiment_results": "numeric",
            "blocking_signal_count": "numeric",
            "dns_blocking_events": "numeric",
            "tcp_blocking_events": "numeric",
            "tls_blocking_events": "numeric",
            "http_blocking_events": "numeric",
            "high_confidence_events": "numeric",
            "medium_confidence_events": "numeric",
            "low_confidence_events": "numeric",
            "blocking_signal_rate": "numeric",
            "protocol_interference_intensity": "numeric",
            "extracted_at": "datetime",
        },
        non_nullable=[
            "month_date",
            "test_name",
            "protocol",
            "extracted_at",
        ],
        title="get_protocol_blocking_summary",
    )


@st.cache_data(ttl=3600)
def get_pressure_attribution_daily(start_date, end_date):
    """reporting.mart_pressure_attribution_daily (ADR-0006): the arithmetic
    decomposition of composite_pressure_score into its only two real terms
    (conflict 0.75 / platform 0.25, per ADR-0004), with per-term grain
    markers and evidence-pointer join keys. OONI is deliberately absent
    here -- it is not a composite input; see get_ooni_corroboration.
    """
    sql = f"""
        SELECT
            measurement_date,
            composite_pressure_score,
            pressure_level,
            conflict_pressure_score,
            conflict_weight,
            conflict_contribution,
            conflict_share,
            conflict_events,
            fatalities,
            conflict_week_start_date,
            conflict_data_grain,
            platform_pressure_score,
            platform_weight,
            platform_contribution,
            platform_share,
            google_requests,
            detailed_total,
            platform_period_start,
            platform_period_end,
            platform_data_grain,
            legal_pressure_score,
            legal_pressure_is_synthetic,
            regime_primary_regime,
            regime_confidence_level,
            regime_transition_detected,
            regime_transition_type,
            regime_protest_band,
            regime_violence_band,
            regime_suppression_band,
            regime_disorder_band,
            attribution_residual,
            composite_delta_7d,
            conflict_contribution_delta_7d,
            platform_contribution_delta_7d,
            attribution_methodology_version,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.mart_pressure_attribution_daily`
        WHERE measurement_date BETWEEN DATE('{start_date}')
        AND DATE('{end_date}')
        ORDER BY measurement_date
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "measurement_date",
            "composite_pressure_score",
            "pressure_level",
            "conflict_pressure_score",
            "conflict_weight",
            "conflict_contribution",
            "conflict_share",
            "conflict_events",
            "fatalities",
            "conflict_week_start_date",
            "conflict_data_grain",
            "platform_pressure_score",
            "platform_weight",
            "platform_contribution",
            "platform_share",
            "google_requests",
            "detailed_total",
            "platform_period_start",
            "platform_period_end",
            "platform_data_grain",
            "legal_pressure_score",
            "legal_pressure_is_synthetic",
            "regime_primary_regime",
            "regime_confidence_level",
            "attribution_residual",
            "composite_delta_7d",
            "conflict_contribution_delta_7d",
            "platform_contribution_delta_7d",
            "attribution_methodology_version",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "measurement_date": "datetime",
            "composite_pressure_score": "numeric",
            "pressure_level": "string",
            "conflict_pressure_score": "numeric",
            "conflict_weight": "numeric",
            "conflict_contribution": "numeric",
            "conflict_share": "numeric",
            "conflict_events": "numeric",
            "fatalities": "numeric",
            "conflict_week_start_date": "datetime",
            "conflict_data_grain": "string",
            "platform_pressure_score": "numeric",
            "platform_weight": "numeric",
            "platform_contribution": "numeric",
            "platform_share": "numeric",
            "google_requests": "numeric",
            "detailed_total": "numeric",
            "platform_data_grain": "string",
            "legal_pressure_score": "numeric",
            "legal_pressure_is_synthetic": "any",
            "regime_primary_regime": "string",
            "regime_confidence_level": "string",
            "attribution_residual": "numeric",
            "composite_delta_7d": "numeric",
            "conflict_contribution_delta_7d": "numeric",
            "platform_contribution_delta_7d": "numeric",
            "attribution_methodology_version": "string",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "composite_pressure_score",
            "pressure_level",
            "conflict_contribution",
            "platform_contribution",
            "conflict_week_start_date",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_pressure_attribution_daily",
    )


@st.cache_data(ttl=3600)
def get_conflict_drivers(week_start_date):
    """reporting.mart_pressure_attribution_conflict_drivers (ADR-0006):
    the classified ACLED rows behind one week's conflict pressure input,
    at ACLED's own weekly-aggregate grain. weekly_intensity_share is a
    share of the week's pre-log intensity mass (events + 3*fatalities),
    never of the log-scale score itself.
    """
    sql = f"""
        SELECT
            week_start_date,
            weekly_intensity_rank,
            event_type,
            sub_event_type,
            disorder_type,
            admin1,
            events,
            fatalities,
            intensity_mass,
            weekly_intensity_share,
            week_intensity_mass,
            week_conflict_events,
            week_fatalities,
            pressure_domain,
            is_suppression_marker,
            is_civic_response,
            severity_tier,
            classification_confidence,
            is_ambiguous_event,
            methodology_risk_level,
            classification_note,
            low_event_density,
            population_exposure_missing,
            acled_source_id,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.mart_pressure_attribution_conflict_drivers`
        WHERE week_start_date = DATE('{week_start_date}')
        ORDER BY weekly_intensity_rank
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "week_start_date",
            "weekly_intensity_rank",
            "event_type",
            "sub_event_type",
            "admin1",
            "events",
            "fatalities",
            "intensity_mass",
            "weekly_intensity_share",
            "week_intensity_mass",
            "week_conflict_events",
            "week_fatalities",
            "pressure_domain",
            "is_suppression_marker",
            "severity_tier",
            "classification_confidence",
            "methodology_risk_level",
            "classification_note",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "week_start_date": "datetime",
            "weekly_intensity_rank": "numeric",
            "event_type": "string",
            "sub_event_type": "string",
            "admin1": "string",
            "events": "numeric",
            "fatalities": "numeric",
            "intensity_mass": "numeric",
            "weekly_intensity_share": "numeric",
            "week_intensity_mass": "numeric",
            "week_conflict_events": "numeric",
            "week_fatalities": "numeric",
            "pressure_domain": "string",
            "is_suppression_marker": "any",
            "severity_tier": "string",
            "classification_confidence": "string",
            "methodology_risk_level": "string",
            "classification_note": "string",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "week_start_date",
            "weekly_intensity_rank",
            "event_type",
            "events",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_conflict_drivers",
    )


@st.cache_data(ttl=3600)
def get_platform_drivers(period_start):
    """reporting.mart_pressure_attribution_platform_drivers (ADR-0006):
    Google Transparency product x reason breakdown for one semiannual
    period. Grain honesty: this evidence contextualizes a ~6-month
    period, never a specific day or week.
    """
    sql = f"""
        SELECT
            period_start,
            period_end,
            product,
            reason,
            removal_items,
            period_detailed_total,
            period_detailed_share,
            period_share_rank,
            google_requests,
            requested_items,
            legal_removed,
            policy_removed,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.mart_pressure_attribution_platform_drivers`
        WHERE period_start = DATE('{period_start}')
        ORDER BY period_share_rank
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "period_start",
            "period_end",
            "product",
            "reason",
            "removal_items",
            "period_detailed_total",
            "period_detailed_share",
            "period_share_rank",
            "google_requests",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "period_start": "datetime",
            "period_end": "datetime",
            "product": "string",
            "reason": "string",
            "removal_items": "numeric",
            "period_detailed_total": "numeric",
            "period_detailed_share": "numeric",
            "period_share_rank": "numeric",
            "google_requests": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "period_start",
            "product",
            "reason",
            "removal_items",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_platform_drivers",
    )


@st.cache_data(ttl=3600)
def get_ooni_corroboration(measurement_date):
    """reporting.mart_pressure_attribution_ooni_daily (ADR-0006): what
    OONI probes directly observed on one date, per app (test_name) and
    protocol layer. CORROBORATING EVIDENCE ONLY -- OONI does not feed
    composite_pressure_score arithmetically (the composite's platform
    term is Google Transparency data). Per-test rows are never pooled
    (TD-49/TD-54).
    """
    sql = f"""
        SELECT
            measurement_date,
            test_name,
            protocol,
            total_experiment_results,
            blocking_signal_count,
            blocked_results,
            ok_results,
            down_results,
            error_results,
            distinct_asns,
            high_confidence_events,
            medium_confidence_events,
            low_confidence_events,
            blocking_signal_rate,
            reporting_version,
            snapshot_at
        FROM `{REPORTING}.mart_pressure_attribution_ooni_daily`
        WHERE measurement_date = DATE('{measurement_date}')
        ORDER BY blocking_signal_count DESC, test_name, protocol
    """

    df = run_query(sql)
    return _validate_mart_response(
        df,
        required_columns=[
            "measurement_date",
            "test_name",
            "protocol",
            "total_experiment_results",
            "blocking_signal_count",
            "blocked_results",
            "high_confidence_events",
            "medium_confidence_events",
            "low_confidence_events",
            "blocking_signal_rate",
            "reporting_version",
            "snapshot_at",
        ],
        dtype_hints={
            "measurement_date": "datetime",
            "test_name": "string",
            "protocol": "string",
            "total_experiment_results": "numeric",
            "blocking_signal_count": "numeric",
            "blocked_results": "numeric",
            "high_confidence_events": "numeric",
            "medium_confidence_events": "numeric",
            "low_confidence_events": "numeric",
            "blocking_signal_rate": "numeric",
            "reporting_version": "string",
            "snapshot_at": "datetime",
        },
        non_nullable=[
            "measurement_date",
            "test_name",
            "protocol",
            "total_experiment_results",
            "reporting_version",
            "snapshot_at",
        ],
        title="get_ooni_corroboration",
    )
