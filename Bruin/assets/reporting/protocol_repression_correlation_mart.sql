/* @bruin
tags:
  - reporting

name: reporting.protocol_repression_correlation_mart
type: bq.sql
connection: bigquery-default

description: |
  Measures protocol-level alignment between observed
  OONI interference anomalies and Kenyan national
  repression pressure conditions.

depends:
  - reporting.mart_protocol_interference_trends
  - marts.fact_country_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ============================================
-- JOIN DAILY PROTOCOL + COUNTRY PRESSURE
-- ============================================
WITH joined AS (

    SELECT
        p.date_key AS measurement_date,
        p.protocol,

        p.measurement_volume,
        p.signal_rate,
        p.confidence_weighted_interference,

        p.anomaly_score,
        p.anomaly_delta,
        p.protocol_state,

        c.conflict_pressure_score,
        c.legal_pressure_score,
        c.platform_pressure_score,
        c.composite_pressure_score,
        c.pressure_level

    FROM
        `encoded-joy-485413-k5.reporting.mart_protocol_interference_trends` p

    LEFT JOIN
        `encoded-joy-485413-k5.marts.fact_country_pressure_daily` c
        ON p.date_key = c.measurement_date
),

-- ============================================
-- 30-DAY ROLLING RELATIONSHIP
-- ============================================
rolling AS (

    SELECT
        *,

        CORR(
            anomaly_delta,
            composite_pressure_score
        ) OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS rolling_pressure_corr,

        AVG(anomaly_delta)
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS rolling_protocol_baseline,

        AVG(composite_pressure_score)
        OVER (
            PARTITION BY protocol
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS rolling_pressure_baseline

    FROM joined
),

-- ============================================
-- NORMALIZED ALIGNMENT SCORE
-- ============================================
scored AS (

    SELECT
        *,

        ROUND(
            (
                anomaly_delta
                *
                composite_pressure_score
            ),
            4
        ) AS synchronized_stress,

        ROUND(
            SAFE_DIVIDE(
                anomaly_delta,
                NULLIF(
                    rolling_protocol_baseline,
                    0
                )
            ),
            4
        ) AS protocol_deviation_ratio,

        ROUND(
            SAFE_DIVIDE(
                composite_pressure_score,
                NULLIF(
                    rolling_pressure_baseline,
                    0
                )
            ),
            4
        ) AS pressure_deviation_ratio

    FROM rolling
)

-- ============================================
-- FINAL CLASSIFICATION
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
    protocol_deviation_ratio,
    pressure_deviation_ratio,

    protocol_state,
    pressure_level,

    CASE

        WHEN rolling_pressure_corr >= 0.70
             AND synchronized_stress >= 0.50
            THEN 'STRONG_REPRESSION_ALIGNMENT'

        WHEN rolling_pressure_corr >= 0.45
            THEN 'MODERATE_ALIGNMENT'

        WHEN rolling_pressure_corr >= 0.20
            THEN 'WEAK_ALIGNMENT'

        WHEN rolling_pressure_corr <= -0.20
            THEN 'INVERSE_RELATIONSHIP'

        ELSE 'NO_CLEAR_RELATIONSHIP'

    END AS correlation_state,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM scored

ORDER BY
    measurement_date,
    protocol