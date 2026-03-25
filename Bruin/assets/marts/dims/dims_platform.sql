/* @bruin
name: dims.platform
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
description: Dimension table for platforms/services targeted in takedown requests
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: create+replace
depends:
    - stg.lumen
columns:
    - name: platform
      type: STRING
      description: Platform or service name
      primary_key: true
      checks:
        - name: not_null
        - name: unique
@bruin */

SELECT DISTINCT INITCAP(TRIM(recipient)) AS platform
FROM stg.lumen
WHERE recipient IS NOT NULL;
