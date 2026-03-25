/* @bruin
name: view.top_platforms_requests
type: duckdb.sql
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: View ranking platforms by takedown requests (Google + Lumen)
owner: civil-liberties-pipeline

materialization:
    type: view

depends:
    - mart.civil_liberties

columns:
    - name: country
      type: STRING
      description: Standardized country name
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
    - name: half_year_label
      type: STRING
      description: Human-readable half-year label
    - name: platform
      type: STRING
      description: Platform targeted in requests
    - name: total_requests
      type: INTEGER
      description: Combined takedown requests (Google + Lumen)
    - name: rank
      type: INTEGER
      description: Rank of platform by total requests within country/period
@bruin */

SELECT
    country,
    period,
    half_year_label,
    platform,
    COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0) AS total_requests,
    RANK() OVER (
        PARTITION BY country, period
        ORDER BY COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0) DESC
    ) AS rank
FROM mart.civil_liberties
WHERE platform IS NOT NULL;
