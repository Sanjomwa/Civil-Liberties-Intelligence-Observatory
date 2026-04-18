/* @bruin
tags:
  - marts_bq
name: marts.fact_platform_blocking_summary
type: bq.sql
connection: bigquery-default

description: |
  Monthly aggregation of OONI censorship signals by platform.
  Canonical, taxonomy-aligned, Streamlit-ready.

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
        DATE_TRUNC(measurement_date, MONTH) AS month_date,

        EXTRACT(YEAR FROM measurement_date) AS year,
        EXTRACT(MONTH FROM measurement_date) AS month,
        FORMAT_DATE('%Y-%m', measurement_date) AS year_month,

        test_name AS platform,
        test_category,

        blocking_signal_type,
        blocking_confidence,

        is_blocked,
        has_measurement_failure,

        COALESCE(asn, 'UNKNOWN') AS asn

    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
),

aggregated AS (

    SELECT
        month_date,
        year,
        month,
        year_month,

        platform,
        test_category,

        COUNT(*) AS total_measurements,

        COUNTIF(is_blocked) AS blocked_count,
        COUNTIF(has_measurement_failure) AS failure_count,

        COUNT(DISTINCT asn) AS distinct_asns_tested,

        -- canonical taxonomy alignment
        COUNTIF(blocking_signal_type = 'NETWORK_BLOCK') AS network_block_signals,
        COUNTIF(blocking_signal_type = 'DNS_INCONSISTENCY') AS dns_signals,
        COUNTIF(blocking_signal_type = 'APP_LAYER_BLOCK') AS app_layer_signals,
        COUNTIF(blocking_signal_type = 'WEB_FAILURE') AS web_failure_signals,
        COUNTIF(blocking_signal_type = 'SERVICE_FAILURE') AS service_failure_signals,

        -- confidence
        COUNTIF(blocking_confidence = 'HIGH') AS high_conf_signals,
        COUNTIF(blocking_confidence = 'MEDIUM') AS medium_conf_signals,
        COUNTIF(blocking_confidence = 'LOW') AS low_conf_signals,

        -- rates
        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS blocking_rate,
        SAFE_DIVIDE(COUNTIF(blocking_confidence = 'HIGH'), COUNT(*)) AS high_conf_rate,
        SAFE_DIVIDE(COUNTIF(has_measurement_failure), COUNT(*)) AS failure_rate,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
    GROUP BY month_date, year, month, year_month, platform, test_category
)

SELECT
    *,

    -- improved intensity (more stable)
    LEAST(
        (blocking_rate * 0.6) +
        (high_conf_rate * 0.25) +
        (failure_rate * 0.15),
        1.0
    ) AS platform_censorship_intensity

FROM aggregated;