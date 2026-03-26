/* @bruin
name: stg.google_transparency
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned Google Transparency requests (both summary and detailed)
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - raw.google_transparency_requests
  - raw.google_transparency_detailed

columns:
  - name: country
    type: STRING
    description: Country issuing request
  - name: product
    type: STRING
    description: Google product targeted
  - name: reason
    type: STRING
    description: Reason for takedown
  - name: time_period
    type: STRING
    description: Reporting period
  - name: number_of_requests
    type: INTEGER
    description: Number of requests
  - name: items_requested_removal
    type: INTEGER
    description: Items requested for removal
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin */

SELECT
    country,
    product,
    reason,
    time_period,
    number_of_requests,
    items_requested_removal,
    extracted_at
FROM google_transparency_requests

UNION ALL

SELECT
    country_region AS country,
    product,
    reason,
    period_ending AS time_period,
    total AS number_of_requests,
    NULL AS items_requested_removal,
    extracted_at
FROM google_transparency_detailed;
