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

  Statistical robustness improvements:
  - stronger baseline sufficiency
  - variance floor protection
  - winsorized signal normalization
  - capped z-score anomalies
  - near-zero variance detection

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
@bruin */

WITH source_events AS (

  SELECT
    measurement_date,
    country,
    LOWER(protocol) AS protocol,

    CASE
      WHEN LOWER(test_name) = 'web_connectivity' THEN 'web'
      WHEN LOWER(test_name) IN (
        'whatsapp',
        'telegram',
        'signal',
        'facebook_messenger'
      ) THEN 'messaging'
      WHEN LOWER(test_name) IN ('tor', 'psiphon')
        THEN 'circumvention'
      WHEN LOWER(test_name) = 'dnscheck'
        THEN 'dns'
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
    14 AS min_baseline_days_30d,
    30.0 AS target_measurements_per_day,
    100.0 AS target_observations_per_day,
    0.00001 AS min_stddev_floor,
    12.0 AS max_zscore_cap
),

measurement_rollup AS (

  SELECT
    measurement_date,
    country,
    protocol,
    test_family,
    asn,
    measurement_id,

    MAX(IF(is_blocking_signal, 1, 0))
      AS measurement_has_blocking_signal,

    AVG(COALESCE(confidence_score, 0.0))
      AS measurement_avg_confidence

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

    COUNTIF(
      STARTS_WITH(blocking_detail, 'tls.')
      AND blocking_detail NOT IN ('tls.ok','tls.rst')
    ) AS tls_handshake_failure_events,

    COUNTIF(blocking_detail = 'http.451')
      AS http_451_events,

    COUNTIF(
      STARTS_WITH(blocking_detail,'http.')
      AND blocking_detail NOT IN ('http.ok','http.451')
    ) AS http_error_events,

    AVG(COALESCE(confidence_score,0.0))
      AS avg_confidence_score,

    COUNTIF(
      is_blocking_signal
      AND COALESCE(confidence_score,0.0) >= 0.80
    ) AS high_confidence_blocked_events,

    COUNTIF(
      is_blocking_signal
      AND confidence_score BETWEEN 0.60 AND 0.799999
    ) AS medium_confidence_blocked_events,

    COUNTIF(
      is_blocking_signal
      AND confidence_score BETWEEN 0.000001 AND 0.599999
    ) AS low_confidence_blocked_events,

    SAFE_DIVIDE(
      COUNTIF(is_blocking_signal),
      COUNT(*)
    ) AS blocked_rate_observation_weighted,

    SAFE_DIVIDE(
      COUNTIF(result_state='UNKNOWN'),
      COUNT(*)
    ) AS unknown_rate,

    SAFE_DIVIDE(
      COUNTIF(result_state='DOWN'),
      COUNT(*)
    ) AS down_rate,

    SAFE_DIVIDE(
      SUM(
        IF(
          is_blocking_signal,
          COALESCE(confidence_score,0.0),
          0.0
        )
      ),
      COUNT(*)
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

    COUNT(DISTINCT measurement_id)
      AS measurement_count,

    SAFE_DIVIDE(
      SUM(measurement_has_blocking_signal),
      COUNT(DISTINCT measurement_id)
    ) AS blocked_rate_measurement_weighted,

    AVG(measurement_avg_confidence)
      AS avg_measurement_confidence

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
    o.*,
    m.measurement_count,
    m.blocked_rate_measurement_weighted,
    m.avg_measurement_confidence,

    LEAST(
      1.0,
      GREATEST(
        0.0,
        o.confidence_weighted_interference
      )
    ) AS signal_rate

  FROM daily_observation_features o
  JOIN daily_measurement_features m
    USING (
      measurement_date,
      country,
      protocol,
      test_family,
      asn
    )
),

with_baselines AS (

  SELECT
    *,

    AVG(signal_rate)
      OVER feature_30d_prior
      AS baseline_signal_rate_30d,

    STDDEV_SAMP(signal_rate)
      OVER feature_30d_prior
      AS baseline_signal_stddev_30d,

    COUNT(signal_rate)
      OVER feature_30d_prior
      AS baseline_days_30d

  FROM daily_features

  WINDOW feature_30d_prior AS (
    PARTITION BY
      country,
      protocol,
      test_family,
      asn
    ORDER BY UNIX_DATE(measurement_date)
    RANGE BETWEEN 30 PRECEDING
    AND 1 PRECEDING
  )
)

SELECT

  TO_HEX(MD5(CONCAT(
    country,'|',
    CAST(measurement_date AS STRING),'|',
    protocol,'|',
    test_family,'|',
    asn
  ))) AS feature_id,

  *,

  signal_rate - baseline_signal_rate_30d
    AS signal_delta_30d,

  CASE
    WHEN baseline_days_30d < min_baseline_days_30d
      THEN NULL

    WHEN baseline_signal_stddev_30d < min_stddev_floor
      THEN NULL

    ELSE LEAST(
      max_zscore_cap,
      ABS(
        SAFE_DIVIDE(
          signal_rate - baseline_signal_rate_30d,
          baseline_signal_stddev_30d
        )
      )
    )
  END AS signal_zscore_30d,

  LEAST(
    12.0,
    ABS(
      CASE
        WHEN baseline_days_30d < min_baseline_days_30d
          THEN NULL

        WHEN baseline_signal_stddev_30d < min_stddev_floor
          THEN NULL

        ELSE SAFE_DIVIDE(
          signal_rate - baseline_signal_rate_30d,
          baseline_signal_stddev_30d
        )
      END
    )
  ) AS anomaly_score,

  LEAST(
    1.0,
    SAFE_DIVIDE(
      measurement_count,
      target_measurements_per_day
    )
  ) AS coverage_score,

  LEAST(
    1.0,
      0.50 * SAFE_DIVIDE(
        measurement_count,
        target_measurements_per_day
      )
    + 0.30 * SAFE_DIVIDE(
        observation_count,
        target_observations_per_day
      )
    + 0.20 * (1.0 - unknown_rate)
  ) AS sample_quality_score,

  measurement_count < min_measurements_per_day
    AS low_sample_flag,

  baseline_days_30d < min_baseline_days_30d
    AS sparse_window_flag,

  baseline_signal_stddev_30d = 0
    AS zero_variance_flag,

  baseline_signal_stddev_30d < min_stddev_floor
    AS near_zero_variance_flag,

  unknown_rate >= 0.50
    AS high_unknown_flag,

  TO_JSON_STRING(STRUCT(
    min_measurements_per_day,
    min_baseline_days_30d,
    target_measurements_per_day,
    target_observations_per_day,
    min_stddev_floor,
    max_zscore_cap
  )) AS guardrail_config_json,

  'protocol_daily_signals_v2'
    AS feature_version,

  CURRENT_TIMESTAMP()
    AS computed_at

FROM with_baselines
CROSS JOIN feature_thresholds;