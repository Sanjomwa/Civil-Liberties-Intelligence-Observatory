/* @bruin
tags:
  - reporting

name: reporting.mart_protocol_interference_trends
type: bq.sql
connection: bigquery-default

description: |
  Detects protocol-level censorship interference trends across DNS, HTTP,
  TCP and TLS observations in Kenya.

depends:
  - features.protocol_daily_signals
  - intelligence.protocol_signal_regimes
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH feature_daily AS (

    SELECT
        measurement_date,
        protocol,

        SUM(measurement_count) AS measurement_volume,
        SUM(observation_count) AS observation_volume,

        SAFE_DIVIDE(
            SUM(signal_rate * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS signal_rate,

        SAFE_DIVIDE(
            SUM(confidence_weighted_interference * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS confidence_weighted_interference,

        SAFE_DIVIDE(
            SUM((unknown_rate + down_rate) * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS protocol_failure_distribution,

        SAFE_DIVIDE(
            SUM(baseline_signal_rate_30d * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS rolling_baseline,

        SAFE_DIVIDE(
            SUM(signal_delta_30d * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS anomaly_delta,

        SAFE_DIVIDE(
            SUM(
                COALESCE(anomaly_score, 0)
                * observation_count
            ),
            NULLIF(
                SUM(
                    CASE
                        WHEN anomaly_score IS NOT NULL
                            THEN observation_count
                    END
                ),
                0
            )
        ) AS anomaly_score,

        SAFE_DIVIDE(
            SUM(sample_quality_score * observation_count),
            NULLIF(SUM(observation_count), 0)
        ) AS sample_quality_score,

        COUNTIF(low_sample_flag)
            AS low_sample_feature_rows,

        COUNTIF(sparse_window_flag)
            AS sparse_window_feature_rows,

        COUNTIF(zero_variance_flag)
            AS zero_variance_feature_rows,

        ANY_VALUE(feature_version)
            AS feature_version

    FROM
        `encoded-joy-485413-k5.features.protocol_daily_signals`

    WHERE country = 'KE'

    GROUP BY
        measurement_date,
        protocol
),

regime_daily AS (

    SELECT
        measurement_date,
        protocol,

        MAX(protocol_stress_score)
            AS protocol_stress_score,

        CASE
            WHEN COUNTIF(
                protocol_state = 'SEVERE_ELEVATION'
            ) > 0
                THEN 'SEVERE_ELEVATION'

            WHEN COUNTIF(
                protocol_state = 'ELEVATED'
            ) > 0
                THEN 'ELEVATED'

            WHEN COUNTIF(
                protocol_state IN (
                    'LOW_SAMPLE',
                    'ZERO_VARIANCE',
                    'INSUFFICIENT_BASELINE',
                    'INVALID_STATISTICS'
                )
            ) > 0
                THEN 'INSUFFICIENT_DATA'

            ELSE 'NORMAL_RANGE'
        END AS protocol_state,

        CASE
            WHEN COUNTIF(confidence_level = 'HIGH') > 0
                THEN 'HIGH'

            WHEN COUNTIF(confidence_level = 'MEDIUM') > 0
                THEN 'MEDIUM'

            ELSE 'LOW'
        END AS confidence_level,

        MAX(regime_confidence)
            AS regime_confidence,

        ANY_VALUE(intelligence_version)
            AS intelligence_version

    FROM
        `encoded-joy-485413-k5.intelligence.protocol_signal_regimes`

    WHERE country = 'KE'

    GROUP BY
        measurement_date,
        protocol
)

SELECT
    d.date_key,

    f.protocol,

    f.measurement_volume,
    f.observation_volume,

    f.signal_rate,
    f.confidence_weighted_interference,
    f.protocol_failure_distribution,

    f.anomaly_score,
    f.rolling_baseline,
    f.anomaly_delta,

    r.protocol_stress_score,
    r.protocol_state,
    r.confidence_level,
    r.regime_confidence,

    f.sample_quality_score,

    f.low_sample_feature_rows,
    f.sparse_window_feature_rows,
    f.zero_variance_feature_rows,

    CASE
        WHEN r.protocol_state = 'SEVERE_ELEVATION'
            THEN 'CRITICAL_PROTOCOL_SHIFT'

        WHEN r.protocol_state = 'ELEVATED'
            THEN 'HIGH_PROTOCOL_ANOMALY'

        WHEN r.protocol_state = 'INSUFFICIENT_DATA'
            THEN 'INSUFFICIENT_DATA'

        ELSE 'NORMAL'
    END AS trend_state,

    'protocol_interference_trends_mart_v4'
        AS reporting_version,

    f.feature_version,
    r.intelligence_version,

    CURRENT_TIMESTAMP()
        AS snapshot_at

FROM
    `encoded-joy-485413-k5.marts.dim_dates` d

LEFT JOIN feature_daily f
    ON d.date_key = f.measurement_date

LEFT JOIN regime_daily r
    ON f.measurement_date = r.measurement_date
   AND f.protocol = r.protocol

WHERE f.protocol IS NOT NULL

ORDER BY
    d.date_key,
    f.protocol
;