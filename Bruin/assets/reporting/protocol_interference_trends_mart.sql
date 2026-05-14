/* @bruin
tags:
  - reporting

name: reporting.mart_protocol_interference_trends
type: bq.sql
connection: bigquery-default

description: |
  Protocol-level interference trends (Kenya). Grain: date_key x protocol.
  v5: weighted anomaly_score; observation-mass regime rollup + share diagnostics.

depends:
  - features.protocol_daily_signals
  - intelligence.protocol_signal_regimes
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH rollup_thresholds AS (
  SELECT
    0.01 AS severe_obs_share_min,
    0.02 AS elevated_obs_share_min,
    0.50 AS insufficient_obs_share_min,
    0.30 AS high_confidence_obs_share_min,
    0.15 AS medium_confidence_obs_share_min
),

feature_daily AS (
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
      SUM(IF(anomaly_score IS NOT NULL, anomaly_score * observation_count, 0)),
      NULLIF(SUM(IF(anomaly_score IS NOT NULL, observation_count, 0)), 0)
    ) AS anomaly_score,
    SAFE_DIVIDE(
      SUM(sample_quality_score * observation_count),
      NULLIF(SUM(observation_count), 0)
    ) AS sample_quality_score,
    COUNTIF(low_sample_flag) AS low_sample_feature_rows,
    COUNTIF(sparse_window_flag) AS sparse_window_feature_rows,
    COUNTIF(zero_variance_flag) AS zero_variance_feature_rows,
    ANY_VALUE(feature_version) AS feature_version
  FROM `encoded-joy-485413-k5.features.protocol_daily_signals`
  WHERE country = 'KE'
  GROUP BY measurement_date, protocol
),

regime_cell AS (
  SELECT
    measurement_date,
    protocol,
    protocol_state,
    confidence_level,
    regime_confidence,
    protocol_stress_score,
    observation_count,
    intelligence_version
  FROM `encoded-joy-485413-k5.intelligence.protocol_signal_regimes`
  WHERE country = 'KE'
),

regime_agg AS (
  SELECT
    measurement_date,
    protocol,
    SUM(observation_count) AS obs_total,
    SUM(
      IF(
        protocol_state IN (
          'LOW_SAMPLE',
          'ZERO_VARIANCE',
          'INSUFFICIENT_BASELINE',
          'INVALID_STATISTICS'
        ),
        observation_count,
        0
      )
    ) AS obs_insufficient,
    SUM(IF(protocol_state = 'SEVERE_ELEVATION', observation_count, 0)) AS obs_severe,
    SUM(IF(protocol_state = 'ELEVATED', observation_count, 0)) AS obs_elevated,
    SUM(IF(protocol_state = 'BELOW_BASELINE', observation_count, 0)) AS obs_below_baseline,
    SUM(IF(confidence_level = 'HIGH', observation_count, 0)) AS obs_conf_high,
    SUM(IF(confidence_level = 'MEDIUM', observation_count, 0)) AS obs_conf_medium,
    SUM(IF(regime_confidence IS NOT NULL, regime_confidence * observation_count, 0))
      AS regime_confidence_weighted_sum,
    SUM(IF(regime_confidence IS NOT NULL, observation_count, 0)) AS regime_confidence_obs,
    MAX(protocol_stress_score) AS protocol_stress_score_max,
    ANY_VALUE(intelligence_version) AS intelligence_version
  FROM regime_cell
  GROUP BY measurement_date, protocol
),

regime_daily AS (
  SELECT
    a.measurement_date,
    a.protocol,
    a.protocol_stress_score_max AS protocol_stress_score,
    SAFE_DIVIDE(a.obs_insufficient, NULLIF(a.obs_total, 0)) AS insufficient_obs_share,
    SAFE_DIVIDE(a.obs_severe, NULLIF(a.obs_total, 0)) AS severe_obs_share,
    SAFE_DIVIDE(a.obs_elevated, NULLIF(a.obs_total, 0)) AS elevated_obs_share,
    SAFE_DIVIDE(
      a.regime_confidence_weighted_sum,
      NULLIF(a.regime_confidence_obs, 0)
    ) AS regime_confidence,
    CASE
      WHEN SAFE_DIVIDE(a.obs_severe, NULLIF(a.obs_total, 0)) >= t.severe_obs_share_min
        THEN 'SEVERE_ELEVATION'
      WHEN SAFE_DIVIDE(a.obs_elevated, NULLIF(a.obs_total, 0)) >= t.elevated_obs_share_min
        THEN 'ELEVATED'
      WHEN SAFE_DIVIDE(a.obs_insufficient, NULLIF(a.obs_total, 0)) >= t.insufficient_obs_share_min
        THEN 'INSUFFICIENT_DATA'
      WHEN SAFE_DIVIDE(a.obs_below_baseline, NULLIF(a.obs_total, 0)) >= t.elevated_obs_share_min
        THEN 'BELOW_BASELINE'
      ELSE 'NORMAL_RANGE'
    END AS protocol_state,
    CASE
      WHEN SAFE_DIVIDE(a.obs_conf_high, NULLIF(a.obs_total, 0)) >= t.high_confidence_obs_share_min
        THEN 'HIGH'
      WHEN SAFE_DIVIDE(
        a.obs_conf_high + a.obs_conf_medium,
        NULLIF(a.obs_total, 0)
      ) >= t.medium_confidence_obs_share_min
        THEN 'MEDIUM'
      ELSE 'LOW'
    END AS confidence_level,
    a.intelligence_version
  FROM regime_agg AS a
  CROSS JOIN rollup_thresholds AS t
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
  r.insufficient_obs_share,
  r.severe_obs_share,
  r.elevated_obs_share,
  f.sample_quality_score,
  f.low_sample_feature_rows,
  f.sparse_window_feature_rows,
  f.zero_variance_feature_rows,
  CASE
    WHEN r.protocol_state = 'SEVERE_ELEVATION' THEN 'CRITICAL_PROTOCOL_SHIFT'
    WHEN r.protocol_state = 'ELEVATED' THEN 'HIGH_PROTOCOL_ANOMALY'
    WHEN r.protocol_state = 'INSUFFICIENT_DATA' THEN 'INSUFFICIENT_DATA'
    WHEN r.protocol_state = 'BELOW_BASELINE' THEN 'BELOW_BASELINE'
    ELSE 'NORMAL'
  END AS trend_state,
  'protocol_interference_trends_mart_v5' AS reporting_version,
  f.feature_version,
  r.intelligence_version,
  CURRENT_TIMESTAMP() AS snapshot_at
FROM `encoded-joy-485413-k5.marts.dim_dates` AS d
LEFT JOIN feature_daily AS f
  ON d.date_key = f.measurement_date
LEFT JOIN regime_daily AS r
  ON f.measurement_date = r.measurement_date
  AND f.protocol = r.protocol
WHERE f.protocol IS NOT NULL
ORDER BY d.date_key, f.protocol;