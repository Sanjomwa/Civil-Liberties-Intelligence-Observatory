/* @bruin
name: fact_censorship_impact
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Bridge table linking censorship measurements with conflict events (the observatory core)
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - fact_censorship_measurements
  - fact_conflict_events
@bruin */

SELECT 
    c.measurement_id,
    c.measurement_date,
    c.test_name,
    c.test_category,
    c.status AS censorship_status,
    c.input AS blocked_domain_or_app,
    e.event_id,
    e.event_type,
    e.sub_event_type,
    e.fatalities,
    e.region,
    e.admin1,
    e.disorder_type,
    e.population_exposure,
    c.extracted_at
FROM {{ ref('fact_censorship_measurements') }} c
LEFT JOIN {{ ref('fact_conflict_events') }} e
    ON DATE(c.start_time) = e.measurement_date
    AND c.country = e.country;
