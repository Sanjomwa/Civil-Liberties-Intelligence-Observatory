/* @bruin
tags:
  - marts_bq
name: marts.fact_takedown_requests
type: bq.sql
connection: bigquery-default

description: Row-level takedown requests (Google + Lumen), unified schema.

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
  country AS country,
  product AS platform,
  requestor AS requestor_name,
  reason AS reason,
  time_period AS time_period,

  CAST(number_of_requests AS INT64) AS number_of_requests,
  CAST(items_requested_removal AS INT64) AS items_requested_removal,
  CAST(items_removed_legal AS INT64) AS items_removed_legal,
  CAST(items_removed_policy AS INT64) AS items_removed_policy,

  CAST(NULL AS INT64) AS item_count,

  CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year AS year

FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
WHERE country = 'Kenya' OR cldr_territory = 'KE'


UNION ALL

-- =========================
-- GOOGLE DETAILED
-- =========================
SELECT
  'google_detailed' AS source,
  country_region AS country,
  product AS platform,
  CAST(NULL AS STRING) AS requestor_name,
  reason AS reason,
  CAST(NULL AS STRING) AS time_period,

  CAST(total AS INT64) AS number_of_requests,
  CAST(NULL AS INT64) AS items_requested_removal,
  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,

  CAST(NULL AS INT64) AS item_count,

  CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year AS year

FROM `encoded-joy-485413-k5.stg.google_transparency_detailed`
WHERE cldr_territory_code = 'KE'


UNION ALL

-- =========================
-- LUMEN
-- =========================
SELECT
  'lumen' AS source,
  country AS country,
  recipient AS platform,
  sender AS requestor_name,
  reason AS reason,
  period AS time_period,

  CAST(request_count AS INT64) AS number_of_requests,
  CAST(NULL AS INT64) AS items_requested_removal,
  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,

  CAST(item_count AS INT64) AS item_count,

  CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  measurement_date AS measurement_date,
  year AS year

FROM `encoded-joy-485413-k5.stg.lumen_requests`
WHERE country IN ('Kenya', 'KE', 'ke');