/* @bruin
name: mart.civil_liberties
type: sql
connection: duckdb-mart
description: Unified mart combining censorship tests, conflict events,
             takedown requests, and Lumen platform requests for civil liberties analysis
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - fact.censorship_tests
    - fact.conflict_events
    - fact.takedown_requests
    - fact.lumen_platforms
    - dims.country
    - dims.platform
    - dims.event_type
columns:
    - name: country
      type: STRING
      description: Standardized country name
      checks:
        - name: not_null
    - name: censorship_tests
      type: INTEGER
      description: Number of censorship measurements
    - name: blocked_pct
      type: FLOAT
      description: Percentage of blocked/anomaly tests
      checks:
        - name: between_0_and_1
    - name: conflict_events
      type: INTEGER
      description: Number of conflict events
      checks:
        - name: non_negative
    - name: fatalities
      type: INTEGER
      description: Fatalities reported in conflict events
      checks:
        - name: non_negative
    - name: takedown_requests
      type: INTEGER
      description: Number of takedown requests (Google Transparency)
      checks:
        - name: non_negative
    - name: items_requested
      type: INTEGER
      description: Number of items requested for removal
      checks:
        - name: non_negative
    - name: lumen_requests
      type: INTEGER
      description: Number of Lumen requests (platform + legal)
      checks:
        - name: non_negative
    - name: platforms_targeted
      type: STRING
      description: Platforms targeted in Lumen requests
@bruin */

WITH censorship AS (
    SELECT country,
           COUNT(*) AS censorship_tests,
           SUM(CASE WHEN status IN ('blocked','anomaly') THEN 1 ELSE 0 END) * 1.0 / COUNT(*) AS blocked_pct
    FROM fact.censorship_tests
    GROUP BY country
),
conflict AS (
    SELECT country,
           SUM(event_count) AS conflict_events,
           SUM(fatalities) AS fatalities
    FROM fact.conflict_events
    GROUP BY country
),
takedowns AS (
    SELECT country,
           SUM(request_count) AS takedown_requests,
           SUM(item_count) AS items_requested
    FROM fact.takedown_requests
    GROUP BY country
),
lumen AS (
    SELECT country,
           COUNT(*) AS lumen_requests,
           ARRAY_TO_STRING(ARRAY_AGG(DISTINCT platform_id), ', ') AS platforms_targeted
    FROM fact.lumen_platforms
    GROUP BY country
)

SELECT
    c.country,
    ce.censorship_tests,
    ce.blocked_pct,
    cf.conflict_events,
    cf.fatalities,
    td.takedown_requests,
    td.items_requested,
    lu.lumen_requests,
    lu.platforms_targeted
FROM dims.country c
LEFT JOIN censorship ce ON c.country = ce.country
LEFT JOIN conflict cf ON c.country = cf.country
LEFT JOIN takedowns td ON c.country = td.country
LEFT JOIN lumen lu ON c.country = lu.country;
