/* @bruin
tags:
  - reporting

name: reporting.protocol_repression_correlation_mart
type: bq.sql
connection: bigquery-default

description: |
  Measures statistically validated relationship between protocol-level
  censorship anomalies and country-level repression pressure.

  v3 recalibrates correlation confidence weighting and suppresses synthetic
  variance amplification from low-confidence protocol windows.

  ADR-0004 / TD-44 / TD-45 (2026-07-05, v4): composite_pressure_score (read
  from marts.fact_country_pressure_daily) no longer includes a Lumen
  legal-pressure term -- see that asset's header. Because z_pressure below
  is a global, unpartitioned AVG/STDDEV_SAMP OVER () normalization against
  composite_pressure_score, this shifts the mean/stddev basis for every
  row in this mart's full history, not just rows where legal_pressure_score
  was previously nonzero -- verified via a live before/after query against
  correlation_state/alignment_state/divergence_state distributions before
  this version was materialized (see technical-debt-inventory.md TD-44/
  TD-45 and ADR-0004's Consequences section for the actual numbers).
  legal_pressure_score and legal_pressure_is_synthetic are still passed
  through for transparency/provenance only.

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

        -- ADR-0004 / TD-44 / TD-45: passthrough only, as of 2026-07-05 --
        -- legal_pressure_score is no longer a term in
        -- composite_pressure_score (see fact_country_pressure_daily
        -- header), so it is not an input to z_pressure below either.
        legal_pressure_score,
        platform_pressure_score,
        legal_pressure_is_synthetic,
        composite_pressure_score,
        pressure_level,

        -- ADR-0002 step (e): additive ACLED path A passthrough. Not
        -- consumed by this mart's own correlation/z-score arithmetic below.
        regime_primary_regime,
        regime_confidence_level,
        regime_transition_detected,
        regime_transition_type,
        regime_previous_regime,
        regime_protest_band,
        regime_violence_band,
        regime_suppression_band,
        regime_disorder_band,

        SAFE_DIVIDE(
            composite_pressure_score
            - AVG(composite_pressure_score) OVER (),
            NULLIF(
                STDDEV_SAMP(composite_pressure_score) OVER (),
                0
            )
        ) AS z_pressure

    FROM `{{ var.project_id }}.marts.fact_country_pressure_daily`

    WHERE iso2 = '{{ var.iso2 }}'
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

        MAX(final_confidence_score)
            AS final_confidence_score,

        ANY_VALUE(final_confidence_level)
            AS final_confidence_level,

        ANY_VALUE(intelligence_state)
            AS intelligence_state,

        ANY_VALUE(strongest_driver_protocol)
            AS strongest_driver_protocol,

        ANY_VALUE(strongest_driver_lag_days)
            AS strongest_driver_lag_days,

        ANY_VALUE(strongest_relationship_state)
            AS strongest_relationship_state,

        ANY_VALUE(intelligence_version)
            AS intelligence_version

    FROM
        `{{ var.project_id }}.intelligence.protocol_relationships`

    WHERE country = '{{ var.iso2 }}'

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
        p.confidence_level,

        pr.protocol_stress_score,
        pr.final_confidence_score,
        pr.final_confidence_level,
        pr.intelligence_state,
        pr.strongest_driver_protocol,
        pr.strongest_driver_lag_days,
        pr.strongest_relationship_state,
        pr.intelligence_version,

        pv.conflict_pressure_score,
        pv.legal_pressure_score,
        pv.platform_pressure_score,
        pv.legal_pressure_is_synthetic,
        pv.composite_pressure_score,
        pv.pressure_level,
        pv.z_pressure,
        pv.pressure_window_stddev,

        pv.regime_primary_regime,
        pv.regime_confidence_level,
        pv.regime_transition_detected,
        pv.regime_transition_type,
        pv.regime_previous_regime,
        pv.regime_protest_band,
        pv.regime_violence_band,
        pv.regime_suppression_band,
        pv.regime_disorder_band

    FROM
        `{{ var.project_id }}.reporting.mart_protocol_interference_trends` p

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
        ) AS raw_z_anomaly

    FROM joined
),

quality_adjusted AS (

    SELECT
        *,

        raw_z_anomaly
        * sample_quality_score
        * COALESCE(final_confidence_score, 0.25)
            AS z_anomaly

    FROM normalized
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
        ) AS raw_corr

    FROM quality_adjusted
),

guarded AS (

    SELECT
        *,

        CASE
            WHEN window_obs < 18 THEN NULL
            WHEN COALESCE(anomaly_window_stddev, 0) = 0 THEN NULL
            WHEN COALESCE(pressure_window_stddev, 0) = 0 THEN NULL

            ELSE raw_corr
                 * sample_quality_score
                 * COALESCE(final_confidence_score, 0.25)
        END AS rolling_pressure_corr,

        window_obs < 18
            AS insufficient_history_flag,

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

        ABS(z_anomaly - z_pressure)
        * (2 - sample_quality_score)
            AS stress_divergence

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
    legal_pressure_is_synthetic,
    composite_pressure_score,

    regime_primary_regime,
    regime_confidence_level,
    regime_transition_detected,
    regime_transition_type,
    regime_previous_regime,
    regime_protest_band,
    regime_violence_band,
    regime_suppression_band,
    regime_disorder_band,

    raw_corr,
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
        WHEN trend_state IN (
            'CRITICAL_PROTOCOL_SHIFT',
            'HIGH_PROTOCOL_ANOMALY'
        )
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

        WHEN ABS(rolling_pressure_corr) >= 0.82
            THEN 'STRONG_RELATIONSHIP'

        WHEN ABS(rolling_pressure_corr) >= 0.55
            THEN 'MODERATE_RELATIONSHIP'

        ELSE 'WEAK_OR_NO_RELATIONSHIP'
    END AS correlation_state,

    CASE
        WHEN rolling_pressure_corr >= 0.55
             AND z_anomaly > 0
             AND z_pressure > 0
            THEN 'SYNCHRONIZED_ESCALATION'

        WHEN rolling_pressure_corr <= -0.55
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
        WHEN stress_divergence >= 2.5
            THEN 'HIGH_DIVERGENCE'

        WHEN stress_divergence >= 1.4
            THEN 'MODERATE_DIVERGENCE'

        ELSE 'LOW_DIVERGENCE'
    END AS divergence_state,

    insufficient_history_flag,
    zero_variance_flag,

    'PRESSURE_FACT_V1'
        AS pressure_context_status,

    'protocol_repression_correlation_mart_v4'
        AS reporting_version,

    intelligence_version,

    CURRENT_TIMESTAMP()
        AS snapshot_at

FROM finalized

ORDER BY
    measurement_date,
    protocol