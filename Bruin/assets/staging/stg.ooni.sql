/* @bruin
name: stg.ooni_conflict_measurements
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

        -- SAFE TIMESTAMP NORMALIZATION
        SAFE.TIMESTAMP(start_time) AS start_time,

        extracted_at,

        -- TELEGRAM
        telegram_http_blocking,
        telegram_tcp_blocking,

        -- SIGNAL
        signal_backend_failure,

        -- WHATSAPP
        whatsapp_endpoints_blocked,
        whatsapp_endpoints_dns_inconsistent,
        whatsapp_web_failure,

        -- TOR
        tor_or_port_accessible,
        tor_obfs4_accessible,

        -- PSIPHON
        psiphon_failure,

        -- RAW DERIVED FLAGS (FROM INGEST ONLY)
        is_blocked,
        is_confirmed_block,
        has_measurement_failure,
        blocking_signal_type

    FROM `encoded-joy-485413-k5.stg.ooni`
    WHERE probe_cc = 'KE'
)

SELECT
    *,
    
    -- DERIVED ANALYTICS DIMENSIONS
    DATE(start_time) AS measurement_date,
    EXTRACT(YEAR FROM start_time) AS year,
    EXTRACT(MONTH FROM start_time) AS month,
    EXTRACT(DAY FROM start_time) AS day

FROM raw;
