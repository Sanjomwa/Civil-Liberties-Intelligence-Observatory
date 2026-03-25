/* @bruin
name: dims.reasons
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Dimension table for standardized takedown request reasons
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.google_transparency
    - stg.lumen

columns:
    - name: reason_id
      type: STRING
      description: Surrogate key for reason
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: reason_name
      type: STRING
      description: Standardized reason for takedown request
      checks:
        - name: not_null
@bruin */

WITH google_reasons AS (
    SELECT DISTINCT LOWER(TRIM(reason)) AS reason_name
    FROM stg.google_transparency
    WHERE reason IS NOT NULL
),
lumen_reasons AS (
    SELECT DISTINCT LOWER(TRIM(reason)) AS reason_name
    FROM stg.lumen
    WHERE reason IS NOT NULL
),
unioned AS (
    SELECT reason_name FROM google_reasons
    UNION
    SELECT reason_name FROM lumen_reasons
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY reason_name) AS reason_id,
        INITCAP(reason_name) AS reason_name
    FROM unioned
)

SELECT * FROM normalized;
