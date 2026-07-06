/* @bruin
tags:
  - reporting

name: reporting.mart_protocol_interference_trends
type: bq.sql
connection: bigquery-default

description: |
  Protocol-level interference trends (Kenya). Grain: date_key x protocol.

  v5: observation-weighted anomaly_score; regime rollup uses observation mass
  (thresholds in rollup_thresholds) so sparse tails do not erase protocol-day
  signal when most volume is reliable.

  v6 (TD-49, 2026-07-06): the regime rollup's share denominators are now
  computed PER test_family, never pooled across families. TD-54's measured
  finding: pooling dnscheck's dedicated high-volume, near-zero-signal DNS
  observations (test_family='dns', recovered by TD-47) into the same
  denominator as the DNS-layer checks embedded in app tests
  (test_family='messaging'/'circumvention') one-directionally dilutes real
  app-blocking shares below the fixed thresholds -- in the Finance Bill
  2024 simulation, two ELEVATED days flipped to NORMAL and 06-23's severe
  margin thinned 0.041->0.016 from volume asymmetry alone. Semantics now:
  - severe_obs_share / elevated_obs_share = MAX across families of that
    family's own within-family share. protocol_state fires iff some
    family crosses the threshold within its own volume ("is any kind of
    testing of this protocol layer showing elevated blocking"), so
    `severe_obs_share >= severe_obs_share_min` remains equivalent to
    SEVERE_ELEVATION, as before -- but a high-volume quiet family can no
    longer mask a small loud one.
  - insufficient_obs_share = MIN across families; INSUFFICIENT_DATA fires
    only when EVERY family's volume is majority-insufficient (one family
    having thin data must not label the protocol insufficient while
    another family has good data, and vice versa).
  - state_driving_family (new column) names which test_family triggered
    the protocol_state; confidence_level and regime_confidence now come
    from that driving family, so the state and its confidence describe
    the same evidence rather than a pooled blend (dnscheck's bulk sits at
    MEDIUM confidence and was diluting/inflating the pooled bands).
  - protocol_stress_score was already MAX across cells and is unchanged.
  The feature_daily CTE's continuous descriptive rates (signal_rate etc.)
  remain deliberately observation-weighted across families: they are
  volume-honest descriptions of all traffic at that layer, not threshold
  classifications; per-family rates live in features.protocol_daily_signals
  and per-app rates in marts.fact_protocol_blocking_summary /
  reporting.mart_pressure_attribution_ooni_daily.

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
  FROM `{{ var.project_id }}.features.protocol_daily_signals`
  WHERE country = 'KE'
  GROUP BY measurement_date, protocol
),

regime_cell AS (
  SELECT
    measurement_date,
    protocol,
    test_family,
    protocol_state,
    confidence_level,
    regime_confidence,
    protocol_stress_score,
    observation_count,
    intelligence_version
  FROM `{{ var.project_id }}.intelligence.protocol_signal_regimes`
  WHERE country = 'KE'
),

-- TD-49: aggregate WITHIN each test_family first. A family's shares are
-- of its own volume only -- dnscheck's dedicated 'dns' family volume
-- never enters the denominator of messaging/circumvention's embedded
-- DNS checks, and vice versa.
regime_family_agg AS (
  SELECT
    measurement_date,
    protocol,
    test_family,
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
  GROUP BY measurement_date, protocol, test_family
),

regime_family AS (
  SELECT
    a.measurement_date,
    a.protocol,
    a.test_family,
    a.obs_total,
    a.protocol_stress_score_max,
    a.intelligence_version,
    SAFE_DIVIDE(a.obs_insufficient, NULLIF(a.obs_total, 0)) AS insufficient_share,
    SAFE_DIVIDE(a.obs_severe, NULLIF(a.obs_total, 0)) AS severe_share,
    SAFE_DIVIDE(a.obs_elevated, NULLIF(a.obs_total, 0)) AS elevated_share,
    SAFE_DIVIDE(a.obs_below_baseline, NULLIF(a.obs_total, 0)) AS below_baseline_share,
    SAFE_DIVIDE(
      a.regime_confidence_weighted_sum,
      NULLIF(a.regime_confidence_obs, 0)
    ) AS family_regime_confidence,
    CASE
      WHEN SAFE_DIVIDE(a.obs_conf_high, NULLIF(a.obs_total, 0)) >= t.high_confidence_obs_share_min
        THEN 'HIGH'
      WHEN SAFE_DIVIDE(
        a.obs_conf_high + a.obs_conf_medium,
        NULLIF(a.obs_total, 0)
      ) >= t.medium_confidence_obs_share_min
        THEN 'MEDIUM'
      ELSE 'LOW'
    END AS family_confidence_level
  FROM regime_family_agg AS a
  CROSS JOIN rollup_thresholds AS t
),

-- Roll families up to date x protocol. Severity states are ANY-quantified
-- (some family crossed its own threshold); INSUFFICIENT_DATA is
-- ALL-quantified (every family majority-insufficient). The emitted share
-- columns keep the invariant `share >= threshold <=> state fires`:
-- MAX for severe/elevated/below, MIN for insufficient.
regime_daily_agg AS (
  SELECT
    measurement_date,
    protocol,
    MAX(protocol_stress_score_max) AS protocol_stress_score,
    MAX(severe_share) AS severe_obs_share,
    MAX(elevated_share) AS elevated_obs_share,
    MAX(below_baseline_share) AS below_baseline_share_max,
    MIN(insufficient_share) AS insufficient_obs_share,
    ARRAY_AGG(
      STRUCT(test_family, family_confidence_level, family_regime_confidence)
      ORDER BY severe_share DESC, obs_total DESC LIMIT 1
    )[OFFSET(0)] AS by_severe,
    ARRAY_AGG(
      STRUCT(test_family, family_confidence_level, family_regime_confidence)
      ORDER BY elevated_share DESC, obs_total DESC LIMIT 1
    )[OFFSET(0)] AS by_elevated,
    ARRAY_AGG(
      STRUCT(test_family, family_confidence_level, family_regime_confidence)
      ORDER BY below_baseline_share DESC, obs_total DESC LIMIT 1
    )[OFFSET(0)] AS by_below,
    ARRAY_AGG(
      STRUCT(test_family, family_confidence_level, family_regime_confidence)
      ORDER BY obs_total DESC LIMIT 1
    )[OFFSET(0)] AS by_volume,
    ANY_VALUE(intelligence_version) AS intelligence_version
  FROM regime_family
  GROUP BY measurement_date, protocol
),

regime_daily AS (
  SELECT
    a.measurement_date,
    a.protocol,
    a.protocol_stress_score,
    a.insufficient_obs_share,
    a.severe_obs_share,
    a.elevated_obs_share,
    CASE
      WHEN a.severe_obs_share >= t.severe_obs_share_min
        THEN 'SEVERE_ELEVATION'
      WHEN a.elevated_obs_share >= t.elevated_obs_share_min
        THEN 'ELEVATED'
      WHEN a.insufficient_obs_share >= t.insufficient_obs_share_min
        THEN 'INSUFFICIENT_DATA'
      WHEN a.below_baseline_share_max >= t.elevated_obs_share_min
        THEN 'BELOW_BASELINE'
      ELSE 'NORMAL_RANGE'
    END AS protocol_state,
    CASE
      WHEN a.severe_obs_share >= t.severe_obs_share_min
        THEN a.by_severe.test_family
      WHEN a.elevated_obs_share >= t.elevated_obs_share_min
        THEN a.by_elevated.test_family
      WHEN a.insufficient_obs_share >= t.insufficient_obs_share_min
        THEN a.by_volume.test_family
      WHEN a.below_baseline_share_max >= t.elevated_obs_share_min
        THEN a.by_below.test_family
      ELSE a.by_volume.test_family
    END AS state_driving_family,
    CASE
      WHEN a.severe_obs_share >= t.severe_obs_share_min
        THEN a.by_severe.family_confidence_level
      WHEN a.elevated_obs_share >= t.elevated_obs_share_min
        THEN a.by_elevated.family_confidence_level
      WHEN a.insufficient_obs_share >= t.insufficient_obs_share_min
        THEN a.by_volume.family_confidence_level
      WHEN a.below_baseline_share_max >= t.elevated_obs_share_min
        THEN a.by_below.family_confidence_level
      ELSE a.by_volume.family_confidence_level
    END AS confidence_level,
    CASE
      WHEN a.severe_obs_share >= t.severe_obs_share_min
        THEN a.by_severe.family_regime_confidence
      WHEN a.elevated_obs_share >= t.elevated_obs_share_min
        THEN a.by_elevated.family_regime_confidence
      WHEN a.insufficient_obs_share >= t.insufficient_obs_share_min
        THEN a.by_volume.family_regime_confidence
      WHEN a.below_baseline_share_max >= t.elevated_obs_share_min
        THEN a.by_below.family_regime_confidence
      ELSE a.by_volume.family_regime_confidence
    END AS regime_confidence,
    a.intelligence_version
  FROM regime_daily_agg AS a
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
  r.state_driving_family,
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
  'protocol_interference_trends_mart_v6' AS reporting_version,
  f.feature_version,
  r.intelligence_version,
  CURRENT_TIMESTAMP() AS snapshot_at
FROM `{{ var.project_id }}.marts.dim_dates` AS d
LEFT JOIN feature_daily AS f
  ON d.date_key = f.measurement_date
LEFT JOIN regime_daily AS r
  ON f.measurement_date = r.measurement_date
  AND f.protocol = r.protocol
WHERE f.protocol IS NOT NULL
ORDER BY d.date_key, f.protocol;