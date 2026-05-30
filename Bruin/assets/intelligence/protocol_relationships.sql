/* @bruin
name: intelligence.protocol_relationships
type: bq.sql
connection: bigquery-default

tags:
  - intelligence_bq
  - dataset_ooni
  - ooni_intelligence_phase_1

description: |
  Final OONI-only protocol intelligence surface.
  Grain: country x measurement_date x protocol x test_family x ASN.

  This table combines protocol regime classification with the strongest
  observed protocol-to-protocol lag relationship.

depends:
  - intelligence.protocol_signal_regimes
  - intelligence.protocol_lag_relationships

materialization:
  type: table
  strategy: create+replace

columns:
  - name: protocol_relationship_id
    type: string
    checks:
      - name: not_null
      - name: unique
@bruin */

WITH regimes AS (
  SELECT *
  FROM `{{ var.project_id }}.intelligence.protocol_signal_regimes`
),

ranked_relationships AS (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY country, measurement_date, target_protocol, test_family, asn
      ORDER BY
        relationship_strength DESC NULLS LAST,
        relationship_confidence_score DESC NULLS LAST,
        lag_days ASC
    ) AS relationship_rank
  FROM `{{ var.project_id }}.intelligence.protocol_lag_relationships`
  WHERE guarded_lag_correlation IS NOT NULL
),

best_relationship AS (
  SELECT
    country,
    measurement_date,
    target_protocol AS protocol,
    test_family,
    asn,
    driver_protocol AS strongest_driver_protocol,
    lag_days AS strongest_driver_lag_days,
    guarded_lag_correlation AS strongest_lag_correlation,
    relationship_strength AS strongest_relationship_strength,
    relationship_state AS strongest_relationship_state,
    lag_direction AS strongest_lag_direction,
    relationship_confidence_score AS strongest_relationship_confidence_score
  FROM ranked_relationships
  WHERE relationship_rank = 1
)

SELECT
  TO_HEX(MD5(CONCAT(
    r.country, '|',
    CAST(r.measurement_date AS STRING), '|',
    r.protocol, '|',
    r.test_family, '|',
    r.asn, '|protocol_relationships_v1'
  ))) AS protocol_relationship_id,
  r.measurement_date,
  r.country,
  r.protocol,
  r.test_family,
  r.asn,
  r.network_name,
  r.measurement_count,
  r.observation_count,
  r.signal_rate,
  r.confidence_weighted_interference,
  r.baseline_signal_rate_30d,
  r.signal_delta_30d,
  r.signal_zscore_30d,
  r.anomaly_score,
  r.protocol_stress_score,
  r.protocol_state,
  r.baseline_divergence_state,
  COALESCE(b.strongest_driver_protocol, 'none') AS strongest_driver_protocol,
  b.strongest_driver_lag_days,
  b.strongest_lag_correlation,
  b.strongest_relationship_strength,
  COALESCE(b.strongest_relationship_state, 'NO_STABLE_RELATIONSHIP') AS strongest_relationship_state,
  COALESCE(b.strongest_lag_direction, 'NONE') AS strongest_lag_direction,
  b.strongest_relationship_confidence_score,
  CASE
    WHEN r.confidence_level = 'LOW' THEN 'LOW'
    WHEN b.strongest_relationship_confidence_score IS NULL THEN r.confidence_level
    WHEN b.strongest_relationship_confidence_score >= 0.75 AND r.confidence_level = 'HIGH' THEN 'HIGH'
    WHEN b.strongest_relationship_confidence_score >= 0.50 THEN 'MEDIUM'
    ELSE 'LOW'
  END AS final_confidence_level,
  LEAST(
    1.0,
    0.60 * COALESCE(r.sample_quality_score, 0.0)
      + 0.40 * COALESCE(b.strongest_relationship_confidence_score, 0.0)
  ) AS final_confidence_score,
  CASE
    WHEN r.protocol_state IN ('LOW_SAMPLE', 'SPARSE_WINDOW', 'ZERO_VARIANCE_BASELINE', 'INSUFFICIENT_BASELINE') THEN 'INSUFFICIENT_DATA'
    WHEN r.protocol_state IN ('SEVERE_ELEVATION', 'ELEVATED')
      AND COALESCE(b.strongest_relationship_state, '') IN ('STRONG_POSITIVE', 'MODERATE_POSITIVE')
      THEN 'COUPLED_PROTOCOL_ESCALATION'
    WHEN r.protocol_state IN ('SEVERE_ELEVATION', 'ELEVATED')
      THEN 'ISOLATED_PROTOCOL_ESCALATION'
    WHEN r.protocol_state = 'BELOW_BASELINE' THEN 'BELOW_BASELINE'
    WHEN COALESCE(b.strongest_relationship_state, '') IN ('STRONG_POSITIVE', 'MODERATE_POSITIVE')
      THEN 'COUPLED_WITH_OTHER_PROTOCOL'
    ELSE 'NO_ACTIVE_ESCALATION'
  END AS intelligence_state,
  r.statistical_warning_flags,
  'protocol_relationships_v1' AS intelligence_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM regimes AS r
LEFT JOIN best_relationship AS b
  USING (country, measurement_date, protocol, test_family, asn);
