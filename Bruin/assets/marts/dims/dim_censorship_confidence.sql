/* @bruin
tags:
  - marts_bq
name: marts.dim_censorship_confidence
type: bq.sql
connection: bigquery-default

description: |
  Confidence model for censorship detection across OONI-derived datasets.
  Provides both ordinal ranking and normalized probability weights for scoring models.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'LOW' AS confidence_level,
        1 AS ordinal_rank,
        0.25 AS probability_weight,
        'Weak or noisy signal; likely measurement uncertainty' AS description
    ),

    STRUCT(
        'MEDIUM' AS confidence_level,
        2 AS ordinal_rank,
        0.60 AS probability_weight,
        'Probable censorship signal with moderate confidence' AS description
    ),

    STRUCT(
        'HIGH' AS confidence_level,
        3 AS ordinal_rank,
        0.90 AS probability_weight,
        'Strong censorship signal with high confidence' AS description
    ),

    STRUCT(
        'NONE' AS confidence_level,
        0 AS ordinal_rank,
        0.00 AS probability_weight,
        'No evidence of censorship detected' AS description
    )

]);