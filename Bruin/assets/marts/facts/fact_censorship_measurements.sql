/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_measurements
type: bq.sql
connection: bigquery-default
description: |
  One row per OONI measurement in Kenya.
  Uses test-specific normalized blocking fields from stg.ooni rather than
  the old generic status IN ('anomaly','confirmed','failure') approach.

  Key columns:
    is_blocked          — broadest blocking signal (test-type aware)
    is_confirmed_block  — high-confidence blocks only
    has_measurement_failure — any network-level error regardless of blocking
    blocking_confidence — 'Confirmed' | 'Probable' | 'Disruption' | 'OK'
    blocking_signal_type — human-readable source of the determination

owner: civil-liberties-pipeline
depends:
  - stg.ooni
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    measurement_id,
    country,
    asn,
    test_name,
    input                                               AS tested_url_or_app,
    start_time,
    probe_cc,
    probe_asn,
    extracted_at,
    measurement_date,
    test_category,
    year,
    month,

    -- ── Canonical blocking fields ─────────────────────────────────────────
    is_blocked,
    is_confirmed_block,
    has_measurement_failure,
    blocking_confidence,
    blocking_signal_type,

    -- ── Test-specific raw flags (for platform-specific dashboards) ────────
    telegram_http_blocking,
    telegram_tcp_blocking,
    signal_backend_failure,
    whatsapp_endpoints_blocked,
    whatsapp_endpoints_dns_inconsistent,
    whatsapp_web_failure,
    tor_dir_port_accessible,
    tor_obfs4_accessible,
    tor_or_port_accessible,
    psiphon_failure

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_ooni`
WHERE probe_cc = 'KE'
