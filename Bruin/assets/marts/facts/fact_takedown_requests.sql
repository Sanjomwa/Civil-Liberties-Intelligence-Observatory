/* @bruin
tags:
  - marts_bq
name: marts.fact_takedown_requests
type: bq.sql
connection: bigquery-default
description: Row-level takedown requests (Google + Lumen).
owner: civil-liberties-pipeline
depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  'google_requests' AS source,
  country,
  product AS platform,
  requestor AS requestor_name,
  reason,
  time_period,
  number_of_requests,
  items_requested_removal,
  items_removed_legal,
  items_removed_policy,
  CAST(NULL AS INT64) AS item_count,
  CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
WHERE country = 'Kenya' OR cldr_territory = 'KE'

UNION ALL

SELECT
  'google_detailed' AS source,
  country_region AS country,
  product AS platform,
  CAST(NULL AS STRING) AS requestor_name,
  reason,
  CAST(NULL AS STRING) AS time_period,
  total AS number_of_requests,
  CAST(NULL AS INT64) AS items_requested_removal,
  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,
  CAST(NULL AS INT64) AS item_count,
  CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.stg.google_transparency_detailed`
WHERE cldr_territory_code = 'KE'

UNION ALL

SELECT
  'lumen' AS source,
  country,
  recipient AS platform,
  sender AS requestor_name,
  reason,
  period AS time_period,
  request_count AS number_of_requests,
  item_count AS items_requested_removal,
  CAST(NULL AS INT64) AS items_removed_legal,
  CAST(NULL AS INT64) AS items_removed_policy,
  item_count,
  CASE
    WHEN extracted_at IS NULL THEN NULL
    WHEN CAST(extracted_at AS INT64) BETWEEN 946684800 AND 4102444800
      THEN TIMESTAMP_SECONDS(CAST(extracted_at AS INT64))
    WHEN CAST(extracted_at AS INT64) BETWEEN 946684800000 AND 4102444800000
      THEN TIMESTAMP_MILLIS(CAST(extracted_at AS INT64))
    WHEN CAST(extracted_at AS INT64) BETWEEN 946684800000000 AND 4102444800000000
      THEN TIMESTAMP_MICROS(CAST(extracted_at AS INT64))
    WHEN CAST(extracted_at AS INT64) BETWEEN 946684800000000000 AND 4102444800000000000
      THEN TIMESTAMP_MICROS(DIV(CAST(extracted_at AS INT64), 1000))
    ELSE NULL
  END AS extracted_at,
  measurement_date,
  year
FROM `encoded-joy-485413-k5.stg.lumen_requests`
WHERE country = 'Kenya' OR country = 'KE';
