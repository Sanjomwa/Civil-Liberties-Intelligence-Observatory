/* @bruin
tags:
  - marts_bq
name: marts.dim_reasons
type: bq.sql
connection: bigquery-default
description: Standardized takedown/censorship reasons.
owner: civil-liberties-pipeline
depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH all_reasons AS (
  SELECT reason, 'Google Requests' AS source
  FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
  WHERE (country = 'Kenya' OR cldr_territory = 'KE') AND reason IS NOT NULL

  UNION DISTINCT

  SELECT reason, 'Google Detailed' AS source
  FROM `encoded-joy-485413-k5.stg.google_transparency_detailed`
  WHERE cldr_territory_code = 'KE' AND reason IS NOT NULL

  UNION DISTINCT

  SELECT reason, 'Lumen' AS source
  FROM `encoded-joy-485413-k5.stg.lumen_requests`
  WHERE (country = 'Kenya' OR country = 'KE') AND reason IS NOT NULL
)
SELECT DISTINCT
  reason,
  source,
  CASE
    WHEN LOWER(reason) LIKE '%defamation%' OR LOWER(reason) LIKE '%privacy%' THEN 'Privacy & Reputation'
    WHEN LOWER(reason) LIKE '%copyright%' OR LOWER(reason) LIKE '%trademark%' THEN 'Intellectual Property'
    WHEN LOWER(reason) LIKE '%hate%' OR LOWER(reason) LIKE '%violent%' OR LOWER(reason) LIKE '%terror%' THEN 'Harmful Content'
    WHEN LOWER(reason) LIKE '%national security%' OR LOWER(reason) LIKE '%government%' THEN 'Government / National Security'
    WHEN LOWER(reason) LIKE '%fraud%' OR LOWER(reason) LIKE '%spam%' THEN 'Fraud & Spam'
    ELSE 'Other'
  END AS reason_group
FROM all_reasons
ORDER BY source, reason;
