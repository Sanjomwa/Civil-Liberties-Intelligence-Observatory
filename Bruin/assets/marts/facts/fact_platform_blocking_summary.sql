/* @bruin
tags:
  - marts_bq
name: marts.fact_platform_blocking_summary
type: bq.sql
connection: bigquery-default
description: |
  Monthly aggregation of OONI censorship signals by platform.
  Built strictly on int.ooni_signals canonical schema.

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        measurement_date,
        EXTRACT(YEAR FROM measurement_date) AS year,
        EXTRACT(MONTH FROM measurement_date) AS month,

        test_name AS platform,
        test_category,

        blocking_signal_type,
        blocking_confidence,

        is_blocked,
        has_measurement_failure,

        asn
    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
),

aggregated AS (
    SELECT
        year,
        month,
        platform,
        test_category,

        COUNT(*) AS total_measurements,

        COUNTIF(is_blocked = TRUE) AS blocked_count,

        COUNT(DISTINCT asn) AS distinct_asns_tested,

        -- SIGNAL DISTRIBUTION (FIXED)
        COUNTIF(blocking_signal_type = 'NETWORK_BLOCK') AS network_block_signals,
        COUNTIF(blocking_signal_type = 'APP_BLOCK') AS app_block_signals,
        COUNTIF(blocking_signal_type = 'DNS_BLOCK') AS dns_block_signals,
        COUNTIF(blocking_signal_type = 'FAILURE') AS failure_signals,

        -- CONFIDENCE DISTRIBUTION
        COUNTIF(blocking_confidence = 'HIGH') AS high_confidence_signals,
        COUNTIF(blocking_confidence = 'MEDIUM') AS medium_confidence_signals,
        COUNTIF(blocking_confidence = 'LOW') AS low_confidence_signals,

        -- RATES
        SAFE_DIVIDE(COUNTIF(is_blocked = TRUE), COUNT(*)) AS blocking_rate,
        SAFE_DIVIDE(COUNTIF(blocking_confidence = 'HIGH'), COUNT(*)) AS high_confidence_rate,
        SAFE_DIVIDE(COUNTIF(has_measurement_failure = TRUE), COUNT(*)) AS failure_rate,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
    GROUP BY year, month, platform, test_category
)

SELECT
    *,

    -- INTENSITY SCORE (clean + bounded)
    LEAST(
        (blocking_rate * 0.65) +
        (high_confidence_rate * 0.25) +
        (failure_rate * 0.10),
        1.0
    ) AS platform_censorship_intensity

FROM aggregated;