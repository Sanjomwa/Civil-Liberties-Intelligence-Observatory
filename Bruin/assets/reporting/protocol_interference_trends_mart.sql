/* @bruin
tags:
  - reporting

name: reporting.mart_protocol_interference_trends
type: bq.sql
connection: bigquery-default

description: |
  Detects protocol-level censorship interference trends across
  DNS, HTTP, TCP and TLS observations in Kenya.

depends:
  - marts.fact_ooni_censorship_signals
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ============================================
-- DAILY PROTOCOL AGGREGATION
-- ============================================
WITH base AS (

    SELECT
        d.date_key,
        s.protocol,

        COUNT(*) AS measurement_volume,

        AVG(
            CASE
                WHEN s.is_blocking_signal THEN 1
                ELSE 0
            END
        ) AS signal_rate,

        AVG(
            CASE
                WHEN s.is_blocking_signal
                    THEN s.confidence_score
                ELSE 0
            END
        ) AS confidence_weighted_interference,

        COUNTIF(
            s.result_state != 'OK'
        ) AS failure_count

    FROM `encoded-joy-485413-k5.marts.dim_dates` d

    LEFT JOIN
        `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals` s
        ON d.date_key = s.measurement_date
        AND s.country = 'KE'

    GROUP BY
        d.date_key,
        s.protocol
),

-- ============================================
-- SCORE PROTOCOL STRESS
-- ============================================
scored AS (

    SELECT
        *,

        SAFE_DIVIDE(
            failure_count,
            measurement_volume
        ) AS protocol_failure_distribution,

        ROUND(
            (
                signal_rate * 5
              + confidence_weighted_interference * 8
              + SAFE_DIVIDE(
                    failure_count,
                    measurement_volume
                ) * 3
            ),
            4
        ) AS anomaly_score

    FROM base
),

-- ============================================
-- ROLLING BASELINE
-- ============================================
windowed AS (

    SELECT
        *,

        AVG(anomaly_score)
        OVER (
            PARTITION BY protocol
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS rolling_baseline

    FROM scored
),

-- ============================================
-- DELTA FROM HISTORICAL BASELINE
-- ============================================
finalized AS (

    SELECT
        *,

        ROUND(
            anomaly_score
            -
            COALESCE(
                rolling_baseline,
                anomaly_score
            ),
            4
        ) AS anomaly_delta

    FROM windowed
)

-- ============================================
-- FINAL CLASSIFICATION
-- ============================================
SELECT
    date_key,
    protocol,

    measurement_volume,

    signal_rate,
    confidence_weighted_interference,
    protocol_failure_distribution,

    anomaly_score,
    rolling_baseline,
    anomaly_delta,

    CASE

        WHEN anomaly_delta >= 0.75
            THEN 'CRITICAL_PROTOCOL_SHIFT'

        WHEN anomaly_delta >= 0.35
            THEN 'HIGH_PROTOCOL_ANOMALY'

        WHEN anomaly_delta >= 0.10
            THEN 'ELEVATED_PROTOCOL_ACTIVITY'

        ELSE 'NORMAL'

    END AS protocol_state,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM finalized

WHERE protocol IS NOT NULL

ORDER BY
    date_key,
    protocol