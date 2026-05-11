/* @bruin
tags:
  - reporting

name: reporting.asn_behavior_profile_mart
type: bq.sql
connection: bigquery-default

description: |
  Behavioral observability profile for Kenyan ASNs using normalized
  OONI-derived feature and intelligence distributions.

  Reporting grain matches the existing project mart: one row per ASN.

depends:
  - features.protocol_daily_signals
  - intelligence.protocol_relationships
  - marts.dim_asn

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH protocol_averages AS (

    SELECT
        asn,
        protocol,
        AVG(signal_rate) AS avg_protocol_signal_rate

    FROM `encoded-joy-485413-k5.features.protocol_daily_signals`

    WHERE country = 'KE'

    GROUP BY
        asn,
        protocol
),

dominant_protocol AS (

    SELECT
        asn,
        protocol AS dominant_protocol

    FROM (
        SELECT
            *,
            ROW_NUMBER() OVER (
                PARTITION BY asn
                ORDER BY avg_protocol_signal_rate DESC
            ) AS protocol_rank

        FROM protocol_averages
    )

    WHERE protocol_rank = 1
),

features AS (

    SELECT
        asn,

        COUNT(DISTINCT measurement_date) AS observation_days,
        SUM(measurement_count) AS measurement_count,
        SUM(observation_count) AS observation_count,

        AVG(blocked_rate_observation_weighted)
            AS avg_blocking_rate,

        AVG(confidence_weighted_interference)
            AS avg_weighted_blocking,

        STDDEV(signal_rate)
            AS blocking_variability,

        SUM(blocked_events)
            AS total_blocked_events,

        AVG(sample_quality_score)
            AS avg_sample_quality_score,

        COUNTIF(low_sample_flag) AS low_sample_days,
        COUNTIF(sparse_window_flag) AS sparse_window_days,
        COUNTIF(zero_variance_flag) AS zero_variance_days,

        ANY_VALUE(feature_version) AS feature_version

    FROM `encoded-joy-485413-k5.features.protocol_daily_signals`

    WHERE country = 'KE'

    GROUP BY asn
),

intelligence AS (

    SELECT
        asn,

        COUNTIF(intelligence_state = 'COUPLED_PROTOCOL_ESCALATION')
            AS coupled_escalation_days,

        COUNTIF(intelligence_state = 'ISOLATED_PROTOCOL_ESCALATION')
            AS isolated_escalation_days,

        MAX(final_confidence_score)
            AS max_intelligence_confidence_score,

        ARRAY_AGG(
            STRUCT(
                measurement_date,
                protocol,
                intelligence_state,
                final_confidence_level,
                strongest_driver_protocol,
                strongest_driver_lag_days
            )
            ORDER BY measurement_date DESC
            LIMIT 1
        )[OFFSET(0)] AS latest_intelligence,

        ANY_VALUE(intelligence_version) AS intelligence_version

    FROM `encoded-joy-485413-k5.intelligence.protocol_relationships`

    WHERE country = 'KE'

    GROUP BY asn
),

scaled AS (

    SELECT
        f.*,

        SAFE_DIVIDE(
            avg_weighted_blocking,
            NULLIF(MAX(avg_weighted_blocking) OVER (), 0)
        ) AS normalized_weighted_signal

    FROM features f
)

SELECT
    s.asn,

    d.asn AS display_asn,
    d.network_class,
    d.is_kenya_observability_core,
    d.censorship_sensitivity_score,

    s.observation_days,
    s.measurement_count,
    s.observation_count,

    s.avg_blocking_rate,
    s.avg_weighted_blocking,
    s.normalized_weighted_signal,

    s.blocking_variability,
    s.total_blocked_events,
    s.avg_sample_quality_score,

    s.low_sample_days,
    s.sparse_window_days,
    s.zero_variance_days,

    dp.dominant_protocol,

    COALESCE(i.coupled_escalation_days, 0) AS coupled_escalation_days,
    COALESCE(i.isolated_escalation_days, 0) AS isolated_escalation_days,
    i.max_intelligence_confidence_score,
    i.latest_intelligence.measurement_date AS latest_intelligence_date,
    i.latest_intelligence.protocol AS latest_protocol,
    i.latest_intelligence.intelligence_state AS latest_intelligence_state,
    i.latest_intelligence.final_confidence_level AS latest_confidence_level,
    i.latest_intelligence.strongest_driver_protocol,
    i.latest_intelligence.strongest_driver_lag_days,

    ROUND(
        (
            COALESCE(s.normalized_weighted_signal, 0)
            * LOG(1 + COALESCE(s.total_blocked_events, 0))
            * COALESCE(d.censorship_sensitivity_score, 0.50)
            * (1 + COALESCE(i.coupled_escalation_days, 0) * 0.02)
        ),
        4
    ) AS anomaly_score,

    CASE
        WHEN normalized_weighted_signal >= 0.75
            THEN 'HIGH_SIGNAL_PROVIDER'

        WHEN normalized_weighted_signal >= 0.45
            THEN 'ELEVATED_SIGNAL_PROVIDER'

        WHEN normalized_weighted_signal >= 0.20
            THEN 'VARIABLE_BEHAVIOR'

        ELSE 'STABLE'
    END AS behavioral_class,

    'asn_behavior_profile_mart_v2' AS reporting_version,
    s.feature_version,
    i.intelligence_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM scaled s

LEFT JOIN `encoded-joy-485413-k5.marts.dim_asn` d
    ON CAST(s.asn AS STRING) = CAST(d.asn_numeric AS STRING)

LEFT JOIN dominant_protocol dp
    USING (asn)

LEFT JOIN intelligence i
    USING (asn)

ORDER BY anomaly_score DESC
