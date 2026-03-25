/* @bruin
name: mart.civil_liberties
type: duckdb.sql
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Mart combining takedown requests, censorship tests, and conflict events for civil liberties analysis
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - fact.takedown_requests
    - fact.lumen_platforms
    - fact.censorship_tests
    - fact.conflict_events
    - dims.country
    - dims.platform
    - dims.event_type
    - dims.reasons
    - dims.periods

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
    - name: reason
      type: STRING
      description: Reason for takedown request
    - name: takedown_requests
      type: INTEGER
      description: Number of takedown requests (Google Transparency)
    - name: lumen_requests
      type: INTEGER
      description: Number of takedown requests (Lumen)
    - name: censorship_tests
      type: INTEGER
      description: Number of censorship measurements (OONI)
    - name: conflict_events
      type: INTEGER
      description: Number of conflict events (ACLED)
    - name: fatalities
      type: INTEGER
      description: Fatalities from conflict events
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */

WITH takedowns AS (
    SELECT country, period, half_year_label, product AS platform, reason,
           SUM(request_count) AS takedown_requests,
           SUM(item_count) AS items_requested,
           MAX(extracted_at) AS extracted_at
    FROM fact.takedown_requests
    GROUP BY country, period, half_year_label, product, reason
),
lumen AS (
    SELECT country, period, half_year_label, platform_id AS platform,
           reason, COUNT(request_id) AS lumen_requests,
           MAX(extracted_at) AS extracted_at
    FROM fact.lumen_platforms
    GROUP BY country, period, half_year_label, platform_id, reason
),
ooni AS (
    SELECT country, period, half_year_label,
           COUNT(measurement_id) AS censorship_tests,
           MAX(extracted_at) AS extracted_at
    FROM fact.censorship_tests
    GROUP BY country, period, half_year_label
),
conflict AS (
    SELECT country, period, half_year_label,
           SUM(event_count) AS conflict_events,
           SUM(fatalities) AS fatalities,
           MAX(extracted_at) AS extracted_at
    FROM fact.conflict_events
    GROUP BY country, period, half_year_label
)
SELECT
    COALESCE(t.country, l.country, o.country, c.country) AS country,
    COALESCE(t.period, l.period, o.period, c.period) AS period,
    COALESCE(t.half_year_label, l.half_year_label, o.half_year_label, c.half_year_label) AS half_year_label,
    COALESCE(t.platform, l.platform) AS platform,
    COALESCE(t.reason, l.reason) AS reason,
    t.takedown_requests,
    l.lumen_requests,
    o.censorship_tests,
    c.conflict_events,
    c.fatalities,
    GREATEST(t.extracted_at, l.extracted_at, o.extracted_at, c.extracted_at) AS extracted_at
FROM takedowns t
FULL OUTER JOIN lumen l
  ON t.country = l.country AND t.period = l.period
FULL OUTER JOIN ooni o
  ON COALESCE(t.country, l.country) = o.country AND COALESCE(t.period, l.period) = o.period
FULL OUTER JOIN conflict c
  ON COALESCE(t.country, l.country, o.country) = c.country AND COALESCE(t.period, l.period, o.period) = c.period;
