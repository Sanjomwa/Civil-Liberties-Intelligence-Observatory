/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  Daily ASN-level repression index derived from OONI censorship signals.
  Measures intensity, breadth, and consistency of censorship across ISPs.

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        asn,
        country,
        measurement_date,
        test_name,

        is_blocked,
        blocking_confidence,

        telegram_http_blocking,
        telegram_tcp_blocking,
        whatsapp_endpoints_blocked,
        whatsapp_web_failure,
        signal_backend_failure,
        tor_or_port_accessible,
        tor_obfs4_accessible,
        psiphon_failure

    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
),

aggregated AS (
    SELECT
        asn,
        measurement_date,

        COUNT(*) AS total_tests,

        COUNTIF(is_blocked) AS blocked_tests,

        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS raw_block_rate,

        -- =========================
        -- confidence weighting
        -- =========================
        SUM(
            CASE blocking_confidence
                WHEN 'HIGH' THEN 1.0
                WHEN 'MEDIUM' THEN 0.6
                WHEN 'LOW' THEN 0.3
                ELSE 0.1
            END * IF(is_blocked, 1, 0)
        ) AS weighted_blocking_intensity,

        -- =========================
        -- failure pressure
        -- =========================
        SUM(
            IF(signal_backend_failure IS NOT NULL, 1, 0)
        ) AS failure_signals,

        -- =========================
        -- breadth (multi-test spread)
        -- =========================
        COUNT(DISTINCT test_name) AS test_breadth,

        -- =========================
        -- consistency proxy
        -- =========================
        COUNTIF(is_blocked) / COUNT(DISTINCT test_name) AS consistency_score

    FROM base
    GROUP BY asn, measurement_date
)

SELECT
    asn,
    measurement_date,
    total_tests,
    blocked_tests,

    raw_block_rate,

    test_breadth,
    failure_signals,

    -- normalized components
    SAFE_DIVIDE(weighted_blocking_intensity, total_tests) AS blocking_intensity,

    SAFE_DIVIDE(failure_signals, total_tests) AS failure_pressure,

    SAFE_DIVIDE(test_breadth, 5.0) AS breadth_score,

    LEAST(consistency_score, 1.0) AS consistency_score,

    -- =========================
    -- FINAL INDEX
    -- =========================
    ROUND(
        (0.35 * SAFE_DIVIDE(weighted_blocking_intensity, total_tests))
      + (0.20 * SAFE_DIVIDE(failure_signals, total_tests))
      + (0.20 * SAFE_DIVIDE(test_breadth, 5.0))
      + (0.15 * LEAST(consistency_score, 1.0))
      + (0.10 * LOG(total_tests + 1))
    , 4) AS asn_repression_index

FROM aggregated;