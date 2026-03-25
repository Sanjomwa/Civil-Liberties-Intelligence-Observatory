/* @bruin
name: view.conflict_vs_takedowns
type: duckdb.sql
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: View comparing conflict events/fatalities with takedown requests
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
    - name: conflict_events
      type: INTEGER
      description: Number of conflict events (ACLED)
    - name: fatalities
      type: INTEGER
      description: Fatalities from conflict events
    - name: takedown_requests
      type: INTEGER
      description: Number of takedown requests (Google Transparency)
    - name: lumen_requests
      type: INTEGER
      description: Number of takedown requests (Lumen)
    - name: total_requests
      type: INTEGER
      description: Combined takedown requests (Google + Lumen)
    - name: conflict_to_request_ratio
      type: FLOAT
      description: Ratio of conflict events to takedown requests
@bruin */

SELECT
    country,
    period,
    half_year_label,
    conflict_events,
    fatalities,
    COALESCE(takedown_requests, 0) AS takedown_requests,
    COALESCE(lumen_requests, 0) AS lumen_requests,
    COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0) AS total_requests,
    CASE 
        WHEN (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) > 0
        THEN ROUND(conflict_events::FLOAT / (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)), 2)
        ELSE NULL
    END AS conflict_to_request_ratio
FROM mart.civil_liberties
WHERE conflict_events IS NOT NULL;
