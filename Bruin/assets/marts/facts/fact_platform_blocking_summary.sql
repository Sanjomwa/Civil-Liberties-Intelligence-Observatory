/* @bruin
tags:
  - marts_bq
name: marts.fact_platform_blocking_summary
type: bq.sql
connection: bigquery-default
description: |
  Monthly aggregation of OONI censorship signals by platform.
  Core input to dashboards for tracking censorship intensity over time.

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

        blocking_signal,
        blocking_confidence,
        is_blocked,
        is_confirmed_block,

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

        COUNTIF(is_blocked) AS blocked_count,
        COUNTIF(is_confirmed_block) AS confirmed_block_count,

        COUNT(DISTINCT asn) AS distinct_asns_tested,

        -- SIGNAL DISTRIBUTION
        COUNTIF(blocking_signal = 'confirmed_block') AS confirmed_block_signals,
        COUNTIF(blocking_signal = 'suspected_block') AS suspected_block_signals,
        COUNTIF(blocking_signal = 'network_failure') AS network_failure_signals,
        COUNTIF(blocking_signal = 'no_evidence') AS clean_signals,

        -- RATES
        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS blocking_rate,
        SAFE_DIVIDE(COUNTIF(is_confirmed_block), COUNT(*)) AS confirmed_blocking_rate,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
    GROUP BY year, month, platform, test_category
)

SELECT
    *,
    
    -- INTENSITY SCORE (0–1 normalized)
    LEAST(
        (blocking_rate * 0.6) +
        (confirmed_blocking_rate * 0.3) +
        (SAFE_DIVIDE(network_failure_signals, total_measurements) * 0.1),
        1.0
    ) AS platform_censorship_intensity

FROM aggregated;
