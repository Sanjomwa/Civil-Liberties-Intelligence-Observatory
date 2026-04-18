/* @bruin
tags:
  - staging_bq
  - dataset_ooni_measurements
name: stg.ooni_measurements
type: bq.sql
connection: bigquery-default

depends:
  - load.ooni_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    measurement_id,
    probe_cc AS country,
    asn,
    probe_asn,
    test_name,
    input,
    SAFE_CAST(start_time AS TIMESTAMP) AS start_time,
    extracted_at,

    telegram_http_blocking,
    telegram_tcp_blocking,
    signal_backend_failure,
    whatsapp_endpoints_blocked,
    whatsapp_web_failure,
    tor_or_port_accessible,
    tor_obfs4_accessible,
    psiphon_failure,

    DATE(SAFE_CAST(start_time AS TIMESTAMP)) AS measurement_date,
    EXTRACT(YEAR FROM SAFE_CAST(start_time AS TIMESTAMP)) AS year,
    EXTRACT(MONTH FROM SAFE_CAST(start_time AS TIMESTAMP)) AS month,
    EXTRACT(DAY FROM SAFE_CAST(start_time AS TIMESTAMP)) AS day

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
WHERE probe_cc = 'KE';