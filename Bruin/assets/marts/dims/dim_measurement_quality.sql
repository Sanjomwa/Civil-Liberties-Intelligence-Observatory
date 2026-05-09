/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_measurement_quality
type: bq.sql
connection: bigquery-default

description: |
  Canonical OONI measurement reliability taxonomy.

  Used to score trustworthiness of censorship observations
  and suppress noisy or incomplete measurements in
  downstream repression and pressure analytics.

  Scope:
  Kenya observability analysis
  June 2023 → June 2025

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'COMPLETE' AS quality_level,
        1.00 AS weight,
        5 AS reliability_score,
        'Complete protocol execution with valid outputs and full metadata'
            AS description
    ),

    STRUCT(
        'PARTIAL' AS quality_level,
        0.80 AS weight,
        4 AS reliability_score,
        'Mostly complete execution with minor missing fields'
            AS description
    ),

    STRUCT(
        'DEGRADED' AS quality_level,
        0.55 AS weight,
        3 AS reliability_score,
        'Protocol completed with ambiguous or degraded outputs'
            AS description
    ),

    STRUCT(
        'NOISY' AS quality_level,
        0.35 AS weight,
        2 AS reliability_score,
        'Measurement likely affected by transient probe or network instability'
            AS description
    ),

    STRUCT(
        'INCOMPLETE' AS quality_level,
        0.15 AS weight,
        1 AS reliability_score,
        'Critical protocol outputs missing; weak analytical trust'
            AS description
    ),

    STRUCT(
        'FAILED' AS quality_level,
        0.00 AS weight,
        0 AS reliability_score,
        'Measurement execution failed completely'
            AS description
    )

]);