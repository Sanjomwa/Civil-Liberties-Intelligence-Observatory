/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_trends
type: bq.sql
connection: bigquery-default

depends:
  - marts.fact_takedown_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    source,
    platform,
    reason,

    EXTRACT(YEAR FROM measurement_date) AS year,
    EXTRACT(MONTH FROM measurement_date) AS month,

    FORMAT_DATE('%Y-%m', measurement_date)
        AS year_month,

    COUNT(*) AS request_records,

    SUM(number_of_requests)
        AS total_requests,

    SUM(item_count)
        AS total_items_targeted,

    SUM(SUM(number_of_requests))
        OVER (
            PARTITION BY source, platform
            ORDER BY measurement_date
        ) AS cumulative_requests

FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`

GROUP BY
    source,
    platform,
    reason,
    year,
    month,
    year_month,
    measurement_date