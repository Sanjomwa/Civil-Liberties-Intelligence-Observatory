/* @bruin
tags:
  - reporting

name: reporting.protocol_repression_correlation_mart
type: bq.sql
connection: bigquery-default

description: |
  Measures statistical relationship between protocol-level censorship
  anomalies and country-level repression pressure.

  Protocol metrics come from the new features/intelligence-backed reporting
  mart. Pressure still comes from the existing country pressure fact until a
  dedicated pressure feature layer is introduced.

depends:
  - reporting.mart_protocol_interference_trends
  - intelligence.protocol_relationships
  - marts.fact_country_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH pressure_windowed AS (

    SELECT
        measurement_date,

        conflict_pressure_score,
        legal_pressure_score,
        platform_pressure_score,
        composite_pressure_score,
        pressure_level,

        SAFE_DIVIDE(
            composite_pressure_score
            - AVG(composite_pressure_score) OVER (),
            NULLIF(STDDEV_SAMP(composite_pressure_score) OVER (), 0)
        ) AS z_pressure

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`

    WHERE iso2 = 'KE'
),

pressure_variance AS (

    SELECT
        *,

        STDDEV_SAMP(z_pressure)
        OVER (
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS pressure_window_stddev

    FROM pressure_windowed
),

protocol_relationships AS (

    SELECT
        measurement_date,
        protocol,

        MAX(protocol_stress_score)
            AS protocol_stress_score,

        ANY_VALUE(intelligence_state)
            AS intelligence_state,

        MAX(final_confidence_score)
            AS final_confidence_score,

        ANY_VALUE(final_confidence_level)
            AS final_confidence_level,

        ANY_VALUE(strongest_driver_protocol)
            AS strongest_driver_protocol,

        ANY_VALUE(strongest_driver_lag_days)
            AS strongest_driver_lag_days,

        ANY_VALUE(strongest_relationship_state)
            AS strongest_relationship_state,

        ANY_VALUE(intelligence_version)
            AS intelligence_version

    FROM `encoded-joy-485413-k5.intelligence.protocol_relationships`

    WHERE country = 'KE'

    GROUP BY
        measurement_date,
        protocol
),

joined AS (

    SELECT
        p.date_key AS measurement_date,
        p.protocol,

        p.measurement_volume,
        p.observation_volume,
        p.signal_rate,
        p.confidence_weighted_interference,

        p.anomaly_score,
        p.anomaly_delta,
        p.sample_quality_score,
        p.trend_state,

        pr.protocol_stress_score,
        pr.intelligence_state,
        pr.final_confidence_score,
        pr.final_confidence_level,
        pr.strongest_driver_protocol,
        pr.strongest_driver_lag_days,
        pr.strongest_relationship_state,
        pr.intelligence_version,

        pv.conflict_pressure_score,
        pv.legal_pressure_score,
        pv.platform_pressure_score,
        pv.composite_pressure_score,
        pv.pressure_level,

        pv.z_pressure,
        pv.pressure_window_stddev

    FROM `encoded-joy-485413-k5.reporting.mart_protocol_interference_trends` p

    LEFT JOIN pressure_variance pv
        ON p.date_key = pv.measurement_date

    LEFT JOIN protocol_relationships pr
        ON p.date_key = pr.measurement_date
        AND p.protocol = pr.protocol

    WHERE p.protocol IS NOT NULL
),

normalized AS (

    SELECT
        *,

        SAFE_DIVIDE(
            anomaly_score
            - AVG(anomaly_score)
              OVER (PARTITION BY protocol),

            NULLIF(
                STDDEV_SAMP(anomaly_score)
                OVER (PARTITION BY protocol),
                0
            )
        ) AS z_anomaly

    FROM joined
),

correlated AS (

    SELECT
        *,

        COUNT(*)
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS window_obs,

        STDDEV_SAMP(z_anomaly)
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS anomaly_window_stddev,

        CORR(
            z_anomaly,
            z_pressure
        ) OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS raw_rolling_pressure_corr

    FROM normalized
),

guarded AS (

    SELECT
        *,

        CASE
            WHEN window_obs < 14 THEN NULL
            WHEN COALESCE(anomaly_window_stddev, 0) = 0 THEN NULL
            WHEN COALESCE(pressure_window_stddev, 0) = 0 THEN NULL
            ELSE raw_rolling_pressure_corr
        END AS rolling_pressure_corr,

        window_obs < 14 AS insufficient_history_flag,
        COALESCE(anomaly_window_stddev, 0) = 0
            OR COALESCE(pressure_window_stddev, 0) = 0
            AS zero_variance_flag

    FROM correlated
),

synchronized AS (

    SELECT
        *,

        AVG(ABS(rolling_pressure_corr))
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
        ) AS synchronized_stress

    FROM guarded
),

finalized AS (

    SELECT
        *,

        ABS(z_anomaly - z_pressure) AS stress_divergence

    FROM synchronized
)

SELECT
    measurement_date,
    protocol,

    measurement_volume,
    observation_volume,
    signal_rate,
    confidence_weighted_interference,

    anomaly_score,
    anomaly_delta,
    sample_quality_score,
    trend_state,

    conflict_pressure_score,
    legal_pressure_score,
    platform_pressure_score,
    composite_pressure_score,

    raw_rolling_pressure_corr,
    rolling_pressure_corr,
    synchronized_stress,
    stress_divergence,

    protocol_stress_score,
    intelligence_state,
    final_confidence_score,
    final_confidence_level,
    strongest_driver_protocol,
    strongest_driver_lag_days,
    strongest_relationship_state,

    CASE
        WHEN trend_state IN ('CRITICAL_PROTOCOL_SHIFT', 'HIGH_PROTOCOL_ANOMALY')
            THEN 'ELEVATED'
        WHEN trend_state = 'INSUFFICIENT_DATA'
            THEN 'INSUFFICIENT_DATA'
        ELSE 'NORMAL'
    END AS protocol_state,

    pressure_level,

    CASE
        WHEN insufficient_history_flag
            THEN 'INSUFFICIENT_HISTORY'

        WHEN zero_variance_flag
            THEN 'ZERO_VARIANCE_WINDOW'

        WHEN ABS(rolling_pressure_corr) >= 0.70
            THEN 'STRONG_RELATIONSHIP'

        WHEN ABS(rolling_pressure_corr) >= 0.40
            THEN 'MODERATE_RELATIONSHIP'

        ELSE 'WEAK_OR_NO_RELATIONSHIP'
    END AS correlation_state,

    CASE
        WHEN rolling_pressure_corr >= 0.40
            AND z_anomaly > 0
            AND z_pressure > 0
            THEN 'SYNCHRONIZED_ESCALATION'

        WHEN rolling_pressure_corr <= -0.40
            THEN 'INVERSE_MOVEMENT'

        WHEN z_anomaly > 0
            AND z_pressure <= 0
            THEN 'PROTOCOL_DIVERGENCE'

        WHEN z_pressure > 0
            AND z_anomaly <= 0
            THEN 'PRESSURE_ONLY'

        ELSE 'NO_CLEAR_ALIGNMENT'
    END AS alignment_state,

    CASE
        WHEN stress_divergence >= 2.0 THEN 'HIGH_DIVERGENCE'
        WHEN stress_divergence >= 1.0 THEN 'MODERATE_DIVERGENCE'
        ELSE 'LOW_DIVERGENCE'
    END AS divergence_state,

    insufficient_history_flag,
    zero_variance_flag,
    'PRESSURE_FACT_V1' AS pressure_context_status,
    'protocol_repression_correlation_mart_v2' AS reporting_version,
    intelligence_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM finalized

ORDER BY
    measurement_date,
    protocol
