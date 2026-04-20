/* @bruin
tags:
  - marts_bq
name: marts.dim_asn
type: bq.sql
connection: bigquery-default
description: Deterministic ASN dimension from OONI signals
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ranked AS (
  SELECT
    CAST(asn AS STRING) AS asn_id,
    country,
    COUNT(*) AS freq
  FROM `encoded-joy-485413-k5.int.ooni_signals`
  WHERE asn IS NOT NULL
  GROUP BY asn_id, country
),

dedup AS (
  SELECT *,
    ROW_NUMBER() OVER (PARTITION BY asn_id ORDER BY freq DESC) AS rn
  FROM ranked
)

SELECT
  asn_id,
  CASE
    WHEN country IN ('KE','ke','Kenya','kenya') THEN 'Kenya'
    ELSE INITCAP(country)
  END AS country,

  CASE
    WHEN asn_id LIKE '32%' THEN 'mobile'
    WHEN asn_id LIKE '3%' THEN 'fixed'
    ELSE 'unknown'
  END AS isp_type
FROM dedup
WHERE rn = 1;
