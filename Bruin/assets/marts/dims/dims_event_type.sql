/* @bruin
name: dims.event_type
type: sql
connection: duckdb-mart
description: Dimension table for ACLED conflict event types
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.acled
columns:
    - name: event_type
      type: STRING
      description: Conflict event type
      primary_key: true
      checks: [not_null, unique]
@bruin */

SELECT DISTINCT INITCAP(TRIM(event_type)) AS event_type
FROM stg.acled
WHERE event_type IS NOT NULL;
