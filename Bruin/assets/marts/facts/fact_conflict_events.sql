/* @bruin
name: fact.conflict_events
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Fact table for ACLED conflict events with coordinates
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.acled
    - dims.country
    - dims.event_type
    - dims.periods

columns:
    - name: surrogate_id
      type: INTEGER
      description: Unique surrogate identifier from staging
      primary_key: true
    - name: country
      type: STRING
      description: Standardized country name
      checks:
        - name: not_null
    - name: admin1
      type: STRING
      description: First-level administrative division
    - name: event_type
      type: STRING
      description: Type of conflict event
      checks:
        - name: not_null
    - name: fatalities
      type: INTEGER
      description: Number of fatalities
      checks:
        - name: non_negative
    - name: events
      type: INTEGER
      description: Number of events aggregated
      checks:
        - name: non_negative
    - name: year
      type: INTEGER
      description: Event year
      checks:
        - name: not_null
    - name: month
      type: INTEGER
      description: Event month
    - name: period
      type: STRING
      description: Reporting period (YYYY-MM)
      checks:
        - name: not_null
    - name: half_year_label
      type: STRING
      description: Human-readable half-year (e.g. Jan-Jun 2023)
    - name: centroid_latitude
      type: FLOAT
      description: Latitude of event centroid
    - name: centroid_longitude
      type: FLOAT
      description: Longitude of event centroid
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp

custom_checks:
    - name: valid_period_range
      description: Ensure events fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM fact.conflict_events WHERE period < '2023-06' OR period > '2025-06'"
      value: 0
@bruin */

WITH base AS (
    SELECT
        surrogate_id,
        country,
        admin1,
        event_type,
        fatalities,
        events,
        CAST(week AS DATE) AS week,
        EXTRACT(YEAR FROM week) AS year,
        EXTRACT(MONTH FROM week) AS month,
        strftime(week, '%Y-%m') AS period,
        CASE
            WHEN EXTRACT(MONTH FROM week) BETWEEN 1 AND 6
                 THEN 'Jan-Jun ' || EXTRACT(YEAR FROM week)
            ELSE 'Jul-Dec ' || EXTRACT(YEAR FROM week)
        END AS half_year_label,
        centroid_latitude,
        centroid_longitude,
        extracted_at
    FROM stg.acled
    WHERE week BETWEEN DATE '2023-06-01' AND DATE '2025-06-30'
)

SELECT
    c.country,
    b.admin1,
    e.event_type,
    b.fatalities,
    b.events,
    b.year,
    b.month,
    b.period,
    b.half_year_label,
    b.centroid_latitude,
    b.centroid_longitude,
    b.extracted_at,
    b.surrogate_id
FROM base b
JOIN dims.country c
  ON LOWER(TRIM(b.country)) = LOWER(TRIM(c.country_code))
JOIN dims.event_type e
  ON LOWER(TRIM(b.event_type)) = LOWER(TRIM(e.event_type))
JOIN dims.periods p
  ON b.period = p.period;
