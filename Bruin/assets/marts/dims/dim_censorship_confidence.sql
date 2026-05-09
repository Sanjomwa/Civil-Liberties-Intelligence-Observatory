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

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'NONE' AS confidence_level,
        0 AS ordinal_rank,
        0.00 AS probability_weight,
        'No observable interference signal detected' AS description
    ),

    STRUCT(
        'LOW' AS confidence_level,
        1 AS ordinal_rank,
        0.25 AS probability_weight,
        'Weak interference indicators; likely transient failure or measurement uncertainty' AS description
    ),

    STRUCT(
        'MEDIUM' AS confidence_level,
        2 AS ordinal_rank,
        0.60 AS probability_weight,
        'Moderate interference consistency suggesting possible filtering or disruption' AS description
    ),

    STRUCT(
        'HIGH' AS confidence_level,
        3 AS ordinal_rank,
        0.90 AS probability_weight,
        'Strong repeated interference indicators consistent with probable suppression behavior' AS description
    )

]);