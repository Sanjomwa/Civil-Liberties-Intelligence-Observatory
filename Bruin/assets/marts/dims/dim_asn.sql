-- reporting.dim_asn
-- @bruin
-- type: bq.sql
-- connection: bigquery-default
-- description: ASN dimension table for censorship + network classification

WITH base AS (
  SELECT DISTINCT
    probe_asn AS asn
  FROM `encoded-joy-485413-k5.stg.ooni_measurements`
  WHERE probe_asn IS NOT NULL
)

SELECT
  asn,

  -- numeric extraction for sorting/analysis
  SAFE_CAST(REGEXP_REPLACE(asn, r'AS', '') AS INT64) AS asn_numeric,

  -- ─────────────────────────────────────────────
  -- NETWORK TYPE CLASSIFICATION (heuristic layer)
  -- ─────────────────────────────────────────────

  CASE
    WHEN asn IN ('AS36926','AS37061','AS33771') THEN 'ISP_CORE'
    WHEN asn LIKE 'AS32%' OR asn LIKE 'AS33%' THEN 'MOBILE_OR_AGGREGATOR'
    WHEN asn IN ('AS15169','AS8075') THEN 'GLOBAL_CDN'
    WHEN asn LIKE 'AS3%' THEN 'REGIONAL_ISP'
    ELSE 'OTHER'
  END AS network_class,

  -- ─────────────────────────────────────────────
  -- ROLE IN OONI CONTEXT
  -- ─────────────────────────────────────────────

  CASE
    WHEN asn IN ('AS36926','AS37061') THEN 'MAJOR_KENYA_ISP'
    WHEN asn IN ('AS33771','AS15399') THEN 'SECONDARY_ISP'
    ELSE 'UNCLASSIFIED'
  END AS kenya_relevance,

  -- ─────────────────────────────────────────────
  -- INTERFERENCE RISK SCORE (0–1 heuristic)
  -- ─────────────────────────────────────────────

  CASE
    WHEN asn IN ('AS36926','AS37061','AS33771') THEN 0.9
    WHEN asn LIKE 'AS32%' THEN 0.6
    ELSE 0.3
  END AS censorship_sensitivity_score,

  CURRENT_TIMESTAMP() AS created_at

FROM base;