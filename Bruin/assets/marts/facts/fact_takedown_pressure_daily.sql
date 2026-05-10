/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_pressure_daily
type: bq.sql
connection: bigquery-default

depends:
  - marts.fact_takedown_activity

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH daily AS (

    SELECT
        source,
        measurement_date,

        SUM(number_of_requests) AS total_requests,
        SUM(item_count) AS total_items_targeted,
        AVG(pressure_score) AS pressure_score

    FROM `encoded-joy-485413-k5.marts.fact_takedown_activity`
    GROUP BY source, measurement_date
)

SELECT
    source,

    measurement_date,

    EXTRACT(YEAR FROM measurement_date) AS year,
    EXTRACT(MONTH FROM measurement_date) AS month,

    FORMAT_DATE('%Y-%m', measurement_date)
        AS year_month,

    total_requests,
    total_items_targeted,

    ROUND(pressure_score,4) AS pressure_score,

    CASE
        WHEN pressure_score >= 9 THEN 'CRITICAL'
        WHEN pressure_score >= 7 THEN 'HIGH'
        WHEN pressure_score >= 5 THEN 'MODERATE'
        ELSE 'LOW'
    END AS pressure_band,

    SUM(total_requests)
        OVER (
            PARTITION BY source
            ORDER BY measurement_date
        ) AS cumulative_requests

FROM daily
ORDER BY source, measurement_date