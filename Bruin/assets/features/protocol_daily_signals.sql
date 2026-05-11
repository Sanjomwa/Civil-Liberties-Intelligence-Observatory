/* @bruin
name: features.protocol_daily_signals
type: bq.sql
connection: bigquery-default

tags:
  - features_bq
  - dataset_ooni
  - ooni_intelligence_phase_1

description: |
  Deterministic daily OONI protocol signal features.
  Grain: country x measurement_date x protocol x test_family x ASN.

  This is a model-ready feature table. It contains no cross-domain
  intelligence, no correlation logic, and no product/reporting logic.

depends:
  - marts.fact_ooni_censorship_signals

materialization:
  type: table
  strategy: create+replace

columns:
  - name: feature_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: measurement_date
    type: date
    checks:
      - name: not_null
  - name: country
    type: string
    checks:
      - name: not_null
  - name: protocol
    type: string
    checks:
      - name: not_null
      - name: accepted_values
        value: [dns, http, tcp, tls]
  - name: feature_grain
    type: string
    checks:
      - name: not_null
@bruin */

WITH source_events AS (
  SELECT
    measurement_date,
    country,
    LOWER(protocol) AS protocol,
    CASE
      WHEN LOWER(test_name) IN ('web_connectivity') THEN 'web'
      WHEN LOWER(test_name) IN ('whatsapp', 'telegram', 'signal', 'facebook_messenger') THEN 'messaging'
      WHEN LOWER(test_name) IN ('tor', 'psiphon') THEN 'circumvention'
      WHEN LOWER(test_name) IN ('dnscheck') THEN 'dns'
      ELSE COALESCE(LOWER(test_name), 'unknown')
    END AS test_family,
    COALESCE(CAST(probe_asn AS STRING), 'unknown') AS asn,
    probe_network_name AS network_name,
    measurement_id,
    observation_id,
    result_state,
    is_blocking_signal,
    blocking_detail,
    SAFE_CAST(confidence_score AS FLOAT64) AS confidence_score
  FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
  WHERE measurement_date IS NOT NULL
    AND country IS NOT NULL
    AND protocol IS NOT NULL
),

feature_thresholds AS (
  SELECT
    5 AS min_measurements_per_day,
    7 AS min_baseline_days_30d,
    30.0 AS target_measurements_per_day,
    100.0 AS target_observations_per_day
),

measurement_rollup AS (
  SELECT
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    measurement_id,
    MAX(IF(is_blocking_signal, 1, 0)) AS measurement_has_blocking_signal,
    AVG(COALESCE(confidence_score, 0.0)) AS measurement_avg_confidence
  FROM source_events
  GROUP BY
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    measurement_id
),

daily_observation_features AS (
  SELECT
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    ANY_VALUE(network_name) AS network_name,
    COUNT(*) AS observation_count,
    COUNT(DISTINCT observation_id) AS distinct_observation_count,
    COUNTIF(result_state = 'OK') AS ok_events,
    COUNTIF(result_state = 'BLOCKED') AS blocked_events,
    COUNTIF(result_state = 'DOWN') AS down_events,
    COUNTIF(result_state = 'UNKNOWN') AS unknown_events,
    COUNTIF(blocking_detail = 'dns.bogon') AS dns_bogon_events,
    COUNTIF(blocking_detail = 'dns.nxdomain') AS dns_nxdomain_events,
    COUNTIF(blocking_detail = 'tcp.rst') AS tcp_reset_events,
    COUNTIF(blocking_detail = 'tcp.timeout') AS tcp_timeout_events,
    COUNTIF(blocking_detail = 'tls.rst') AS tls_reset_events,
    COUNTIF(STARTS_WITH(blocking_detail, 'tls.') AND blocking_detail NOT IN ('tls.ok', 'tls.rst')) AS tls_handshake_failure_events,
    COUNTIF(blocking_detail = 'http.451') AS http_451_events,
    COUNTIF(STARTS_WITH(blocking_detail, 'http.') AND blocking_detail NOT IN ('http.ok', 'http.451')) AS http_error_events,
    AVG(COALESCE(confidence_score, 0.0)) AS avg_confidence_score,
    COUNTIF(is_blocking_signal AND COALESCE(confidence_score, 0.0) >= 0.80) AS high_confidence_blocked_events,
    COUNTIF(is_blocking_signal AND COALESCE(confidence_score, 0.0) >= 0.60 AND COALESCE(confidence_score, 0.0) < 0.80) AS medium_confidence_blocked_events,
    COUNTIF(is_blocking_signal AND COALESCE(confidence_score, 0.0) > 0.0 AND COALESCE(confidence_score, 0.0) < 0.60) AS low_confidence_blocked_events,
    SAFE_DIVIDE(COUNTIF(is_blocking_signal), COUNT(*)) AS blocked_rate_observation_weighted,
    SAFE_DIVIDE(COUNTIF(result_state = 'UNKNOWN'), COUNT(*)) AS unknown_rate,
    SAFE_DIVIDE(COUNTIF(result_state = 'DOWN'), COUNT(*)) AS down_rate,
    SAFE_DIVIDE(
      SUM(IF(is_blocking_signal, COALESCE(confidence_score, 0.0), 0.0)),
      NULLIF(COUNT(*), 0)
    ) AS confidence_weighted_interference
  FROM source_events
  GROUP BY
    measurement_date,
    country,
    protocol,
    test_family,
    asn
),

daily_measurement_features AS (
  SELECT
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    COUNT(DISTINCT measurement_id) AS measurement_count,
    SAFE_DIVIDE(SUM(measurement_has_blocking_signal), COUNT(DISTINCT measurement_id)) AS blocked_rate_measurement_weighted,
    AVG(measurement_avg_confidence) AS avg_measurement_confidence
  FROM measurement_rollup
  GROUP BY
    measurement_date,
    country,
    protocol,
    test_family,
    asn
),

daily_features AS (
  SELECT
    o.measurement_date,
    o.country,
    o.protocol,
    o.test_family,
    o.asn,
    o.network_name,
    m.measurement_count,
    o.observation_count,
    o.distinct_observation_count,
    o.ok_events,
    o.blocked_events,
    o.down_events,
    o.unknown_events,
    o.dns_bogon_events,
    o.dns_nxdomain_events,
    o.tcp_reset_events,
    o.tcp_timeout_events,
    o.tls_reset_events,
    o.tls_handshake_failure_events,
    o.http_451_events,
    o.http_error_events,
    o.avg_confidence_score,
    m.avg_measurement_confidence,
    o.high_confidence_blocked_events,
    o.medium_confidence_blocked_events,
    o.low_confidence_blocked_events,
    o.blocked_rate_observation_weighted,
    m.blocked_rate_measurement_weighted,
    o.unknown_rate,
    o.down_rate,
    o.confidence_weighted_interference,
    o.confidence_weighted_interference AS signal_rate
  FROM daily_observation_features AS o
  INNER JOIN daily_measurement_features AS m
    USING (measurement_date, country, protocol, test_family, asn)
),

with_baselines AS (
  SELECT
    *,
    AVG(signal_rate) OVER feature_30d_prior AS baseline_signal_rate_30d,
    STDDEV_SAMP(signal_rate) OVER feature_30d_prior AS baseline_signal_stddev_30d,
    COUNT(signal_rate) OVER feature_30d_prior AS baseline_days_30d,
    AVG(signal_rate) OVER feature_90d_prior AS baseline_signal_rate_90d,
    STDDEV_SAMP(signal_rate) OVER feature_90d_prior AS baseline_signal_stddev_90d,
    COUNT(signal_rate) OVER feature_90d_prior AS baseline_days_90d
  FROM daily_features
  WINDOW
    feature_30d_prior AS (
      PARTITION BY country, protocol, test_family, asn
      ORDER BY UNIX_DATE(measurement_date)
      RANGE BETWEEN 30 PRECEDING AND 1 PRECEDING
    ),
    feature_90d_prior AS (
      PARTITION BY country, protocol, test_family, asn
      ORDER BY UNIX_DATE(measurement_date)
      RANGE BETWEEN 90 PRECEDING AND 1 PRECEDING
    )
)

SELECT
  TO_HEX(MD5(CONCAT(
    country, '|',
    CAST(measurement_date AS STRING), '|',
    protocol, '|',
    test_family, '|',
    asn
  ))) AS feature_id,
  measurement_date,
  country,
  protocol,
  test_family,
  asn,
  'country_date_protocol_test_family_asn' AS feature_grain,
  network_name,
  measurement_count,
  observation_count,
  distinct_observation_count,
  ok_events,
  blocked_events,
  down_events,
  unknown_events,
  dns_bogon_events,
  dns_nxdomain_events,
  tcp_reset_events,
  tcp_timeout_events,
  tls_reset_events,
  tls_handshake_failure_events,
  http_451_events,
  http_error_events,
  avg_confidence_score,
  avg_measurement_confidence,
  high_confidence_blocked_events,
  medium_confidence_blocked_events,
  low_confidence_blocked_events,
  blocked_rate_observation_weighted,
  blocked_rate_measurement_weighted,
  unknown_rate,
  down_rate,
  confidence_weighted_interference,
  signal_rate,
  baseline_signal_rate_30d,
  baseline_signal_stddev_30d,
  baseline_days_30d,
  baseline_signal_rate_90d,
  baseline_signal_stddev_90d,
  baseline_days_90d,
  signal_rate - baseline_signal_rate_30d AS signal_delta_30d,
  CASE
    WHEN baseline_signal_stddev_30d IS NULL OR baseline_signal_stddev_30d = 0 THEN NULL
    ELSE SAFE_DIVIDE(signal_rate - baseline_signal_rate_30d, baseline_signal_stddev_30d)
  END AS signal_zscore_30d,
  ABS(CASE
    WHEN baseline_signal_stddev_30d IS NULL OR baseline_signal_stddev_30d = 0 THEN NULL
    ELSE SAFE_DIVIDE(signal_rate - baseline_signal_rate_30d, baseline_signal_stddev_30d)
  END) AS anomaly_score,
  LEAST(1.0, SAFE_DIVIDE(measurement_count, target_measurements_per_day)) AS coverage_score,
  LEAST(
    1.0,
    0.50 * LEAST(1.0, SAFE_DIVIDE(measurement_count, target_measurements_per_day))
      + 0.30 * LEAST(1.0, SAFE_DIVIDE(observation_count, target_observations_per_day))
      + 0.20 * (1.0 - COALESCE(unknown_rate, 0.0))
  ) AS sample_quality_score,
  measurement_count < min_measurements_per_day AS low_sample_flag,
  COALESCE(baseline_days_30d, 0) < min_baseline_days_30d AS sparse_window_flag,
  COALESCE(baseline_signal_stddev_30d, 0.0) = 0.0 AS zero_variance_flag,
  COALESCE(unknown_rate, 0.0) >= 0.50 AS high_unknown_flag,
  TO_JSON_STRING(STRUCT(
    min_measurements_per_day,
    min_baseline_days_30d,
    target_measurements_per_day,
    target_observations_per_day
  )) AS guardrail_config_json,
  'protocol_daily_signals_v1' AS feature_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM with_baselines
CROSS JOIN feature_thresholds;
