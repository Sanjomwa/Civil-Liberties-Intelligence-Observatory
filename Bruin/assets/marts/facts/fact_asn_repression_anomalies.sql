/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_anomalies
type: bq.sql
connection: bigquery-default

description: |
  Detects anomalies in ASN repression index using rolling baseline and z-score.

  Grain: measurement_date × asn

owner: civil-liberties-pipeline

depends:
  - marts.fact_asn_repression_index

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT
        measurement_date,
        asn,
        asn_repression_index_v3 AS index_value
    FROM `encoded-joy-485413-k5.marts.fact_asn_repression_index`

),

windowed AS (

    SELECT
        measurement_date,
        asn,
        index_value,

        AVG(index_value) OVER (
            PARTITION BY asn
            ORDER BY measurement_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_mean,

        STDDEV(index_value) OVER (
            PARTITION BY asn
            ORDER BY measurement_date
            ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
        ) AS rolling_std

    FROM base
),

scored AS (

    SELECT
        *,
        SAFE_DIVIDE(
            (index_value - rolling_mean),
            NULLIF(rolling_std, 0)
        ) AS z_score
    FROM windowed
)

SELECT
    *,

    -- anomaly flags
    CASE
        WHEN z_score >= 3 THEN 'EXTREME_SPIKE'
        WHEN z_score >= 2 THEN 'SPIKE'
        WHEN z_score <= -2 THEN 'DROP'
        ELSE 'NORMAL'
    END AS anomaly_type,

    CASE
        WHEN z_score >= 2 THEN TRUE
        WHEN z_score <= -2 THEN TRUE
        ELSE FALSE
    END AS is_anomaly,

    CURRENT_TIMESTAMP() AS extracted_at

FROM scored;