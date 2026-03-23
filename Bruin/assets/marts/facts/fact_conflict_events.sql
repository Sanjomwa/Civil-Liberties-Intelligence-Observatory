/* @bruin
name: fact.conflict_events
type: sql
connection: duckdb-mart
description: Fact table for ACLED conflict events
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.acled
    - dims.country
columns:
    - name: country
      type: STRING
      description: Standardized country name
      checks: [not_null]
    - name: admin1
      type: STRING
      description: First-level administrative division
    - name: event_type
      type: STRING
      description: Type of conflict event
      checks: [not_null]
    - name: fatalities
      type: INTEGER
      description: Number of fatalities
      checks: [non_negative]
    - name: event_count
      type: INTEGER
      description: Number of events aggregated
      checks: [non_negative]
    - name: year
      type: INTEGER
      description: Event year
      checks: [not_null]
    - name: month
      type: INTEGER
      description: Event month
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */

SELECT
    c.country,
    a.admin1,
    a.event_type,
    a.fatalities,
    a.event_count,
    a.year,
    a.month,
    a.extracted_at
FROM stg.acled a
JOIN dims.country c
  ON LOWER(TRIM(a.country)) = LOWER(TRIM(c.country));
