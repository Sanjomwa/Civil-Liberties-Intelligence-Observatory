/* @bruin
tags:
  - marts_bq
name: marts.fact_ooni_censorship_signals
type: bq.sql
connection: bigquery-default

description: |
  OONI censorship signals at measurement × test grain.
  Preserves per-test blocking behavior for cross-platform analysis.

owner: civil-liberties-pipeline

depends:
  - int.ooni_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    -- =========================
    -- PRIMARY GRAIN
    -- =========================
    measurement_id,
    test_name,

    -- =========================
    -- ENTITY DIMENSIONS
    -- =========================
    country,
    asn,
    probe_asn,
    input,

    -- =========================
    -- TIME
    -- =========================
    start_time,
    measurement_date,
    year,
    month,
    day,
    extracted_at,
    int_extracted_at,

    -- =========================
    -- CLASSIFICATION
    -- =========================
    test_category,
    blocking_signal_type,
    blocking_confidence,

    -- =========================
    -- SIGNAL FLAGS
    -- =========================
    telegram_http_blocking,
    telegram_tcp_blocking,

    whatsapp_endpoints_blocked,
    whatsapp_web_failure,

    signal_backend_failure,

    tor_or_port_accessible,
    tor_obfs4_accessible,

    psiphon_failure,

    -- =========================
    -- CORE OUTCOMES
    -- =========================
    is_blocked,
    has_measurement_failure

FROM `encoded-joy-485413-k5.int.ooni_signals`;