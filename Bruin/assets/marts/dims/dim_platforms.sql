/* @bruin
tags:
  - marts_bq
name: marts.dim_platforms
type: bq.sql
connection: bigquery-default

description: |
  Unified platform/service dimension across OONI, Google, and Lumen datasets.

owner: civil-liberties-pipeline

depends:
  - stg.ooni_measurements
  - stg.google_transparency_requests
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH raw AS (

  SELECT
    test_name AS platform_name,
    'OONI' AS source
  FROM `encoded-joy-485413-k5.stg.ooni_measurements`
  WHERE country = 'KE'
    AND test_name IS NOT NULL

  UNION DISTINCT

  SELECT
    product AS platform_name,
    'Google' AS source
  FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
  WHERE (country = 'Kenya' OR cldr_territory = 'KE')
    AND product IS NOT NULL

  UNION DISTINCT

  SELECT
    recipient AS platform_name,
    'Lumen' AS source
  FROM `encoded-joy-485413-k5.stg.lumen_requests`
  WHERE (country = 'Kenya' OR country = 'KE')
    AND recipient IS NOT NULL
),

classified AS (

  SELECT
    platform_name,
    source,

    CASE
      WHEN LOWER(platform_name) IN ('whatsapp','telegram','signal','facebook_messenger')
        THEN 'Messaging'
      WHEN LOWER(platform_name) IN ('web_connectivity','dnscheck','http_requests')
        THEN 'Web / DNS'
      WHEN LOWER(platform_name) IN ('tor','psiphon','lantern')
        THEN 'Circumvention'
      WHEN LOWER(platform_name) LIKE '%google%' THEN 'Search / Platform'
      WHEN LOWER(platform_name) LIKE '%youtube%' THEN 'Media Platform'
      ELSE 'Other'
    END AS service_type

  FROM raw
)

SELECT
  FARM_FINGERPRINT(CONCAT(platform_name, '||', source)) AS platform_key,
  platform_name,
  source,
  service_type
FROM classified;