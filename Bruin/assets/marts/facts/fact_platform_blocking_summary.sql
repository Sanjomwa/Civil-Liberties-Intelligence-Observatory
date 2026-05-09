/* @bruin
tags:
  - marts_bq
  - dataset_ooni

name: marts.fact_protocol_blocking_summary
type: bq.sql
connection: bigquery-default

description: |
  Monthly aggregation of OONI protocol-level experiment results.
  Aligned to OONI v5 observation/result philosophy.

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

        country,
        probe_asn,
        probe_network_name,

        test_name,
        protocol,

        result_state,
        blocking_detail,
        failure_reason,

        is_blocking_signal,

        confidence_score,

        measurement_id,
        observation_id,
        experiment_result_id

    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
),

aggregated AS (

    SELECT
        month_date,
        year,
        month,
        year_month,

        country,

        test_name,
        protocol,

        COUNT(*) AS total_experiment_results,

        COUNTIF(is_blocking_signal) AS blocking_signal_count,

        COUNTIF(result_state = 'BLOCKED') AS blocked_results,
        COUNTIF(result_state = 'OK') AS ok_results,
        COUNTIF(result_state = 'DOWN') AS down_results,
        COUNTIF(result_state = 'ERROR') AS error_results,

        COUNT(DISTINCT measurement_id) AS distinct_measurements,
        COUNT(DISTINCT observation_id) AS distinct_observations,
        COUNT(DISTINCT probe_asn) AS distinct_asns,

        -- evidence types
        COUNTIF(blocking_detail = 'dns') AS dns_blocking_events,
        COUNTIF(blocking_detail = 'tcp') AS tcp_blocking_events,
        COUNTIF(blocking_detail = 'tls') AS tls_blocking_events,
        COUNTIF(blocking_detail = 'http') AS http_blocking_events,

        -- confidence bands
        COUNTIF(confidence_score >= 0.90) AS high_confidence_events,
        COUNTIF(confidence_score BETWEEN 0.70 AND 0.89) AS medium_confidence_events,
        COUNTIF(confidence_score < 0.70) AS low_confidence_events,

        SAFE_DIVIDE(
            COUNTIF(is_blocking_signal),
            COUNT(*)
        ) AS blocking_signal_rate,

        SAFE_DIVIDE(
            COUNTIF(result_state = 'BLOCKED'),
            COUNT(*)
        ) AS blocked_result_rate,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
    GROUP BY
        month_date,
        year,
        month,
        year_month,
        country,
        test_name,
        protocol
)

SELECT
    *,

    LEAST(
        (blocking_signal_rate * 0.7) +
        (blocked_result_rate * 0.3),
        1.0
    ) AS protocol_interference_intensity

FROM aggregated;
