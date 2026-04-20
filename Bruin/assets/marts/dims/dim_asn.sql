/* @bruin
tags:
  - marts_bq
name: marts.dim_asn
type: bq.sql
connection: bigquery-default
description: Canonical ASN dimension (stable + deterministic).
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
  SELECT
    CAST(asn AS STRING) AS asn_id,

    ARRAY_AGG(country ORDER BY COUNT(*) DESC LIMIT 1)[OFFSET(0)] AS country

  FROM `encoded-joy-485413-k5.int.ooni_signals`
  WHERE asn IS NOT NULL
  GROUP BY asn_id
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
FROM base;
