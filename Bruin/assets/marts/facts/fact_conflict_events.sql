/* @bruin
name: fact.conflict_events
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Fact table for ACLED conflict events
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
    - name: event_count
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
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp

custom_checks:
    - name: valid_period_range
      description: Ensure events fall within Jun 2023–Jun 2025
      query: "SELECT COUNT(*) FROM fact.conflict_events WHERE period < '2023-06' OR period > '2025-06'"
      value: 0
@bruin */

SELECT
    c.country,
    a.admin1,
    e.event_type,
    a.fatalities,
    a.event_count,
    a.year,
    a.month,
    a.period,
    a.half_year_label,
    a.extracted_at
FROM stg.acled a
JOIN dims.country c
  ON LOWER(TRIM(a.country)) = LOWER(TRIM(c.country_code))
JOIN dims.event_type e
  ON LOWER(TRIM(a.event_type)) = LOWER(TRIM(e.event_type))
JOIN dims.periods p
  ON a.period = p.period;
