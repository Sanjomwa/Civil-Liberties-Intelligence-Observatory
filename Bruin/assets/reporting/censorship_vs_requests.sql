/* @bruin
name: view.censorship_vs_requests
type: duckdb.sql
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: View comparing censorship measurements (OONI) with takedown requests (Google + Lumen)
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
    - name: censorship_tests
      type: INTEGER
      description: Number of censorship measurements (OONI)
    - name: takedown_requests
      type: INTEGER
      description: Number of takedown requests (Google Transparency)
    - name: lumen_requests
      type: INTEGER
      description: Number of takedown requests (Lumen)
    - name: total_requests
      type: INTEGER
      description: Combined takedown requests (Google + Lumen)
    - name: censorship_to_request_ratio
      type: FLOAT
      description: Ratio of censorship tests to takedown requests
@bruin */

SELECT
    country,
    period,
    half_year_label,
    COALESCE(censorship_tests, 0) AS censorship_tests,
    COALESCE(takedown_requests, 0) AS takedown_requests,
    COALESCE(lumen_requests, 0) AS lumen_requests,
    COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0) AS total_requests,
    CASE 
        WHEN (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) > 0
        THEN ROUND(censorship_tests::FLOAT / (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)), 2)
        ELSE NULL
    END AS censorship_to_request_ratio
FROM mart.civil_liberties
WHERE censorship_tests IS NOT NULL;
