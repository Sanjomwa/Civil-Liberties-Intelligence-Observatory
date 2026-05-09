/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_requests
type: bq.sql
connection: bigquery-default

description: |
  Unified takedown request fact across Google + Lumen.

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    source,
    'Kenya' AS country,
    'KE' AS iso2,

    platform,
    requestor_name,
    reason,
    time_period,

    number_of_requests,
    items_requested_removal,
    items_removed_legal,
    items_removed_policy,
    item_count,

    extracted_at,
    measurement_date,
    year

FROM (

    SELECT
        'google_requests' AS source,
        product AS platform,
        requestor AS requestor_name,
        reason,
        time_period,
        number_of_requests,
        items_requested_removal,
        items_removed_legal,
        items_removed_policy,
        NULL AS item_count,
        extracted_at,
        period_date AS measurement_date,
        year
    FROM `encoded-joy-485413-k5.stg.google_transparency_requests`

    UNION ALL

    SELECT
        'google_detailed',
        product,
        NULL,
        reason,
        NULL,
        total,
        NULL,
        NULL,
        NULL,
        NULL,
        extracted_at,
        period_date,
        year
    FROM `encoded-joy-485413-k5.stg.google_transparency_detailed`

    UNION ALL

    SELECT
        'lumen',
        recipient,
        sender,
        reason,
        period,
        request_count,
        NULL,
        NULL,
        NULL,
        item_count,
        extracted_at,
        measurement_date,
        year
    FROM `encoded-joy-485413-k5.stg.lumen_requests`

)