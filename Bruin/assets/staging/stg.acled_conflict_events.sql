/* @bruin
name: stg.acled_conflict_events
type: duckdb.sql
connection: duckdb-parquet

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
  - load.acled_conflict_events_to_gcs
@bruin */

WITH raw AS (
    SELECT
        event_id,
        event_date,
        country,
        event_type,
        fatalities,
        extracted_at,
        DATE(event_date) AS measurement_date,
        EXTRACT(YEAR FROM event_date) AS year
    FROM {{ ref('load.acled_conflict_events_to_gcs') }}
)

SELECT * FROM raw;
