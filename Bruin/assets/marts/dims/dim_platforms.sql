/* @bruin
tags:
  - marts_bq
name: marts.dim_platforms
type: bq.sql
connection: bigquery-default
description: Unified platform/service dimension.
owner: civil-liberties-pipeline
depends:
  - stg.ooni_measurements
  - stg.google_transparency_requests
  - stg.lumen_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH combined AS (
  SELECT DISTINCT
    test_name AS platform_name,
    'OONI' AS source,
    CASE
      WHEN test_name IN ('web_connectivity', 'dnscheck', 'http_requests') THEN 'Website / DNS'
      WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal') THEN 'Messaging App'
      WHEN test_name IN ('tor', 'psiphon', 'lantern') THEN 'Circumvention Tool'
      ELSE 'Other Protocol'
    END AS platform_category
  FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_ooni_measurements`
  WHERE probe_cc = 'KE' AND test_name IS NOT NULL

  UNION DISTINCT

  SELECT DISTINCT
    product AS platform_name,
    'Google' AS source,
    'Google Product' AS platform_category
  FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_google_transparency_requests`
  WHERE (country = 'Kenya' OR cldr_territory = 'KE') AND product IS NOT NULL

  UNION DISTINCT

  SELECT DISTINCT
    recipient AS platform_name,
    'Lumen' AS source,
    'Content Platform' AS platform_category
  FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_lumen_requests`
  WHERE (country = 'Kenya' OR country = 'KE') AND recipient IS NOT NULL
)
SELECT
  FARM_FINGERPRINT(CONCAT(platform_name, '||', source)) AS platform_key,
  platform_name,
  source,
  platform_category
FROM combined
ORDER BY source, platform_category, platform_name;
