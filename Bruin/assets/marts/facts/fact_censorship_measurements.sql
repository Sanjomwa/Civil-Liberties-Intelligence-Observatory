/* @bruin
name: fact_censorship_measurements
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Daily OONI censorship measurements (Kenya only)
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - stg.ooni
@bruin */

SELECT 
    measurement_id,
    country,
    asn,
    test_name,
    input,
    start_time,
    status,
    probe_cc,
    probe_asn,
    extracted_at,
    DATE(start_time) AS measurement_date,
    test_category
FROM {{ ref('stg.ooni') }}
WHERE country = 'KE';
