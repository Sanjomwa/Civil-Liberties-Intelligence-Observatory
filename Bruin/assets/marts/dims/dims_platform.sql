/* @bruin
name: dims.platform
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-parquet

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
    - stg.google_transparency

columns:
    - name: platform_id
      type: STRING
      description: Surrogate key for platform
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: platform_name
      type: STRING
      description: Cleaned platform/service name
      checks:
        - name: not_null
@bruin */

WITH lumen_platforms AS (
    SELECT DISTINCT LOWER(TRIM(recipient)) AS platform_name
    FROM stg.lumen
    WHERE recipient IS NOT NULL
),
google_platforms AS (
    SELECT DISTINCT LOWER(TRIM(product)) AS platform_name
    FROM stg.google_transparency
    WHERE product IS NOT NULL
),
unioned AS (
    SELECT platform_name FROM lumen_platforms
    UNION
    SELECT platform_name FROM google_platforms
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY platform_name) AS platform_id,
        INITCAP(platform_name) AS platform_name
    FROM unioned
)

SELECT * FROM normalized;
