/* @bruin
name: stg.acled
type: duckdb.sql
connection: duckdb-acled
description: Cleaned ACLED conflict events
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: create+replace
depends:
    - raw.acled_aggregated
columns:
    - name: country
      type: STRING
      description: Country of event
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
    - name: extracted_at
      type: TIMESTAMP
      description: Pipeline extraction timestamp
@bruin */
