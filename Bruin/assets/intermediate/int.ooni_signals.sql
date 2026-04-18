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
        extracted_at,

        -- =========================
        -- CANONICAL SIGNAL TYPE
        -- =========================
        CASE

            -- TELEGRAM
            WHEN test_name = 'telegram'
                AND (telegram_http_blocking = TRUE OR telegram_tcp_blocking = TRUE)
                THEN 'telegram_blocking'

            -- WHATSAPP
            WHEN test_name = 'whatsapp'
                AND (
                    whatsapp_endpoints_blocked = TRUE
                    OR whatsapp_endpoints_dns_inconsistent = TRUE
                    OR whatsapp_web_failure IS NOT NULL
                )
                THEN 'whatsapp_blocking'

            -- SIGNAL
            WHEN test_name = 'signal'
                AND signal_backend_failure IS NOT NULL
                THEN 'signal_blocking'

            -- TOR
            WHEN test_name = 'tor'
                AND (
                    tor_or_port_accessible = 0
                    OR tor_obfs4_accessible = 0
                )
                THEN 'tor_blocking'

            -- PSIPHON
            WHEN test_name = 'psiphon'
                AND psiphon_failure IS NOT NULL
                THEN 'psiphon_blocking'

            ELSE 'no_blocking_signal'
        END AS blocking_signal_type,

        -- =========================
        -- UNIFIED BLOCK FLAG
        -- =========================
        CASE

            WHEN (
                telegram_http_blocking = TRUE
                OR telegram_tcp_blocking = TRUE
                OR whatsapp_endpoints_blocked = TRUE
                OR whatsapp_endpoints_dns_inconsistent = TRUE
                OR whatsapp_web_failure IS NOT NULL
                OR signal_backend_failure IS NOT NULL
                OR tor_or_port_accessible = 0
                OR tor_obfs4_accessible = 0
                OR psiphon_failure IS NOT NULL
            )
            THEN TRUE

            ELSE FALSE
        END AS is_blocked,

        -- =========================
        -- CONFIRMED BLOCK (HIGH CONFIDENCE ONLY)
        -- =========================
        CASE

            WHEN telegram_http_blocking = TRUE THEN TRUE
            WHEN whatsapp_endpoints_blocked = TRUE THEN TRUE
            WHEN tor_or_port_accessible = 0 AND tor_obfs4_accessible = 0 THEN TRUE

            ELSE FALSE
        END AS is_confirmed_block,

        -- =========================
        -- MEASUREMENT FAILURE SIGNAL
        -- =========================
        CASE
            WHEN signal_backend_failure IS NOT NULL THEN TRUE
            WHEN whatsapp_web_failure = 'timeout' THEN TRUE
            WHEN psiphon_failure IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS has_measurement_failure,

        -- =========================
        -- CONFIDENCE SCORING
        -- =========================
        CASE
            WHEN is_confirmed_block = TRUE THEN 'HIGH'
            WHEN is_blocked = TRUE THEN 'MEDIUM'
            WHEN has_measurement_failure = TRUE THEN 'LOW'
            ELSE 'NONE'
        END AS confidence_level,

        -- =========================
        -- BLOCKING VECTOR (EXPLANATION)
        -- =========================
        ARRAY_TO_STRING(ARRAY[
            IF(telegram_http_blocking, 'telegram_http', NULL),
            IF(telegram_tcp_blocking, 'telegram_tcp', NULL),
            IF(whatsapp_endpoints_blocked, 'whatsapp_endpoint', NULL),
            IF(whatsapp_endpoints_dns_inconsistent, 'whatsapp_dns', NULL),
            IF(signal_backend_failure IS NOT NULL, 'signal_backend', NULL),
            IF(tor_or_port_accessible = 0, 'tor_port', NULL),
            IF(tor_obfs4_accessible = 0, 'tor_obfs4', NULL),
            IF(psiphon_failure IS NOT NULL, 'psiphon', NULL)
        ], ',') AS blocking_vector

    FROM base
)

SELECT *
FROM normalized;
