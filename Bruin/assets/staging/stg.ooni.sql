/* @bruin
name: stg.ooni
type: bq.sql
connection: bigquery-default
description: |
  Cleaned and standardised OONI censorship measurements for Kenya
  (Jun 2023–Jun 2025).

  Uses test-specific blocking fields extracted in raw.ooni rather than
  generic anomaly/confirmed/failure flags, which are unreliable across
  test types.

  Blocking logic summary:
    telegram   → telegram_http_blocking OR telegram_tcp_blocking
    whatsapp   → whatsapp_endpoints_blocked OR dns_inconsistent
    signal     → signal_backend_failure IS NOT NULL (disruption only)
    tor        → tor_or_port_accessible = 0 (circumvention disruption)
    psiphon    → psiphon_failure IS NOT NULL (disruption only)
    web/other  → is_blocked as derived in raw layer

tags:
  - stg_bq
  - dataset_ooni

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
        start_time,
        probe_cc,
        probe_asn,
        extracted_at,

        -- ── Test-specific raw flags (preserved for forensic analysis) ──────
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

        -- ── Canonical normalized blocking fields ───────────────────────────
        is_blocked,
        is_confirmed_block,
        has_measurement_failure,
        blocking_signal_type,

        -- ── Derived time fields ────────────────────────────────────────────
        DATE(start_time)                                    AS measurement_date,
        EXTRACT(YEAR  FROM start_time)                      AS year,
        EXTRACT(MONTH FROM start_time)                      AS month,

        -- ── Test category ──────────────────────────────────────────────────
        CASE
            WHEN test_name IN ('web_connectivity', 'dnscheck', 'http_requests')
                THEN 'Website/DNS Blocking'
            WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal')
                THEN 'Messaging App Blocking'
            WHEN test_name IN ('tor', 'psiphon', 'lantern')
                THEN 'Circumvention Tool Blocking'
            ELSE 'Other'
        END                                                 AS test_category,

        -- ── Blocking confidence tier ───────────────────────────────────────
        -- Used for dashboard colour coding and filtering
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
