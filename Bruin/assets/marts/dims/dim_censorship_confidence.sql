/* @bruin
tags:
  - marts_bq
name: marts.dim_censorship_confidence
type: bq.sql
connection: bigquery-default

description: |
  Confidence scoring model for inferred censorship-related network interference signals.
  Represents analytical confidence in observed interference patterns, not proof of intent
  or definitive censorship attribution.

  min_score is the inclusive lower bound of raw OONI confidence_score (from
  int.ooni_experiment_results) that maps to this tier; NULL for NONE, which is
  the fallback when no tier's min_score is met. Canonicalized 2026-07-05 (ADR-0001)
  from features.protocol_daily_signals.sql's thresholds, which independently agreed
  with the (now-retired) bucketing in int.ooni_signals.sql. See ADR-0001 for why
  0.80/0.60 was chosen over the disagreeing 0.90/0.70 that
  marts.fact_platform_blocking_summary used to hardcode.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'NONE' AS confidence_level,
        0 AS ordinal_rank,
        0.00 AS probability_weight,
        CAST(NULL AS FLOAT64) AS min_score,
        'No observable interference signal detected' AS description
    ),

    STRUCT(
        'LOW' AS confidence_level,
        1 AS ordinal_rank,
        0.25 AS probability_weight,
        0.00 AS min_score,
        'Weak interference indicators; likely transient failure or measurement uncertainty' AS description
    ),

    STRUCT(
        'MEDIUM' AS confidence_level,
        2 AS ordinal_rank,
        0.60 AS probability_weight,
        0.60 AS min_score,
        'Moderate interference consistency suggesting possible filtering or disruption' AS description
    ),

    STRUCT(
        'HIGH' AS confidence_level,
        3 AS ordinal_rank,
        0.90 AS probability_weight,
        0.80 AS min_score,
        'Strong repeated interference indicators consistent with probable suppression behavior' AS description
    )

]);