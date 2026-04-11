/* @bruin
name: dim_dates
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Master date dimension covering June 2023 – June 2025 with Kenya-relevant flags
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH dates AS (
    SELECT 
        GENERATE_DATE_ARRAY(DATE '2023-06-01', DATE '2025-06-30', INTERVAL 1 DAY) AS date_array
)

SELECT 
    d.date AS date_key,
    d.date AS full_date,
    EXTRACT(YEAR FROM d.date) AS year,
    EXTRACT(MONTH FROM d.date) AS month,
    EXTRACT(DAY FROM d.date) AS day,
    FORMAT_DATE('%Y-%m', d.date) AS year_month,
    CASE WHEN EXTRACT(MONTH FROM d.date) <= 6 THEN 'Jan-Jun' ELSE 'Jul-Dec' END AS half_year,
    -- Kenya-specific flags
    CASE 
        WHEN EXTRACT(MONTH FROM d.date) IN (3,4,5,6,10,11,12) THEN 'High Protest Season'
        ELSE 'Low Protest Season'
    END AS protest_season_flag,
    CASE 
        WHEN EXTRACT(MONTH FROM d.date) = 6 OR EXTRACT(MONTH FROM d.date) = 12 THEN 'Half-Year End'
        ELSE 'Regular'
    END AS reporting_period_flag
FROM dates,
UNNEST(date_array) AS d
ORDER BY d.date;
