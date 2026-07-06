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
  # TD-58 (2026-07-06): this is the 61.5 GiB raw table whose missing
  # clustering made every ad-hoc raw_test_keys scan bill the full column
  # (even LIMIT 3 billed 30 GiB). Partitioning by measurement_date enables
  # date-pruned scans and any future incremental conversion; clustering by
  # (country, test_name) prunes the test-type-filtered diagnostic queries
  # (dnscheck/tor investigation was ~$1.8 of July's bill). country is
  # constant at n=1 country today but becomes the first-order pruning key
  # under multi-country expansion, at zero extra cost now.
  partition_by: measurement_date
  cluster_by:
    - country
    - test_name

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
FROM `{{ var.project_id }}.{{ var.bq_dataset }}.ooni_measurements`
WHERE probe_cc = '{{ var.iso2 }}'
  AND COALESCE(measurement_id, raw_measurement) IS NOT NULL;