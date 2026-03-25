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
        DATE_TRUNC('month', d)::DATE AS month_start
    FROM generate_series(
        DATE '2023-06-01',
        DATE '2025-06-01',
        INTERVAL '1 month'
    ) AS d
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY month_start) AS period_id,
        TO_CHAR(month_start, 'YYYY-MM') AS period,
        CASE
            WHEN EXTRACT(MONTH FROM month_start) BETWEEN 1 AND 6
                THEN 'Jan-Jun ' || EXTRACT(YEAR FROM month_start)
            ELSE 'Jul-Dec ' || EXTRACT(YEAR FROM month_start)
        END AS half_year_label
    FROM months
)

SELECT * FROM normalized;
