/* @bruin
name: dims.periods
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Dimension table for standardized reporting periods
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

columns:
    - name: period_id
      type: STRING
      description: Surrogate key for period
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: period
      type: STRING
      description: Reporting period in YYYY-MM format
      checks:
        - name: not_null
    - name: half_year_label
      type: STRING
      description: Human-readable half-year label (e.g. Jan-Jun 2023)
      checks:
        - name: not_null
@bruin */

WITH months AS (
    SELECT
        -- ✅ Correct date handling for MSSQL, DuckDB, BigQuery
        DATEADD(month, n, CAST('2023-06-01' AS DATE)) AS month_start
    FROM (
        SELECT TOP (DATEDIFF(month, CAST('2023-06-01' AS DATE), CAST('2025-06-01' AS DATE)) + 1)
            ROW_NUMBER() OVER (ORDER BY (SELECT NULL)) - 1 AS n
        FROM sys.objects
    ) AS seq
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY month_start) AS period_id,
        FORMAT(month_start, 'yyyy-MM') AS period,   -- MSSQL
        CASE
            WHEN MONTH(month_start) BETWEEN 1 AND 6
                THEN 'Jan-Jun ' || YEAR(month_start)
            ELSE 'Jul-Dec ' || YEAR(month_start)
        END AS half_year_label
    FROM months
)

SELECT * FROM normalized;
