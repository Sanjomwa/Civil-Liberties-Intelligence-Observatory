/* @bruin
tags:
  - marts_bq
name: marts.dim_reasons
type: bq.sql
connection: bigquery-default

description: Unified reason dimension.

owner: civil-liberties-pipeline
depends:
  - stg.ooni_measurements
  - stg.google_transparency_requests
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni AS (
  SELECT DISTINCT
    test_name AS platform_name,
    'OONI' AS source,
    CASE
      WHEN test_name IN ('web_connectivity', 'dnscheck', 'http_requests') THEN 'Website / DNS'
      WHEN test_name IN ('whatsapp', 'telegram', 'signal', 'facebook_messenger') THEN 'Messaging App'
      WHEN test_name IN ('tor', 'psiphon', 'lantern') THEN 'Circumvention Tool'
      ELSE 'Other Protocol'
    END AS platform_category
  FROM `encoded-joy-485413-k5.stg.ooni_measurements`
  WHERE test_name IS NOT NULL
),

google AS (
  SELECT DISTINCT
    product AS platform_name,
    'Google' AS source,
    'Google Product' AS platform_category
  FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
  WHERE product IS NOT NULL
),

lumen AS (
  SELECT DISTINCT
    recipient AS platform_name,
    'Lumen' AS source,
    'Content Platform' AS platform_category
  FROM `encoded-joy-485413-k5.stg.lumen_requests`
  WHERE recipient IS NOT NULL
)

SELECT
  FARM_FINGERPRINT(CONCAT(platform_name, '||', source)) AS platform_key,
  platform_name,
  source,
  platform_category
FROM (
  SELECT * FROM ooni
  UNION DISTINCT
  SELECT * FROM google
  UNION DISTINCT
  SELECT * FROM lumen
);