/* @bruin
name: stg.ooni_measurements
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

        SAFE_CAST(start_time AS TIMESTAMP) AS start_time,
        extracted_at,

        -- test signals
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

        blocking_signal_type

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
    WHERE probe_cc = 'KE'
),

normalized AS (

    SELECT *,
    
    -- ============================
    -- OONI SIGNAL NORMALIZATION
    -- ============================

    CASE
        WHEN is_confirmed_block = TRUE THEN 'confirmed_block'
        
        WHEN is_blocked = TRUE 
             AND has_measurement_failure = FALSE 
        THEN 'suspected_block'
        
        WHEN has_measurement_failure = TRUE THEN 'network_failure'
        
        ELSE 'no_evidence'
    END AS blocking_signal,

    CASE
        WHEN is_confirmed_block THEN 'high'
        WHEN is_blocked THEN 'medium'
        ELSE 'low'
    END AS blocking_confidence,

    CASE
        WHEN test_name IN ('telegram', 'whatsapp', 'signal')
            THEN 'messaging'
        WHEN test_name IN ('tor', 'psiphon')
            THEN 'circumvention'
        ELSE 'web'
    END AS test_category

    FROM raw
)

SELECT
    *,

    -- time dimensions
    DATE(start_time) AS measurement_date,
    EXTRACT(YEAR FROM start_time) AS year,
    EXTRACT(MONTH FROM start_time) AS month,
    EXTRACT(DAY FROM start_time) AS day

FROM normalized;
