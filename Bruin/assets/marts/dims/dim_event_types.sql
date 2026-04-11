/* @bruin
name: dim_event_types
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: ACLED event and sub-event types
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
    event_type,
    sub_event_type
FROM {{ ref('stg.acled_conflict_events') }}
WHERE country = 'Kenya';
