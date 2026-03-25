/* @bruin
name: dims.event_type
type: duckdb.sql          # ← used only in 'dev' environment
connection: duckdb-mart

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Dimension table for standardized event types (conflict + censorship)
owner: civil-liberties-pipeline

materialization:
    type: table
    strategy: create+replace

depends:
    - stg.acled
    - stg.ooni

columns:
    - name: event_type_id
      type: STRING
      description: Surrogate key for event type
      primary_key: true
      checks:
        - name: not_null
        - name: unique
    - name: event_type
      type: STRING
      description: Standardized event type (conflict or censorship)
      checks:
        - name: not_null
@bruin */

WITH acled_event_types AS (
    SELECT DISTINCT LOWER(TRIM(event_type)) AS event_type
    FROM stg.acled
    WHERE event_type IS NOT NULL
),
ooni_event_types AS (
    SELECT DISTINCT LOWER(TRIM(test_name)) AS event_type
    FROM stg.ooni
    WHERE test_name IS NOT NULL
),
unioned AS (
    SELECT event_type FROM acled_event_types
    UNION
    SELECT event_type FROM ooni_event_types
),
normalized AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY event_type) AS event_type_id,
        INITCAP(event_type) AS event_type
    FROM unioned
)

SELECT * FROM normalized;
