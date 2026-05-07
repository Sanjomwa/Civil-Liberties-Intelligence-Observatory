/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_measurements
type: bq.sql
connection: bigquery-default

description: |
  One row per OONI signal measurement (Kenya).
  Clean projection from int.ooni_signals, aligned to the current OONI schema.

owner: civil-liberties-pipeline

depends:
  - int.ooni_signals

materialization:
  type: table
  strategy: create+replace

columns:
  - name: signal_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: observation_id
    type: string
    checks:
      - name: not_null
  - name: measurement_id
    type: string
    checks:
      - name: not_null
  - name: country
    type: string
    checks:
      - name: not_null
  - name: asn
    type: string
    checks:
      - name: not_null
  - name: measurement_date
    type: date
    checks:
      - name: not_null
@bruin */

SELECT
  signal_id,
  observation_id,
  measurement_id,

  country,
  COALESCE(CAST(probe_asn AS STRING), 'UNKNOWN') AS asn,
  probe_asn,
  probe_network_name,

  test_name,
  test_version,
  input AS tested_entity,
  protocol,
  observation_target,

  endpoint_ip,
  endpoint_port,

  start_time,
  measurement_date,
  DATE_TRUNC(measurement_date, MONTH) AS month_date,
  FORMAT_DATE('%Y-%m', measurement_date) AS year_month,

  year,
  month,
  day,

  result_state,
  is_blocked,
  blocking_signal_type,
  blocking_confidence,
  failure_reason,
  confidence_score,

  int_extracted_at

FROM `encoded-joy-485413-k5.int.ooni_signals`
WHERE country = 'KE';