/* @bruin
tags:
  - marts_bq
name: marts.dim_dates
type: bq.sql
connection: bigquery-default

description: |
  Canonical date dimension covering June 2023 through June 2025
  for temporal analysis across observability marts.

owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH date_spine AS (

    SELECT d AS date_key
    FROM UNNEST(
        GENERATE_DATE_ARRAY(
            DATE '2023-06-01',
            DATE '2025-06-30',
            INTERVAL 1 DAY
        )
    ) AS d

)

SELECT
    date_key,
    date_key AS full_date,

    EXTRACT(YEAR FROM date_key) AS year,
    EXTRACT(QUARTER FROM date_key) AS quarter,
    EXTRACT(MONTH FROM date_key) AS month,
    EXTRACT(DAY FROM date_key) AS day,

    EXTRACT(ISOWEEK FROM date_key) AS iso_week_of_year,
    EXTRACT(DAYOFWEEK FROM date_key) AS day_of_week,

    FORMAT_DATE('%Y-%m', date_key) AS year_month,
    FORMAT_DATE('%Y-Q%Q', date_key) AS year_quarter,

    FORMAT_DATE('%A', date_key) AS day_name,
    FORMAT_DATE('%B', date_key) AS month_name,

    CASE
        WHEN EXTRACT(MONTH FROM date_key) <= 6 THEN 'H1'
        ELSE 'H2'
    END AS half_year,

    CASE
        WHEN EXTRACT(DAYOFWEEK FROM date_key) IN (1,7)
        THEN TRUE
        ELSE FALSE
    END AS is_weekend,

    CASE
        WHEN date_key = CURRENT_DATE()
        THEN TRUE
        ELSE FALSE
    END AS is_current_date,

    DATE_TRUNC(date_key, MONTH) AS month_start,
    DATE_TRUNC(date_key, QUARTER) AS quarter_start,
    DATE_TRUNC(date_key, YEAR) AS year_start

FROM date_spine
ORDER BY date_key