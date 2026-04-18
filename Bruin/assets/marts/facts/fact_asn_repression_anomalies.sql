/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_anomalies
type: bq.sql
connection: bigquery-default

description: |
  Detects temporal anomalies in ASN repression behavior using rolling
  statistical deviation of the ASN repression index.

  Grain:
    measurement_date × country × asn

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
        country,
        asn,
        asn_repression_index
    FROM `encoded-joy-485413-k5.marts.fact_asn_repression_index`
),

rolling_stats AS (
    SELECT
        measurement_date,
        country,
        asn,
        asn_repression_index,

        -- 30-day rolling baseline
        AVG(asn_repression_index) OVER (
            PARTITION BY country, asn
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS avg_index_30d,

        STDDEV(asn_repression_index) OVER (
            PARTITION BY country, asn
            ORDER BY measurement_date
            ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
        ) AS stddev_index_30d

    FROM base
)

SELECT
    measurement_date,
    country,
    asn,
    asn_repression_index,
    avg_index_30d,
    stddev_index_30d,

    -- =========================
    -- Z-SCORE STYLE ANOMALY
    -- =========================
    SAFE_DIVIDE(
        (asn_repression_index - avg_index_30d),
        NULLIF(stddev_index_30d, 0)
    ) AS anomaly_score,

    -- =========================
    -- INTERPRETATION
    -- =========================
    CASE
        WHEN SAFE_DIVIDE(
            (asn_repression_index - avg_index_30d),
            NULLIF(stddev_index_30d, 0)
        ) >= 2.5 THEN 'EXTREME_SPIKE'

        WHEN SAFE_DIVIDE(
            (asn_repression_index - avg_index_30d),
            NULLIF(stddev_index_30d, 0)
        ) >= 1.5 THEN 'MODERATE_SPIKE'

        WHEN SAFE_DIVIDE(
            (asn_repression_index - avg_index_30d),
            NULLIF(stddev_index_30d, 0)
        ) <= -1.5 THEN 'DROP_OR_RELAXATION'

        ELSE 'NORMAL'
    END AS anomaly_class

FROM rolling_stats;