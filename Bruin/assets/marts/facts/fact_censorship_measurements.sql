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
  anomaly,
  confirmed,
  failure,
  probe_cc,
  probe_asn,
  extracted_at,
  measurement_date,
  test_category,
  year,
  month,
  CASE
    WHEN confirmed THEN TRUE
    WHEN anomaly THEN TRUE
    ELSE FALSE
  END AS is_blocked,
  confirmed AS is_confirmed_block,
  failure AS has_measurement_failure
FROM `encoded-joy-485413-k5.stg.ooni`
WHERE probe_cc = 'KE';
