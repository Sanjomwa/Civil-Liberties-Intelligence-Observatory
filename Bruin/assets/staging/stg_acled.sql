/* @bruin
name: stg.acled
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-acled

# For staging & prod environments, override the type
environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default
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
