/* @bruin
tags:
  - marts_bq
name: marts.dim_requestors
type: bq.sql
connection: bigquery-default
description: Unified requestor dimension.
owner: civil-liberties-pipeline
depends:
  - stg.google_transparency_requests
  - stg.lumen_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH all_requestors AS (
  SELECT requestor AS requestor_name, 'Google' AS source
  FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
  WHERE (country = 'Kenya' OR cldr_territory = 'KE') AND requestor IS NOT NULL

  UNION DISTINCT

  SELECT sender AS requestor_name, 'Lumen' AS source
  FROM `encoded-joy-485413-k5.stg.lumen_requests`
  WHERE (country = 'Kenya' OR country = 'KE') AND sender IS NOT NULL
)
SELECT DISTINCT
  FARM_FINGERPRINT(CONCAT(requestor_name, '||', source)) AS requestor_key,
  requestor_name,
  source,
  CASE
    WHEN LOWER(requestor_name) LIKE '%government%'
      OR LOWER(requestor_name) LIKE '%ministry%'
      OR LOWER(requestor_name) LIKE '%court%'
      OR LOWER(requestor_name) LIKE '%police%'
      OR LOWER(requestor_name) LIKE '%authority%' THEN 'Government / Law Enforcement'
    WHEN LOWER(requestor_name) LIKE '%copyright%'
      OR LOWER(requestor_name) LIKE '%media%'
      OR LOWER(requestor_name) LIKE '%music%'
      OR LOWER(requestor_name) LIKE '%film%' THEN 'Rights Holder / Media'
    WHEN LOWER(requestor_name) LIKE '%law%'
      OR LOWER(requestor_name) LIKE '%legal%'
      OR LOWER(requestor_name) LIKE '%attorney%' THEN 'Legal Entity'
    ELSE 'Private / Commercial'
  END AS requestor_type
FROM all_requestors
ORDER BY source, requestor_type, requestor_name;
