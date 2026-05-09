/* @bruin
name: marts.fact_network_blocking_daily
type: bq.sql
connection: bigquery-default

tags:
  - marts_bq
  - dataset_ooni

depends:
  - marts.fact_ooni_censorship_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    measurement_date,
    country,
    probe_asn AS asn,
    protocol,

    COUNT(DISTINCT measurement_id) AS measurement_count,
    COUNT(*) AS observation_count,

    COUNTIF(is_blocking_signal) AS blocked_events,
    COUNTIF(NOT is_blocking_signal) AS clear_events,

    SAFE_DIVIDE(
        COUNTIF(is_blocking_signal),
        COUNT(*)
    ) AS blocking_rate,

    AVG(confidence_score) AS avg_confidence_score,

    SAFE_DIVIDE(
        SUM(
            CASE
                WHEN is_blocking_signal
                THEN confidence_score
                ELSE 0
            END
        ),
        COUNT(*)
    ) AS confidence_weighted_blocking,

    COUNTIF(blocking_detail='dns.bogon') AS dns_bogon_events,
    COUNTIF(blocking_detail='tcp.rst') AS tcp_reset_events,
    COUNTIF(blocking_detail='tls.rst') AS tls_reset_events,
    COUNTIF(blocking_detail='http.451') AS http_451_events,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`

GROUP BY
    measurement_date,
    country,
    asn,
    protocol