/* @bruin
name: fact_takedown_requests
type: bq.sql
connection: bigquery-default
description: |
  Grain: one row per takedown request record (Google + Lumen combined).
  Drives the "content removal activity" dashboard panel.
  Joins to dim_dates on measurement_date, dim_reasons on reason,
  dim_requestors on requestor_name, dim_platforms on product.
owner: civil-liberties-pipeline

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

-- Google Transparency: removal request summary
SELECT
    'google_requests'                           AS source,
    country,
    product                                     AS platform,
    requestor                                   AS requestor_name,
    reason,
    time_period,
    number_of_requests,
    items_requested_removal,
    items_removed_legal,
    items_removed_policy,
    NULL                                        AS item_count,
    extracted_at,
    period_date                                 AS measurement_date,
    year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.google_transparency_requests`
WHERE country = 'Kenya'
   OR cldr_territory = 'KE'

UNION ALL

-- Google Transparency: detailed product-level removals
SELECT
    'google_detailed'                           AS source,
    country_region                              AS country,
    product                                     AS platform,
    NULL                                        AS requestor_name,
    reason,
    NULL                                        AS time_period,
    total                                       AS number_of_requests,
    NULL                                        AS items_requested_removal,
    NULL                                        AS items_removed_legal,
    NULL                                        AS items_removed_policy,
    NULL                                        AS item_count,
    extracted_at,
    period_date                                 AS measurement_date,
    year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.google_transparency_detailed`
WHERE cldr_territory_code = 'KE'

UNION ALL

-- Lumen: mock takedown notices
SELECT
    'lumen'                                     AS source,
    country,
    recipient                                   AS platform,
    sender                                      AS requestor_name,
    reason,
    period                                      AS time_period,
    request_count                               AS number_of_requests,
    item_count                                  AS items_requested_removal,
    NULL                                        AS items_removed_legal,
    NULL                                        AS items_removed_policy,
    item_count,
    extracted_at,
    measurement_date,
    year
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
WHERE country = 'Kenya'
   OR country = 'KE'
