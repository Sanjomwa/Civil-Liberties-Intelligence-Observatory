/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_measurements
type: bq.sql
connection: bigquery-default
description: One row per OONI measurement in Kenya.
owner: civil-liberties-pipeline
depends:
  - stg.ooni
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  measurement_id,
  country,
  asn,
  test_name,
  input AS tested_url_or_app,
  start_time,
  status,
  probe_cc,
  probe_asn,
  extracted_at,
  measurement_date,
  test_category,
  year,
  month,
  CASE WHEN status IN ('anomaly', 'confirmed', 'failure') THEN TRUE ELSE FALSE END AS is_blocked,
  CASE WHEN status = 'confirmed' THEN TRUE ELSE FALSE END AS is_confirmed_block
FROM `encoded-joy-485413-k5.stg.ooni`
WHERE probe_cc = 'KE';
