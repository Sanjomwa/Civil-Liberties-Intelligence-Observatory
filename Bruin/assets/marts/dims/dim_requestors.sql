/* @bruin
tags:
  - marts_bq
name: marts.dim_requestors
type: bq.sql
connection: bigquery-default
description: |
  Unified requestor dimension with cross-source identity normalization.
  Supports Google Transparency + Lumen takedown ecosystems.

owner: civil-liberties-pipeline

depends:
  - stg.google_transparency_requests
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH all_requestors AS (

    SELECT
        TRIM(requestor) AS requestor_name,
        'Google' AS source
    FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
    WHERE (country = 'Kenya' OR cldr_territory = 'KE')
      AND requestor IS NOT NULL

    UNION DISTINCT

    SELECT
        TRIM(sender) AS requestor_name,
        'Lumen' AS source
    FROM `encoded-joy-485413-k5.stg.lumen_requests`
    WHERE (country = 'Kenya' OR country = 'KE')
      AND sender IS NOT NULL
),

cleaned AS (

    SELECT
        requestor_name,
        source,

        LOWER(requestor_name) AS requestor_name_norm,

        -- cross-source identity (future merge anchor)
        FARM_FINGERPRINT(LOWER(TRIM(requestor_name))) AS requestor_identity_key,

        -- source-specific key
        FARM_FINGERPRINT(CONCAT(LOWER(TRIM(requestor_name)), '||', source)) AS requestor_key

    FROM all_requestors
)

SELECT
    requestor_key,
    requestor_identity_key,
    requestor_name,
    source,

    CASE
        WHEN REGEXP_CONTAINS(LOWER(requestor_name), r'government|ministry|state|authority|court|police|agency')
            THEN 'Government / State'

        WHEN REGEXP_CONTAINS(LOWER(requestor_name), r'court|judicial|prosecutor|attorney|legal')
            THEN 'Law Enforcement / Judiciary'

        WHEN REGEXP_CONTAINS(LOWER(requestor_name), r'copyright|media|music|film|publisher|broadcast')
            THEN 'Rights Holder / Media'

        WHEN REGEXP_CONTAINS(LOWER(requestor_name), r'company|inc|ltd|corp|platform|tech|service')
            THEN 'Private / Commercial'

        ELSE 'Unknown / Other'
    END AS requestor_type

FROM cleaned
ORDER BY source, requestor_type, requestor_name;