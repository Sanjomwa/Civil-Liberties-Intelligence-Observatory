/* @bruin
name: fact_conflict_events
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: ACLED conflict and protest events filtered to Kenya
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - stg.acled_conflict_events
@bruin */

SELECT 
    event_id,
    measurement_date,
    region,
    admin1,
    event_type,
    sub_event_type,
    events,
    fatalities,
    population_exposure,
    disorder_type,
    centroid_latitude,
    centroid_longitude,
    extracted_at
FROM {{ ref('stg.acled_conflict_events') }}
WHERE country = 'Kenya';
