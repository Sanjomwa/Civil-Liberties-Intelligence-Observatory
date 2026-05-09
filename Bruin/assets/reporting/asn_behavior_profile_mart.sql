/* @bruin
tags:
  - reporting

name: reporting.asn_behavior_profile_mart
type: bq.sql
connection: bigquery-default

description: |
  Behavioral observability profile for Kenyan ASNs
  using OONI-derived blocking signal distributions.

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

        COUNT(*) AS observation_days,

        AVG(blocking_rate)
            AS avg_blocking_rate,

        AVG(confidence_weighted_blocking)
            AS avg_weighted_blocking,

        STDDEV(blocking_rate)
            AS blocking_variability,

        SUM(blocked_events)
            AS total_blocked_events

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country IN ('Kenya','KE','ke')

    GROUP BY asn
)

SELECT
    b.asn,

    d.asn AS display_asn,
    d.network_class,
    d.is_kenya_observability_core,
    d.censorship_sensitivity_score,

    b.observation_days,

    b.avg_blocking_rate,
    b.avg_weighted_blocking,
    b.blocking_variability,
    b.total_blocked_events,

    ROUND(
        (
            b.avg_weighted_blocking
            * LOG(1 + b.total_blocked_events)
            * d.censorship_sensitivity_score
        ),
        4
    ) AS anomaly_score,

    CASE
        WHEN b.avg_weighted_blocking >= 0.80
            THEN 'HIGH_SIGNAL_PROVIDER'

        WHEN b.avg_weighted_blocking >= 0.50
            THEN 'ELEVATED_SIGNAL_PROVIDER'

        WHEN b.avg_weighted_blocking >= 0.20
            THEN 'VARIABLE_BEHAVIOR'

        ELSE 'STABLE'
    END AS behavioral_class,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM base b

LEFT JOIN
    `encoded-joy-485413-k5.marts.dim_asn` d
ON CAST(b.asn AS STRING) = CAST(d.asn_numeric AS STRING)

ORDER BY anomaly_score DESC