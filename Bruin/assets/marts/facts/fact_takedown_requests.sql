/* @bruin
tags:
  - marts_bq
name: marts.fact_takedown_requests
type: bq.sql
connection: bigquery-default

description: Row-level takedown requests (Google + Lumen) - normalized and schema-resilient.

owner: civil-liberties-pipeline

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

-- =========================
-- GOOGLE REQUESTS (RAW)
-- =========================
SELECT
  'google_requests' AS source,
  LOWER(COALESCE(country, cldr_territory)) AS country,
  product AS platform,
  requestor AS requestor_name,
  reason,
  time_period,
  number_of_requests,
  items_requested_removal,
  items_removed_legal,
  items_removed_policy,
  CAST(NULL AS INT64) AS item_count,
  SAFE_CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
WHERE LOWER(COALESCE(country, cldr_territory)) IN ('kenya','ke')

UNION ALL

-- =========================
-- GOOGLE DETAILED (AGGREGATED)
-- =========================
SELECT
  'google_detailed' AS source,
  LOWER(COALESCE(country_region, cldr_territory_code)) AS country,
  product AS platform,
  CAST(NULL AS STRING) AS requestor_name,
  reason,
  CAST(NULL AS STRING) AS time_period,
  total AS number_of_requests,
  CAST(NULL AS INT64) AS items_requested_removal,
  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,
  CAST(NULL AS INT64) AS item_count,
  SAFE_CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.stg.google_transparency_detailed`
WHERE LOWER(cldr_territory_code) IN ('ke','kenya')

UNION ALL

-- =========================
-- LUMEN (FIXED + SCHEMA SAFE)
-- =========================
SELECT
  'lumen' AS source,

  LOWER(COALESCE(country, 'unknown')) AS country,

  COALESCE(recipient, platform, 'unknown') AS platform,
  COALESCE(sender, requestor_name, 'unknown') AS requestor_name,

  reason,

  COALESCE(time_period, period, half_year_label) AS time_period,

  request_count AS number_of_requests,
  item_count AS items_requested_removal,

  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,

  item_count,

  SAFE_CAST(extracted_at AS TIMESTAMP) AS extracted_at,

  COALESCE(
    measurement_date,
    DATE(period),
    DATE(date_submitted)
  ) AS measurement_date,

  COALESCE(year, EXTRACT(YEAR FROM DATE(date_submitted))) AS year

FROM `encoded-joy-485413-k5.stg.lumen_requests`
WHERE LOWER(COALESCE(country, '')) IN ('ke','kenya');
