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

description: Cleaned ACLED conflict events with derived fields
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - load.acled_conflict_events_to_gcs
@bruin */

WITH raw AS (
    SELECT
        id AS event_id,
        week,
        region,
        country,
        admin1,
        event_type,
        sub_event_type,
        events,
        fatalities,
        population_exposure,
        disorder_type,
        centroid_latitude,
        centroid_longitude,
        extracted_at,
        -- Derived fields for easier analysis
        PARSE_DATE('%d-%B-%Y', week) AS measurement_date,
        EXTRACT(YEAR FROM PARSE_DATE('%d-%B-%Y', week)) AS year
    FROM {{ ref('load.acled_conflict_events_to_gcs') }}
)

SELECT * FROM raw;