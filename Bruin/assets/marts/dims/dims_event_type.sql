/* @bruin
name: dims.event_type
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

# For staging & prod environments, override the type
environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default
description: Dimension table for ACLED conflict event types
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: create+replace
depends:
    - stg.acled
columns:
    - name: event_type
      type: STRING
      description: Conflict event type
      primary_key: true
      checks: 
        - name: not_null
        - name: unique
@bruin */

SELECT DISTINCT INITCAP(TRIM(event_type)) AS event_type
FROM stg.acled
WHERE event_type IS NOT NULL;
