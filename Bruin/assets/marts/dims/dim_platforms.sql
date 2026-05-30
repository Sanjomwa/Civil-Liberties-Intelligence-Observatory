/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_platforms
type: bq.sql
connection: bigquery-default

description: |
  Canonical platform and protocol dimension
  across OONI, Google Transparency, and Lumen.

  Scope:
  Kenya observability analysis
  June 2023 → June 2025

  Provides unified platform taxonomy for:
  - protocol interference analysis
  - legal/platform pressure correlation
  - cross-source observability reporting

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
        LOWER(test_name) AS platform_name,
        'OONI' AS source,

        CASE
            WHEN LOWER(test_name) IN (
                'web_connectivity',
                'dnscheck',
                'http_requests'
            ) THEN 'WEB_PROTOCOL'

            WHEN LOWER(test_name) IN (
                'whatsapp',
                'telegram',
                'signal',
                'facebook_messenger'
            ) THEN 'MESSAGING_PLATFORM'

            WHEN LOWER(test_name) IN (
                'tor',
                'psiphon',
                'lantern'
            ) THEN 'CIRCUMVENTION_TOOL'

            ELSE 'OTHER_PROTOCOL'
        END AS platform_category

    FROM `{{ var.project_id }}.stg.ooni_measurements`

    WHERE test_name IS NOT NULL
),

google AS (

    SELECT DISTINCT
        LOWER(product) AS platform_name,
        'GOOGLE_TRANSPARENCY' AS source,
        'PLATFORM_SERVICE' AS platform_category

    FROM `{{ var.project_id }}.stg.google_transparency_requests`

    WHERE product IS NOT NULL
),

lumen AS (

    SELECT DISTINCT
        LOWER(recipient) AS platform_name,
        'LUMEN' AS source,
        'CONTENT_PLATFORM' AS platform_category

    FROM `{{ var.project_id }}.stg.lumen_requests`

    WHERE recipient IS NOT NULL
),

unioned AS (

    SELECT * FROM ooni
    UNION DISTINCT
    SELECT * FROM google
    UNION DISTINCT
    SELECT * FROM lumen
)

SELECT
    FARM_FINGERPRINT(
        CONCAT(platform_name, '||', source)
    ) AS platform_key,

    platform_name,
    source,
    platform_category,

    CASE
        WHEN platform_category IN (
            'MESSAGING_PLATFORM',
            'CONTENT_PLATFORM'
        )
        THEN TRUE
        ELSE FALSE
    END AS is_user_facing_platform,

    CASE
        WHEN platform_category = 'CIRCUMVENTION_TOOL'
        THEN TRUE
        ELSE FALSE
    END AS is_circumvention_tool

FROM unioned;