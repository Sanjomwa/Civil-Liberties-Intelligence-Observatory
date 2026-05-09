/* @bruin
tags:
  - reporting

name: reporting.mart_asn_behavior_profile
type: bq.sql
connection: bigquery-default

depends:
  - marts.fact_network_blocking_daily
  - marts.dim_asn

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT
        asn,

        COUNT(*) observation_days,

        AVG(blocking_rate)
            AS avg_blocking_rate,

        AVG(confidence_weighted_blocking)
            AS avg_weighted_blocking,

        STDDEV(blocking_rate)
            AS blocking_variability,

        SUM(blocked_events)
            AS total_blocked_events

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country='Kenya'

    GROUP BY asn
)

SELECT
    a.asn,
    d.asn_name,
    d.provider_class,

    observation_days,

    avg_blocking_rate,
    avg_weighted_blocking,
    blocking_variability,
    total_blocked_events,

    ROUND(
        avg_weighted_blocking
        * LOG(1+total_blocked_events),
        4
    ) anomaly_score,

    CASE
        WHEN avg_weighted_blocking>=0.80
            THEN 'HIGH_OBSERVABILITY_PROVIDER'

        WHEN avg_weighted_blocking>=0.50
            THEN 'ELEVATED_SIGNAL_PROVIDER'

        WHEN avg_weighted_blocking>=0.20
            THEN 'VARIABLE'

        ELSE 'STABLE'
    END
        AS behavioral_class

FROM base a

LEFT JOIN
    `encoded-joy-485413-k5.marts.dim_asn` d
    ON a.asn=d.probe_asn