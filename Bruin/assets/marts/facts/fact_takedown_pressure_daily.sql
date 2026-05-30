/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_pressure_daily
type: bq.sql
connection: bigquery-default

description: |
  Unified daily takedown pressure aggregation across all
  available takedown providers (Google, optional Lumen).

  Grain:
    source × measurement_date

  Supports client deployments where Lumen may be absent
  without breaking downstream reporting marts.

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

        SAFE_DIVIDE(
            SUM(
                pressure_score * number_of_requests
            ),
            NULLIF(
                SUM(number_of_requests),
                0
            )
        ) AS pressure_score

    FROM `{{ var.project_id }}.marts.fact_takedown_activity`

    GROUP BY
        source,
        measurement_date
)

SELECT
    source,
    measurement_date,

    EXTRACT(YEAR FROM measurement_date) AS year,
    EXTRACT(MONTH FROM measurement_date) AS month,

    FORMAT_DATE(
        '%Y-%m',
        measurement_date
    ) AS year_month,

    total_requests,
    total_items_targeted,

    ROUND(
        pressure_score,
        4
    ) AS pressure_score,

    CASE
        WHEN pressure_score >= 9
            THEN 'CRITICAL'

        WHEN pressure_score >= 7
            THEN 'HIGH'

        WHEN pressure_score >= 5
            THEN 'MODERATE'

        ELSE 'LOW'
    END AS pressure_band,

    SUM(total_requests)
        OVER (
            PARTITION BY source
            ORDER BY measurement_date
            ROWS BETWEEN UNBOUNDED PRECEDING
            AND CURRENT ROW
        ) AS cumulative_requests,

    AVG(pressure_score)
        OVER (
            PARTITION BY source
            ORDER BY measurement_date
            ROWS BETWEEN 29 PRECEDING
            AND CURRENT ROW
        ) AS rolling_30d_pressure,

    pressure_score
    -
    AVG(pressure_score)
        OVER (
            PARTITION BY source
            ORDER BY measurement_date
            ROWS BETWEEN 29 PRECEDING
            AND CURRENT ROW
        ) AS pressure_delta

FROM daily

ORDER BY
    source,
    measurement_date