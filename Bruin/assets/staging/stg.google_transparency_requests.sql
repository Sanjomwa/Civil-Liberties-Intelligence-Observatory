/* @bruin
tags:
  - staging_bq
  - dataset_google_transparency_requests
name: stg.google_transparency_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Google Transparency removal requests for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.google_transparency_requests_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        time_period,
        country,
        cldr_territory,
        requestor,
        product,
        reason,
        number_of_requests,
        items_requested_removal,
        items_removed_legal,
        items_removed_policy,
        extracted_at,
        CASE
            WHEN REGEXP_CONTAINS(time_period, r'January\s*-\s*June\s+\d{4}')
                THEN DATE(CAST(REGEXP_EXTRACT(time_period, r'(\d{4})') AS INT64), 6, 1)
            WHEN REGEXP_CONTAINS(time_period, r'July\s*-\s*December\s+\d{4}')
                THEN DATE(CAST(REGEXP_EXTRACT(time_period, r'(\d{4})') AS INT64), 12, 1)
            ELSE SAFE.PARSE_DATE('%Y-%m', time_period)
        END AS period_date
    FROM `{{ var.project_id }}.{{ var.bq_dataset }}.google_transparency_requests`
    WHERE country = 'Kenya'
       OR cldr_territory = 'KE'
),

raw AS (
    SELECT
        time_period,
        country,
        cldr_territory,
        requestor,
        product,
        reason,
        number_of_requests,
        items_requested_removal,
        items_removed_legal,
        items_removed_policy,
        extracted_at,
        period_date,
        EXTRACT(YEAR FROM period_date) AS year
    FROM base
    WHERE period_date IS NOT NULL
)

SELECT * FROM raw