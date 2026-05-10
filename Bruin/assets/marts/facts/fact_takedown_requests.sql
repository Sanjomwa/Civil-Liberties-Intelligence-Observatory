/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_requests
type: bq.sql
connection: bigquery-default

description: |
  Unified daily takedown pressure fact across
  Google transparency + Lumen legal removals.

depends:
  - int.google_pressure_periodized
  - int.lumen_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    'google' AS source,
    'Kenya' AS country,
    'KE' AS iso2,

    measurement_date,

    google_requests AS number_of_requests,
    requested_items AS items_requested_removal,
    legal_removed AS items_removed_legal,
    policy_removed AS items_removed_policy,
    detailed_total AS item_count,

    google_pressure_score AS pressure_score,

    CASE
        WHEN google_pressure_score >= 5 THEN 'CRITICAL'
        WHEN google_pressure_score >= 4 THEN 'HIGH'
        WHEN google_pressure_score >= 3 THEN 'MODERATE'
        ELSE 'LOW'
    END AS pressure_band,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM `encoded-joy-485413-k5.int.google_pressure_periodized`

UNION ALL

SELECT
    'lumen',
    'Kenya',
    'KE',

    measurement_date,

    request_count,
    NULL,
    NULL,
    NULL,
    item_count,

    lumen_pressure_score,

    CASE
        WHEN lumen_pressure_score >= 5 THEN 'CRITICAL'
        WHEN lumen_pressure_score >= 4 THEN 'HIGH'
        WHEN lumen_pressure_score >= 3 THEN 'MODERATE'
        ELSE 'LOW'
    END,

    CURRENT_TIMESTAMP()

FROM `encoded-joy-485413-k5.int.lumen_pressure_daily`