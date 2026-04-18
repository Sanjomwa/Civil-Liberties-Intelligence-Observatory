/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_measurements
type: bq.sql
connection: bigquery-default

description: |
  One row per OONI measurement (Kenya).
  Clean projection from int.ooni_signals.
  Optimized for joins with dims + Streamlit.

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
    COALESCE(asn, 'UNKNOWN') AS asn,
    probe_asn,

    test_name,
    input AS tested_entity,

    start_time,
    extracted_at,

    measurement_date,
    DATE_TRUNC(measurement_date, MONTH) AS month_date,
    FORMAT_DATE('%Y-%m', measurement_date) AS year_month,

    year,
    month,
    day,

    test_category,

    -- canonical signals
    is_blocked,
    has_measurement_failure,
    blocking_confidence,
    blocking_signal_type,

    -- derived flags (useful in dashboards)
    CASE WHEN blocking_confidence = 'HIGH' THEN TRUE ELSE FALSE END AS is_high_confidence,
    CASE WHEN is_blocked AND blocking_confidence = 'HIGH' THEN TRUE ELSE FALSE END AS is_confirmed_block,

    -- test-specific signals
    telegram_http_blocking,
    telegram_tcp_blocking,

    signal_backend_failure,

    whatsapp_endpoints_blocked,
    whatsapp_web_failure,

    tor_or_port_accessible,
    tor_obfs4_accessible,

    psiphon_failure,

    -- lineage
    int_extracted_at

FROM `encoded-joy-485413-k5.int.ooni_signals`
WHERE country = 'KE';