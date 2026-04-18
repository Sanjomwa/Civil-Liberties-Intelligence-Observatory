/* @bruin
tags:
  - int_bq
name: int.ooni_signals
type: bq.sql
connection: bigquery-default

description: |
  Intermediate OONI signal layer.
  Converts STG OONI measurements into standardized censorship signals
  using only validated STG fields (OONI pipeline compliant).

depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT *
    FROM `encoded-joy-485413-k5.stg.ooni_measurements`
),

classified AS (

    SELECT
        measurement_id,
        country,
        asn,
        probe_asn,
        test_name,
        input,
        start_time,
        extracted_at,
        measurement_date,
        year,
        month,
        day,

        -- =========================
        -- TEST CATEGORY (SAFE RULE-BASED)
        -- =========================
        CASE
            WHEN LOWER(test_name) LIKE '%telegram%' THEN 'messaging'
            WHEN LOWER(test_name) LIKE '%whatsapp%' THEN 'messaging'
            WHEN LOWER(test_name) LIKE '%signal%' THEN 'messaging'
            WHEN LOWER(test_name) LIKE '%dns%' THEN 'dns'
            WHEN LOWER(test_name) LIKE '%tor%' THEN 'circumvention'
            WHEN LOWER(test_name) LIKE '%psiphon%' THEN 'circumvention'
            ELSE 'web'
        END AS test_category,

        telegram_http_blocking,
        telegram_tcp_blocking,
        whatsapp_endpoints_blocked,
        whatsapp_web_failure,
        signal_backend_failure,
        tor_or_port_accessible,
        tor_obfs4_accessible,
        psiphon_failure

    FROM base
),

signals AS (

    SELECT
        *,

        -- =========================
        -- UNIFIED BLOCK SIGNAL TYPE
        -- =========================
        CASE
            WHEN telegram_http_blocking = TRUE
              OR telegram_tcp_blocking = TRUE
              OR whatsapp_endpoints_blocked = TRUE
            THEN 'APP_LAYER_BLOCK'

            WHEN whatsapp_web_failure IS NOT NULL
            THEN 'WEB_FAILURE'

            WHEN signal_backend_failure IS NOT NULL
            THEN 'SERVICE_FAILURE'

            WHEN tor_or_port_accessible = 0
              OR tor_obfs4_accessible = 0
            THEN 'NETWORK_BLOCK'

            WHEN psiphon_failure IS NOT NULL
            THEN 'CIRCUMVENTION_FAILURE'

            ELSE 'NO_SIGNAL'
        END AS blocking_signal_type,

        -- =========================
        -- BOOLEAN BLOCK INDICATOR
        -- =========================
        CASE
            WHEN telegram_http_blocking = TRUE
              OR telegram_tcp_blocking = TRUE
              OR whatsapp_endpoints_blocked = TRUE
              OR (tor_or_port_accessible = 0 AND tor_obfs4_accessible = 0)
            THEN TRUE
            ELSE FALSE
        END AS is_blocked,

        -- =========================
        -- CONFIDENCE MODEL (STRICT + SAFE)
        -- =========================
        CASE
            WHEN telegram_http_blocking = TRUE
              OR whatsapp_endpoints_blocked = TRUE
            THEN 'HIGH'

            WHEN whatsapp_web_failure IS NOT NULL
              OR signal_backend_failure IS NOT NULL
            THEN 'MEDIUM'

            WHEN psiphon_failure IS NOT NULL
              OR tor_or_port_accessible = 0
            THEN 'LOW'

            ELSE 'NONE'
        END AS blocking_confidence,

        -- =========================
        -- FAILURE FLAG
        -- =========================
        CASE
            WHEN signal_backend_failure IS NOT NULL THEN TRUE
            ELSE FALSE
        END AS has_measurement_failure

    FROM classified
)

SELECT
    *,
    CURRENT_TIMESTAMP() AS int_extracted_at
FROM signals;