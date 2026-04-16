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
        probe_cc                                            AS country,
        asn,
        test_name,
        input,

        -- --- FIX: ns → µs → TIMESTAMP ---
        TIMESTAMP_MICROS(CAST(start_time / 1000 AS INT64))  AS start_time,

        probe_cc,
        probe_asn,
        extracted_at,

        telegram_http_blocking,
        telegram_tcp_blocking,
        signal_backend_failure,
        whatsapp_endpoints_blocked,
        whatsapp_endpoints_dns_inconsistent,
        whatsapp_web_failure,
        tor_dir_port_accessible,
        tor_obfs4_accessible,
        tor_or_port_accessible,
        psiphon_failure,

        is_blocked,
        is_confirmed_block,
        has_measurement_failure,
        blocking_signal_type,

        -- --- derived time ---
        DATE(TIMESTAMP_MICROS(CAST(start_time / 1000 AS INT64))) AS measurement_date,
        EXTRACT(YEAR  FROM TIMESTAMP_MICROS(CAST(start_time / 1000 AS INT64))) AS year,
        EXTRACT(MONTH FROM TIMESTAMP_MICROS(CAST(start_time / 1000 AS INT64))) AS month,

        CASE
            WHEN test_name IN ('web_connectivity', 'dnscheck', 'http_requests')
                THEN 'Website/DNS Blocking'
            WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal')
                THEN 'Messaging App Blocking'
            WHEN test_name IN ('tor', 'psiphon', 'lantern')
                THEN 'Circumvention Tool Blocking'
            ELSE 'Other'
        END                                                 AS test_category,

        CASE
            WHEN is_confirmed_block                         THEN 'Confirmed'
            WHEN is_blocked AND NOT is_confirmed_block      THEN 'Probable'
            WHEN has_measurement_failure AND NOT is_blocked THEN 'Disruption'
            ELSE 'OK'
        END                                                 AS blocking_confidence

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
    WHERE probe_cc = 'KE'
)

SELECT * FROM raw