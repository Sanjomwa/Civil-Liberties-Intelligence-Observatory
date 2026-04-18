/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_measurements
type: bq.sql
connection: bigquery-default

description: |
  One row per OONI measurement in Kenya.
  Thin projection over int.ooni_signals (no re-derivation).

owner: civil-liberties-pipeline

depends:
  - int.ooni_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    measurement_id,
    country,
    asn,
    probe_asn,

    test_name,
    input AS tested_url_or_app,

    start_time,
    extracted_at,
    measurement_date,

    year,
    month,
    day,

    test_category,

    -- ── Canonical INT signals ─────────────────────────────────────────────
    is_blocked,
    has_measurement_failure,
    blocking_confidence,
    blocking_signal_type,

    -- ── Test-specific signals ─────────────────────────────────────────────
    telegram_http_blocking,
    telegram_tcp_blocking,

    signal_backend_failure,

    whatsapp_endpoints_blocked,
    whatsapp_web_failure,

    tor_or_port_accessible,
    tor_obfs4_accessible,

    psiphon_failure,

    -- ── lineage/debugging ────────────────────────────────────────────────
    int_extracted_at

FROM `encoded-joy-485413-k5.int.ooni_signals`
WHERE country = 'KE';