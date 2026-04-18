/* @bruin
name: int.ooni_signals
type: bq.sql
connection: bigquery-default
depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT *
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_ooni_measurements`
),

normalized AS (

    SELECT
        measurement_id,
        country,
        asn,
        probe_asn,
        test_name,
        input,
        start_time,

        -- =========================
        -- SIGNAL TYPE MAPPING
        -- =========================
        CASE
            WHEN test_name LIKE '%telegram%' THEN 'telegram'
            WHEN test_name LIKE '%whatsapp%' THEN 'whatsapp'
            WHEN test_name LIKE '%signal%' THEN 'signal'
            WHEN test_name LIKE '%tor%' THEN 'tor'
            WHEN test_name LIKE '%psiphon%' THEN 'psiphon'
            ELSE 'unknown'
        END AS signal_type,

        -- =========================
        -- TELEGRAM
        -- =========================
        telegram_http_blocking,
        telegram_tcp_blocking,

        CASE
            WHEN telegram_http_blocking = TRUE
              OR telegram_tcp_blocking = TRUE THEN TRUE
            ELSE FALSE
        END AS telegram_block_flag,

        -- =========================
        -- WHATSAPP
        -- =========================
        whatsapp_endpoints_blocked,
        whatsapp_endpoints_dns_inconsistent,
        whatsapp_web_failure,

        CASE
            WHEN whatsapp_endpoints_blocked = TRUE
              OR whatsapp_endpoints_dns_inconsistent = TRUE
              OR whatsapp_web_failure IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS whatsapp_block_flag,

        -- =========================
        -- SIGNAL
        -- =========================
        signal_backend_failure,

        CASE
            WHEN signal_backend_failure IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS signal_block_flag,

        -- =========================
        -- TOR
        -- =========================
        tor_or_port_accessible,
        tor_obfs4_accessible,

        CASE
            WHEN tor_or_port_accessible = 0
             AND tor_obfs4_accessible = 0 THEN TRUE
            WHEN tor_or_port_accessible = 0
             OR tor_obfs4_accessible = 0 THEN TRUE
            ELSE FALSE
        END AS tor_block_flag,

        -- =========================
        -- PSIPHON
        -- =========================
        psiphon_failure,

        CASE
            WHEN psiphon_failure IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS psiphon_block_flag,

        -- =========================
        -- UNIFIED BLOCK SIGNAL
        -- =========================
        CASE
            WHEN telegram_http_blocking OR telegram_tcp_blocking THEN 'APP_LAYER_BLOCK'
            WHEN whatsapp_endpoints_blocked THEN 'APP_LAYER_BLOCK'
            WHEN whatsapp_endpoints_dns_inconsistent THEN 'DNS_INCONSISTENCY'
            WHEN whatsapp_web_failure IS NOT NULL THEN 'WEB_FAILURE'
            WHEN signal_backend_failure IS NOT NULL THEN 'SERVICE_FAILURE'
            WHEN tor_or_port_accessible = 0 THEN 'NETWORK_BLOCK'
            WHEN psiphon_failure IS NOT NULL THEN 'CENSORSHIP_INDICATOR'
            ELSE 'NO_SIGNAL'
        END AS blocking_signal_type,

        -- =========================
        -- BLOCK CLASSIFICATION
        -- =========================
        CASE
            WHEN telegram_http_blocking OR whatsapp_endpoints_blocked THEN TRUE
            WHEN tor_or_port_accessible = 0 AND tor_obfs4_accessible = 0 THEN TRUE
            ELSE FALSE
        END AS is_blocked,

        CASE
            WHEN telegram_http_blocking OR whatsapp_endpoints_blocked THEN 'HIGH'
            WHEN whatsapp_web_failure IS NOT NULL THEN 'MEDIUM'
            WHEN psiphon_failure IS NOT NULL THEN 'LOW'
            ELSE 'NONE'
        END AS block_confidence,

        -- =========================
        -- QUALITY SCORE (SIMPLE HEURISTIC)
        -- =========================
        (
            CASE WHEN start_time IS NULL THEN 0 ELSE 0.3 END +
            CASE WHEN input IS NULL THEN 0 ELSE 0.2 END +
            CASE WHEN test_name IS NULL THEN 0 ELSE 0.2 END +
            CASE WHEN asn IS NOT NULL THEN 0.3 ELSE 0 END
        ) AS measurement_quality_score,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
)

SELECT *
FROM normalized;
