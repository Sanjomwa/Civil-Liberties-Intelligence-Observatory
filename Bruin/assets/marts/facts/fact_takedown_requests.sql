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
  NULL AS item_count,
  extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_google_transparency_requests`
WHERE country = 'Kenya' OR cldr_territory = 'KE'

UNION ALL

SELECT
  'google_detailed' AS source,
  country_region AS country,
  product AS platform,
  NULL AS requestor_name,
  reason,
  NULL AS time_period,
  total AS number_of_requests,
  NULL AS items_requested_removal,
  NULL AS items_removed_legal,
  NULL AS items_removed_policy,
  NULL AS item_count,
  extracted_at,
  period_date AS measurement_date,
  year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_google_transparency_detailed`
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
  NULL AS items_removed_legal,
  NULL AS items_removed_policy,
  item_count,
  extracted_at,
  measurement_date,
  year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_lumen_requests`
WHERE country = 'Kenya' OR country = 'KE';
