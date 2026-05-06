/* @bruin
name: stg.ooni_measurements
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements

description: |
  Base OONI measurement staging table.
  Grain: one row per raw OONI measurement. This table keeps metadata and raw
  JSON only; protocol observations are generated in separate staging assets.

depends:
  - load.ooni_to_gcs

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: country
    type: string
    checks:
      - name: not_null
  - name: test_name
    type: string
    checks:
      - name: not_null
  - name: measurement_start_time
    type: timestamp
    checks:
      - name: not_null
  - name: measurement_date
    type: date
    checks:
      - name: not_null
@bruin */

SELECT
  COALESCE(
    measurement_id,
    TO_HEX(SHA256(CONCAT(
      IFNULL(source_file, ''),
      '|',
      IFNULL(report_id, ''),
      '|',
      IFNULL(raw_measurement, '')
    )))
  ) AS measurement_id,
  report_id,
  input,
  probe_cc AS country,
  probe_asn,
  probe_network_name,
  test_name,
  test_version,
  SAFE_CAST(measurement_start_time AS TIMESTAMP) AS measurement_start_time,
  SAFE_CAST(test_start_time AS TIMESTAMP) AS test_start_time,
  DATE(SAFE_CAST(measurement_date AS DATE)) AS measurement_date,
  failure,
  source_file,
  SAFE_CAST(extracted_at AS TIMESTAMP) AS extracted_at,
  raw_test_keys,
  raw_measurement
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
WHERE probe_cc = 'KE'
  AND COALESCE(measurement_id, raw_measurement) IS NOT NULL;