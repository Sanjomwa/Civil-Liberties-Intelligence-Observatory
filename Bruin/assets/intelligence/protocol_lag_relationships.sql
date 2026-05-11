/* @bruin
name: intelligence.protocol_lag_relationships
type: bq.sql
connection: bigquery-default

tags:
  - intelligence_bq
  - dataset_ooni
  - ooni_intelligence_phase_1

description: |
  OONI-only protocol-to-protocol lag relationships.
  Grain: country x measurement_date x target_protocol x driver_protocol x
  test_family x ASN x lag_days.

  This table identifies whether one protocol's daily anomaly signal moves with
  or ahead of another protocol's anomaly signal. It is not pressure modeling.

depends:
  - features.protocol_daily_signals

materialization:
  type: table
  strategy: create+replace

columns:
  - name: lag_relationship_id
    type: string
    checks:
      - name: not_null
      - name: unique
@bruin */

WITH lag_config AS (
  SELECT 0 AS lag_days UNION ALL
  SELECT 1 UNION ALL
  SELECT 7 UNION ALL
  SELECT 14 UNION ALL
  SELECT 30
),

guardrails AS (
  SELECT
    14 AS min_relationship_sample_count,
    30 AS relationship_window_days,
    0.40 AS moderate_correlation_threshold,
    0.70 AS strong_correlation_threshold
),

features AS (
  SELECT
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    signal_rate,
    anomaly_score,
    confidence_weighted_interference,
    sample_quality_score,
    low_sample_flag,
    sparse_window_flag,
    zero_variance_flag
  FROM `encoded-joy-485413-k5.features.protocol_daily_signals`
),

paired AS (
  SELECT
    target.country,
    target.measurement_date,
    target.protocol AS target_protocol,
    driver.protocol AS driver_protocol,
    target.test_family,
    target.asn,
    lag_config.lag_days,
    target.signal_rate AS target_signal_rate,
    target.anomaly_score AS target_anomaly_score,
    driver.signal_rate AS driver_signal_rate,
    driver.anomaly_score AS driver_anomaly_score,
    target.sample_quality_score AS target_sample_quality_score,
    driver.sample_quality_score AS driver_sample_quality_score,
    target.low_sample_flag OR driver.low_sample_flag AS low_sample_flag,
    target.sparse_window_flag OR driver.sparse_window_flag AS sparse_window_flag,
    target.zero_variance_flag OR driver.zero_variance_flag AS zero_variance_flag,
    guardrails.min_relationship_sample_count,
    guardrails.relationship_window_days,
    guardrails.moderate_correlation_threshold,
    guardrails.strong_correlation_threshold
  FROM features AS target
  CROSS JOIN lag_config
  CROSS JOIN guardrails
  INNER JOIN features AS driver
    ON target.country = driver.country
    AND target.test_family = driver.test_family
    AND target.asn = driver.asn
    AND target.protocol != driver.protocol
    AND driver.measurement_date = DATE_SUB(target.measurement_date, INTERVAL lag_config.lag_days DAY)
),

with_window_stats AS (
  SELECT
    *,
    COUNT(*) OVER relationship_window AS relationship_sample_count,
    STDDEV_SAMP(target_anomaly_score) OVER relationship_window AS target_window_stddev,
    STDDEV_SAMP(driver_anomaly_score) OVER relationship_window AS driver_window_stddev,
    CORR(target_anomaly_score, driver_anomaly_score) OVER relationship_window AS raw_lag_correlation
  FROM paired
  WINDOW relationship_window AS (
    PARTITION BY country, target_protocol, driver_protocol, test_family, asn, lag_days
    ORDER BY UNIX_DATE(measurement_date)
    RANGE BETWEEN 30 PRECEDING AND CURRENT ROW
  )
),

guarded AS (
  SELECT
    *,
    relationship_sample_count < min_relationship_sample_count AS insufficient_sample_flag,
    COALESCE(target_window_stddev, 0.0) = 0.0 OR COALESCE(driver_window_stddev, 0.0) = 0.0 AS relationship_zero_variance_flag,
    CASE
      WHEN relationship_sample_count < min_relationship_sample_count THEN NULL
      WHEN COALESCE(target_window_stddev, 0.0) = 0.0 THEN NULL
      WHEN COALESCE(driver_window_stddev, 0.0) = 0.0 THEN NULL
      WHEN low_sample_flag OR sparse_window_flag THEN NULL
      ELSE raw_lag_correlation
    END AS guarded_lag_correlation
  FROM with_window_stats
)

SELECT
  TO_HEX(MD5(CONCAT(
    country, '|',
    CAST(measurement_date AS STRING), '|',
    target_protocol, '|',
    driver_protocol, '|',
    test_family, '|',
    asn, '|',
    CAST(lag_days AS STRING), '|protocol_lag_relationships_v1'
  ))) AS lag_relationship_id,
  measurement_date,
  country,
  target_protocol,
  driver_protocol,
  test_family,
  asn,
  lag_days,
  target_signal_rate,
  target_anomaly_score,
  driver_signal_rate,
  driver_anomaly_score,
  raw_lag_correlation,
  guarded_lag_correlation,
  ABS(guarded_lag_correlation) AS relationship_strength,
  CASE
    WHEN insufficient_sample_flag THEN 'INSUFFICIENT_DATA'
    WHEN relationship_zero_variance_flag THEN 'ZERO_VARIANCE'
    WHEN low_sample_flag OR sparse_window_flag THEN 'LOW_QUALITY_WINDOW'
    WHEN guarded_lag_correlation >= strong_correlation_threshold THEN 'STRONG_POSITIVE'
    WHEN guarded_lag_correlation >= moderate_correlation_threshold THEN 'MODERATE_POSITIVE'
    WHEN guarded_lag_correlation <= -strong_correlation_threshold THEN 'STRONG_NEGATIVE'
    WHEN guarded_lag_correlation <= -moderate_correlation_threshold THEN 'MODERATE_NEGATIVE'
    WHEN guarded_lag_correlation IS NULL THEN 'UNSTABLE'
    ELSE 'WEAK_OR_NONE'
  END AS relationship_state,
  CASE
    WHEN lag_days = 0 THEN 'SAME_DAY'
    ELSE 'DRIVER_PROTOCOL_LEADS_TARGET'
  END AS lag_direction,
  relationship_sample_count,
  target_window_stddev,
  driver_window_stddev,
  LEAST(
    1.0,
    0.40 * LEAST(1.0, SAFE_DIVIDE(relationship_sample_count, 30.0))
      + 0.30 * COALESCE(target_sample_quality_score, 0.0)
      + 0.30 * COALESCE(driver_sample_quality_score, 0.0)
  ) AS relationship_confidence_score,
  insufficient_sample_flag,
  relationship_zero_variance_flag AS zero_variance_flag,
  low_sample_flag,
  sparse_window_flag,
  TO_JSON_STRING(STRUCT(
    min_relationship_sample_count,
    relationship_window_days,
    moderate_correlation_threshold,
    strong_correlation_threshold
  )) AS intelligence_guardrail_config_json,
  'protocol_lag_relationships_v1' AS intelligence_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM guarded;
