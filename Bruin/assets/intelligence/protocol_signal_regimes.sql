/* @bruin
name: intelligence.protocol_signal_regimes
type: bq.sql
connection: bigquery-default

tags:
  - intelligence_bq
  - dataset_ooni
  - ooni_intelligence_phase_1

description: |
  OONI-only protocol stress, divergence-from-baseline, and regime
  classification.
  Grain: country x measurement_date x protocol x test_family x ASN.

  This is an intelligence table. It consumes deterministic OONI features and
  emits explainable inference states with statistical guardrails.

depends:
  - features.protocol_daily_signals

materialization:
  type: table
  strategy: create+replace

columns:
  - name: regime_id
    type: string
    checks:
      - name: not_null
      - name: unique
@bruin */

WITH features AS (
  SELECT
    *
  FROM `encoded-joy-485413-k5.features.protocol_daily_signals`
),

guardrails AS (
  SELECT
    14 AS medium_confidence_baseline_days_30d,
    21 AS high_confidence_baseline_days_30d,
    2.0 AS elevated_zscore_threshold,
    3.0 AS severe_zscore_threshold,
    5.0 AS stress_score_cap_zscore
),

scored AS (
  SELECT
    f.*,
    CASE
      WHEN low_sample_flag OR sparse_window_flag THEN NULL
      WHEN zero_variance_flag THEN NULL
      ELSE signal_zscore_30d
    END AS guarded_signal_zscore_30d,
    CASE
      WHEN low_sample_flag OR sparse_window_flag THEN NULL
      WHEN zero_variance_flag THEN NULL
      ELSE LEAST(100.0, 100.0 * SAFE_DIVIDE(ABS(signal_zscore_30d), stress_score_cap_zscore))
    END AS protocol_stress_score,
    CASE
      WHEN low_sample_flag THEN 'LOW_SAMPLE'
      WHEN sparse_window_flag THEN 'SPARSE_WINDOW'
      WHEN zero_variance_flag THEN 'ZERO_VARIANCE_BASELINE'
      WHEN signal_zscore_30d >= severe_zscore_threshold THEN 'SEVERE_ELEVATION'
      WHEN signal_zscore_30d >= elevated_zscore_threshold THEN 'ELEVATED'
      WHEN signal_zscore_30d <= -elevated_zscore_threshold THEN 'BELOW_BASELINE'
      WHEN signal_zscore_30d IS NULL THEN 'INSUFFICIENT_BASELINE'
      ELSE 'NORMAL_RANGE'
    END AS protocol_state,
    CASE
      WHEN low_sample_flag OR sparse_window_flag OR zero_variance_flag THEN 'UNRELIABLE'
      WHEN ABS(signal_zscore_30d) >= 3 THEN 'HIGH_DIVERGENCE'
      WHEN ABS(signal_zscore_30d) >= 2 THEN 'MODERATE_DIVERGENCE'
      WHEN ABS(signal_zscore_30d) >= 1 THEN 'LOW_DIVERGENCE'
      ELSE 'ALIGNED_WITH_BASELINE'
    END AS baseline_divergence_state,
    CASE
      WHEN low_sample_flag OR sparse_window_flag THEN 'LOW'
      WHEN high_unknown_flag THEN 'LOW'
      WHEN zero_variance_flag THEN 'MEDIUM'
      WHEN sample_quality_score >= 0.80 AND baseline_days_30d >= high_confidence_baseline_days_30d THEN 'HIGH'
      WHEN sample_quality_score >= 0.50 AND baseline_days_30d >= medium_confidence_baseline_days_30d THEN 'MEDIUM'
      ELSE 'LOW'
    END AS confidence_level,
    TO_JSON_STRING(STRUCT(
      medium_confidence_baseline_days_30d,
      high_confidence_baseline_days_30d,
      elevated_zscore_threshold,
      severe_zscore_threshold,
      stress_score_cap_zscore
    )) AS intelligence_guardrail_config_json
  FROM features AS f
  CROSS JOIN guardrails
)

SELECT
  TO_HEX(MD5(CONCAT(
    country, '|',
    CAST(measurement_date AS STRING), '|',
    protocol, '|',
    test_family, '|',
    asn, '|protocol_signal_regimes_v1'
  ))) AS regime_id,
  measurement_date,
  country,
  protocol,
  test_family,
  asn,
  network_name,
  measurement_count,
  observation_count,
  signal_rate,
  confidence_weighted_interference,
  baseline_signal_rate_30d,
  baseline_signal_stddev_30d,
  baseline_days_30d,
  signal_delta_30d,
  signal_zscore_30d,
  guarded_signal_zscore_30d,
  anomaly_score,
  protocol_stress_score,
  protocol_state,
  baseline_divergence_state,
  confidence_level,
  sample_quality_score,
  low_sample_flag,
  sparse_window_flag,
  zero_variance_flag,
  high_unknown_flag,
  ARRAY_TO_STRING(
    ARRAY(
      SELECT warning
      FROM UNNEST([
        IF(low_sample_flag, 'LOW_SAMPLE', NULL),
        IF(sparse_window_flag, 'SPARSE_WINDOW', NULL),
        IF(zero_variance_flag, 'ZERO_VARIANCE_BASELINE', NULL),
        IF(high_unknown_flag, 'HIGH_UNKNOWN_RATE', NULL)
      ]) AS warning
      WHERE warning IS NOT NULL
    ),
    ','
  ) AS statistical_warning_flags,
  intelligence_guardrail_config_json,
  'protocol_signal_regimes_v1' AS intelligence_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM scored;
