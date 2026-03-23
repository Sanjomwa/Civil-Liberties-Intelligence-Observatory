/* @bruin
name: dims.platform
type: sql
connection: duckdb-mart
description: Dimension table for platforms/services targeted in takedown requests
owner: civil-liberties-pipeline
materialization:
    type: table
    strategy: overwrite
depends:
    - stg.lumen
columns:
    - name: platform
      type: STRING
      description: Platform or service name
      primary_key: true
      checks: [not_null, unique]
@bruin */

SELECT DISTINCT INITCAP(TRIM(recipient)) AS platform
FROM stg.lumen
WHERE recipient IS NOT NULL;
