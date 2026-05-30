/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_requestors
type: bq.sql
connection: bigquery-default

description: |
  Canonical requestor identity dimension.

  Normalizes requesting entities across
  Google Transparency and Lumen legal ecosystems.

  Scope:
  Kenya civil-liberties analysis
  June 2023 → June 2025

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
        'GOOGLE_TRANSPARENCY' AS source
    FROM `{{ var.project_id }}.stg.google_transparency_requests`
    WHERE requestor IS NOT NULL

    UNION DISTINCT

    SELECT
        TRIM(sender) AS requestor_name,
        'LUMEN' AS source
    FROM `{{ var.project_id }}.stg.lumen_requests`
    WHERE sender IS NOT NULL
),

normalized AS (

    SELECT
        requestor_name,
        source,

        LOWER(TRIM(requestor_name)) AS requestor_norm,

        FARM_FINGERPRINT(
            LOWER(TRIM(requestor_name))
        ) AS requestor_identity_key,

        FARM_FINGERPRINT(
            CONCAT(
                LOWER(TRIM(requestor_name)),
                '||',
                source
            )
        ) AS requestor_key

    FROM all_requestors
)

SELECT
    requestor_key,
    requestor_identity_key,

    requestor_name,
    source,

    CASE

        WHEN REGEXP_CONTAINS(
            requestor_norm,
            r'court|judicial|judge|tribunal|attorney|legal|prosecutor'
        )
        THEN 'JUDICIAL_LEGAL'

        WHEN REGEXP_CONTAINS(
            requestor_norm,
            r'ministry|government|state|authority|agency|police'
        )
        THEN 'STATE_EXECUTIVE'

        WHEN REGEXP_CONTAINS(
            requestor_norm,
            r'copyright|publisher|media|music|film|broadcast'
        )
        THEN 'RIGHTS_HOLDER'

        WHEN REGEXP_CONTAINS(
            requestor_norm,
            r'company|corp|inc|ltd|platform|service|tech'
        )
        THEN 'PRIVATE_ENTITY'

        ELSE 'OTHER'

    END AS requestor_type

FROM normalized;