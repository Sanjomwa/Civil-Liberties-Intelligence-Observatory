/* @bruin
tags:
  - reporting

name: reporting.protocol_repression_correlation_mart
type: bq.sql
connection: bigquery-default

description: |
  Measures statistical relationship between protocol-level
  censorship anomalies and country-level repression pressure.

  Produces:
  - rolling protocol-pressure correlation
  - synchronized stress alignment
  - protocol divergence from repression conditions
  - relationship classification

depends:
  - reporting.mart_protocol_interference_trends
  - marts.fact_country_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ============================================
-- PRESSURE NORMALIZATION
-- ============================================
WITH pressure_windowed AS (

    SELECT
        measurement_date,

        conflict_pressure_score,
        legal_pressure_score,
        platform_pressure_score,
        composite_pressure_score,

        SAFE_DIVIDE(
            composite_pressure_score
            - AVG(composite_pressure_score) OVER (),
            NULLIF(STDDEV(composite_pressure_score) OVER (), 0)
        ) AS z_pressure

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
    WHERE country = 'Kenya'
),

-- ============================================
-- GLOBAL PRESSURE ROLLING VARIANCE
-- ============================================
pressure_variance AS (

    SELECT
        *,

        AVG(POW(z_pressure, 2))
        OVER (
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS pressure_variance

    FROM pressure_windowed
),

-- ============================================
-- JOIN PROTOCOL + PRESSURE
-- ============================================
joined AS (

    SELECT
        p.date_key AS measurement_date,
        p.protocol,

        p.measurement_volume,
        p.signal_rate,
        p.confidence_weighted_interference,

        p.anomaly_score,
        p.anomaly_delta,

        pv.conflict_pressure_score,
        pv.legal_pressure_score,
        pv.platform_pressure_score,
        pv.composite_pressure_score,

        pv.z_pressure,
        pv.pressure_variance

    FROM `encoded-joy-485413-k5.reporting.mart_protocol_interference_trends` p

    LEFT JOIN pressure_variance pv
        ON p.date_key = pv.measurement_date

    WHERE p.protocol IS NOT NULL
),

-- ============================================
-- NORMALIZE PROTOCOL ANOMALIES
-- ============================================
normalized AS (

    SELECT
        *,

        SAFE_DIVIDE(
            anomaly_score
            - AVG(anomaly_score)
              OVER (PARTITION BY protocol),

            NULLIF(
                STDDEV(anomaly_score)
                OVER (PARTITION BY protocol),
                0
            )
        ) AS z_anomaly

    FROM joined
),

-- ============================================
-- ROLLING CORRELATION
-- ============================================
correlated AS (

    SELECT
        *,

        COUNT(*)
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS window_obs,

        CORR(
            z_anomaly,
            z_pressure
        ) OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS rolling_pressure_corr

    FROM normalized
),

-- ============================================
-- SYNCHRONIZED STRESS
-- ============================================
synchronized AS (

    SELECT
        *,

        AVG(
            ABS(
                COALESCE(rolling_pressure_corr, 0)
            )
        ) OVER (
            ORDER BY measurement_date
            ROWS BETWEEN 14 PRECEDING AND CURRENT ROW
        ) AS synchronized_stress

    FROM correlated
),

-- ============================================
-- FINAL METRICS
-- ============================================
finalized AS (

    SELECT
        *,

        ABS(
            z_anomaly - z_pressure
        ) AS stress_divergence

    FROM synchronized
)

-- ============================================
-- OUTPUT
-- ============================================
SELECT
    measurement_date,
    protocol,

    measurement_volume,
    signal_rate,
    confidence_weighted_interference,

    anomaly_score,
    anomaly_delta,

    conflict_pressure_score,
    legal_pressure_score,
    platform_pressure_score,
    composite_pressure_score,

    rolling_pressure_corr,
    synchronized_stress,
    stress_divergence,

    CASE
        WHEN anomaly_score >= 4 THEN 'SEVERE'
        WHEN anomaly_score >= 2 THEN 'ELEVATED'
        ELSE 'NORMAL'
    END AS protocol_state,

    CASE
        WHEN composite_pressure_score >= 6 THEN 'SEVERE'
        WHEN composite_pressure_score >= 3 THEN 'ELEVATED'
        ELSE 'LOW'
    END AS pressure_level,

    CASE
        WHEN window_obs < 14
            THEN 'INSUFFICIENT_HISTORY'

        WHEN ABS(rolling_pressure_corr) >= 0.6
            THEN 'STRONG_RELATIONSHIP'

        WHEN ABS(rolling_pressure_corr) >= 0.3
            THEN 'MODERATE_RELATIONSHIP'

        WHEN ABS(rolling_pressure_corr) >= 0.1
            THEN 'WEAK_RELATIONSHIP'

        ELSE 'NO_CLEAR_RELATIONSHIP'
    END AS correlation_state,

    CASE
        WHEN synchronized_stress >= 0.80
            THEN 'HIGH_ALIGNMENT'

        WHEN synchronized_stress >= 0.55
            THEN 'MODERATE_ALIGNMENT'

        WHEN synchronized_stress >= 0.30
            THEN 'WEAK_ALIGNMENT'

        ELSE 'NO_ALIGNMENT'
    END AS alignment_state,

    CASE
        WHEN stress_divergence >= 2.5
            THEN 'SEVERE_PROTOCOL_DIVERGENCE'

        WHEN stress_divergence >= 1.0
            THEN 'MODERATE_PROTOCOL_DIVERGENCE'

        ELSE 'LOW_DIVERGENCE'
    END AS divergence_state,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM finalized
ORDER BY measurement_date, protocol;