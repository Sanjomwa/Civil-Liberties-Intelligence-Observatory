/* @bruin
name: stg.ooni
type: bq.sql
connection: bigquery-default
depends:
  - load.ooni_to_gcs
materialization:
  type: table
  strategy: create+replace
@bruin */
WITH raw AS (

    SELECT
        measurement_id,
        probe_cc AS country,
        asn,
        probe_asn,
        test_name,
        input,

        -- FIX: universal timestamp safety
        TIMESTAMP(start_time) AS start_time,

        extracted_at,

        telegram_http_blocking,
        telegram_tcp_blocking,

        signal_backend_failure,

        whatsapp_endpoints_blocked,
        whatsapp_endpoints_dns_inconsistent,
        whatsapp_web_failure,

        tor_or_port_accessible,
        tor_obfs4_accessible,

        psiphon_failure,

        is_blocked,
        is_confirmed_block,
        has_measurement_failure,
        blocking_signal_type,

        -- SAFE DERIVATIONS
        DATE(TIMESTAMP(start_time)) AS measurement_date,
        EXTRACT(YEAR FROM TIMESTAMP(start_time)) AS year,
        EXTRACT(MONTH FROM TIMESTAMP(start_time)) AS month

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
    WHERE probe_cc = 'KE'
)

SELECT * FROM raw;