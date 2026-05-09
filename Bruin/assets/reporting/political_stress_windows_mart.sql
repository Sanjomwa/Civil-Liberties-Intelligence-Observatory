/* @bruin
tags:
  - reporting

name: reporting.mart_political_stress_windows
type: bq.sql
connection: bigquery-default

description: |
  Detects elevated digital pressure windows during Kenyan political stress periods.

depends:
  - marts.fact_country_pressure_daily
  - marts.fact_network_blocking_daily
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH network AS (

    SELECT
        measurement_date,

        AVG(blocking_rate) AS avg_blocking_rate,
        AVG(confidence_weighted_blocking)
            AS weighted_blocking

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country='Kenya'

    GROUP BY measurement_date
),

base AS (

    SELECT
        d.date_key,

        COALESCE(c.composite_pressure_score,0)
            AS country_pressure,

        COALESCE(n.avg_blocking_rate,0)
            AS blocking_rate,

        COALESCE(n.weighted_blocking,0)
            AS weighted_blocking

    FROM `encoded-joy-485413-k5.marts.dim_dates` d

    LEFT JOIN
        `encoded-joy-485413-k5.marts.fact_country_pressure_daily` c
        ON d.date_key=c.measurement_date

    LEFT JOIN network n
        ON d.date_key=n.measurement_date
),

scored AS (

    SELECT
        *,

        ROUND(
            country_pressure
          + (blocking_rate * 5)
          + (weighted_blocking * 4),
            4
        ) AS stress_score

    FROM base
),

windowed AS (

    SELECT
        *,

        AVG(stress_score)
        OVER(
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) baseline

    FROM scored
)

SELECT
    *,

    stress_score-baseline
        AS pressure_delta,

    CASE
        WHEN stress_score>=8
            THEN 'CRITICAL'

        WHEN stress_score>=5
            THEN 'HIGH'

        WHEN stress_score>=2
            THEN 'ELEVATED'

        ELSE 'NORMAL'
    END
        AS suppression_window_class

FROM windowed

ORDER BY date_key