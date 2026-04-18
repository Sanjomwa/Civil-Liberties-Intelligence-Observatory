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
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
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
        measurement_date,
        year,
        month,
        day,

        -- =========================
        -- SIGNAL TYPE
        -- =========================
        CASE
            WHEN LOWER(test_name) LIKE '%telegram%' THEN 'telegram'
            WHEN LOWER(test_name) LIKE '%whatsapp%' THEN 'whatsapp'
            WHEN LOWER(test_name) LIKE '%signal%' THEN 'signal'
            WHEN LOWER(test_name) LIKE '%tor%' THEN 'tor'
            WHEN LOWER(test_name) LIKE '%psiphon%' THEN 'psiphon'
            ELSE 'unknown'
        END AS signal_type,

        -- =========================
        -- TELEGRAM
        -- =========================
        IFNULL(telegram_http_blocking, FALSE) AS telegram_http_blocking,
        IFNULL(telegram_tcp_blocking, FALSE) AS telegram_tcp_blocking,

        CASE
            WHEN IFNULL(telegram_http_blocking, FALSE)
              OR IFNULL(telegram_tcp_blocking, FALSE)
            THEN TRUE ELSE FALSE
        END AS telegram_block_flag,

        -- =========================
        -- WHATSAPP
        -- =========================
        IFNULL(whatsapp_endpoints_blocked, FALSE) AS whatsapp_endpoints_blocked,
        whatsapp_web_failure,

        CASE
            WHEN IFNULL(whatsapp_endpoints_blocked, FALSE)
              OR whatsapp_web_failure IS NOT NULL
            THEN TRUE ELSE FALSE
        END AS whatsapp_block_flag,

        -- =========================
        -- SIGNAL
        -- =========================
        signal_backend_failure,

        CASE
            WHEN signal_backend_failure IS NOT NULL
            THEN TRUE ELSE FALSE
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
            WHEN psiphon_failure IS NOT NULL
            THEN TRUE ELSE FALSE
        END AS psiphon_block_flag,

        -- =========================
        -- UNIFIED BLOCK FLAG
        -- =========================
        CASE
            WHEN (
                IFNULL(telegram_http_blocking, FALSE)
                OR IFNULL(telegram_tcp_blocking, FALSE)
                OR IFNULL(whatsapp_endpoints_blocked, FALSE)
                OR whatsapp_web_failure IS NOT NULL
                OR signal_backend_failure IS NOT NULL
                OR tor_or_port_accessible = 0
                OR tor_obfs4_accessible = 0
                OR psiphon_failure IS NOT NULL
            )
            THEN TRUE ELSE FALSE
        END AS is_blocked,

        -- =========================
        -- BLOCKING SIGNAL TYPE
        -- =========================
        CASE
            WHEN IFNULL(telegram_http_blocking, FALSE)
              OR IFNULL(telegram_tcp_blocking, FALSE)
              OR IFNULL(whatsapp_endpoints_blocked, FALSE)
                THEN 'APP_LAYER_BLOCK'

            WHEN whatsapp_web_failure IS NOT NULL
                THEN 'WEB_FAILURE'

            WHEN signal_backend_failure IS NOT NULL
                THEN 'SERVICE_FAILURE'

            WHEN tor_or_port_accessible = 0
                THEN 'NETWORK_BLOCK'

            WHEN psiphon_failure IS NOT NULL
                THEN 'CENSORSHIP_INDICATOR'

            ELSE 'NO_SIGNAL'
        END AS blocking_signal_type,

        -- =========================
        -- CONFIDENCE
        -- =========================
        CASE
            WHEN (
                IFNULL(telegram_http_blocking, FALSE)
                OR IFNULL(whatsapp_endpoints_blocked, FALSE)
            ) THEN 'HIGH'

            WHEN (
                whatsapp_web_failure IS NOT NULL
                OR signal_backend_failure IS NOT NULL
            ) THEN 'MEDIUM'

            WHEN psiphon_failure IS NOT NULL THEN 'LOW'

            ELSE 'NONE'
        END AS block_confidence,

        -- =========================
        -- QUALITY SCORE
        -- =========================
        (
            CASE WHEN start_time IS NOT NULL THEN 0.3 ELSE 0 END +
            CASE WHEN input IS NOT NULL THEN 0.2 ELSE 0 END +
            CASE WHEN test_name IS NOT NULL THEN 0.2 ELSE 0 END +
            CASE WHEN asn IS NOT NULL THEN 0.3 ELSE 0 END
        ) AS measurement_quality_score,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
)

SELECT *
FROM normalized;
