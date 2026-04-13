/* @bruin
tags:
  - marts_bq 
name: dim_dates
type: bq.sql
connection: bigquery-default
description: |
  Master date dimension covering Jun 2023 – Jun 2025 with Kenya-relevant
  flags (protest season, reporting periods, election proximity).
  Pure SQL — no upstream dependency needed.
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH date_spine AS (
    SELECT d AS date_key
    FROM UNNEST(
        GENERATE_DATE_ARRAY(DATE '2023-06-01', DATE '2025-06-30', INTERVAL 1 DAY)
    ) AS d
)

SELECT
    date_key,
    date_key                                                            AS full_date,
    EXTRACT(YEAR  FROM date_key)                                        AS year,
    EXTRACT(MONTH FROM date_key)                                        AS month,
    EXTRACT(DAY   FROM date_key)                                        AS day,
    EXTRACT(WEEK  FROM date_key)                                        AS week_of_year,
    EXTRACT(DAYOFWEEK FROM date_key)                                    AS day_of_week,
    FORMAT_DATE('%Y-%m', date_key)                                      AS year_month,
    FORMAT_DATE('%A', date_key)                                         AS day_name,
    FORMAT_DATE('%B', date_key)                                         AS month_name,

    -- Half-year bucket used by Google Transparency and Lumen
    CASE
        WHEN EXTRACT(MONTH FROM date_key) <= 6 THEN 'Jan-Jun'
        ELSE 'Jul-Dec'
    END                                                                 AS half_year_label,

    -- Kenya protest season: finance bill protests peaked Mar–Jun and Oct–Dec
    CASE
        WHEN EXTRACT(MONTH FROM date_key) IN (3,4,5,6,10,11,12)
            THEN 'High Protest Season'
        ELSE 'Low Protest Season'
    END                                                                 AS protest_season_flag,

    -- Reporting period boundary
    CASE
        WHEN EXTRACT(MONTH FROM date_key) IN (6, 12)
            THEN 'Half-Year End'
        ELSE 'Regular'
    END                                                                 AS reporting_period_flag,

    -- Kenya 2022 general election aftermath window (Aug–Dec 2022 spills into data context)
    -- 2027 election cycle begins to heat up from mid-2025
    CASE
        WHEN date_key BETWEEN DATE '2024-08-01' AND DATE '2024-12-31'
            THEN 'Finance Bill Crisis Period'
        WHEN date_key BETWEEN DATE '2023-06-01' AND DATE '2023-08-31'
            THEN 'Post-Election Consolidation'
        ELSE 'Baseline Period'
    END                                                                 AS political_context_flag,

    -- Weekend flag (useful for protest day analysis — most protests on weekdays)
    CASE
        WHEN EXTRACT(DAYOFWEEK FROM date_key) IN (1, 7) THEN TRUE
        ELSE FALSE
    END                                                                 AS is_weekend

FROM date_spine
ORDER BY date_key
