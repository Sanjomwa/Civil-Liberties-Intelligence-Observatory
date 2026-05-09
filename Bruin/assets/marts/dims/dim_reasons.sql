/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_reasons
type: bq.sql
connection: bigquery-default

description: |
  Unified censorship / takedown reason taxonomy
  across OONI, Google Transparency, and Lumen.

  Scope:
  Kenya civil-liberties observability
  June 2023 → June 2025

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals
  - stg.google_transparency_requests
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH google AS (

    SELECT DISTINCT
        LOWER(reason) AS raw_reason,
        'GOOGLE_TRANSPARENCY' AS source

    FROM `encoded-joy-485413-k5.stg.google_transparency_requests`

    WHERE reason IS NOT NULL
),

lumen AS (

    SELECT DISTINCT
        LOWER(reason) AS raw_reason,
        'LUMEN' AS source

    FROM `encoded-joy-485413-k5.stg.lumen_requests`

    WHERE reason IS NOT NULL
),

ooni AS (

    SELECT DISTINCT
        LOWER(
            COALESCE(
                blocking_detail,
                failure_reason,
                'unknown'
            )
        ) AS raw_reason,

        'OONI' AS source

    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
),

unioned AS (

    SELECT * FROM google
    UNION DISTINCT
    SELECT * FROM lumen
    UNION DISTINCT
    SELECT * FROM ooni
)

SELECT
    FARM_FINGERPRINT(
        CONCAT(raw_reason, '||', source)
    ) AS reason_key,

    raw_reason,
    source,

    CASE
        WHEN raw_reason LIKE '%defamation%'
            OR raw_reason LIKE '%privacy%'
        THEN 'REPUTATION_PRIVACY'

        WHEN raw_reason LIKE '%copyright%'
            OR raw_reason LIKE '%dmca%'
            OR raw_reason LIKE '%trademark%'
        THEN 'INTELLECTUAL_PROPERTY'

        WHEN raw_reason LIKE '%security%'
            OR raw_reason LIKE '%government%'
            OR raw_reason LIKE '%court%'
        THEN 'STATE_LEGAL_PRESSURE'

        WHEN raw_reason LIKE '%hate%'
            OR raw_reason LIKE '%violent%'
            OR raw_reason LIKE '%terror%'
        THEN 'CONTENT_MODERATION'

        WHEN raw_reason LIKE '%dns%'
            OR raw_reason LIKE '%tcp%'
            OR raw_reason LIKE '%tls%'
        THEN 'NETWORK_INTERFERENCE'

        WHEN raw_reason LIKE '%service%'
            OR raw_reason LIKE '%timeout%'
            OR raw_reason LIKE '%failure%'
        THEN 'SERVICE_DISRUPTION'

        ELSE 'OTHER'
    END AS reason_category,

    CASE
        WHEN source = 'OONI'
        THEN TRUE
        ELSE FALSE
    END AS is_inferred_reason

FROM unioned;