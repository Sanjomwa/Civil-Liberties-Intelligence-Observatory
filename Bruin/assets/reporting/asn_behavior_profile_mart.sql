/* @bruin
tags:
  - reporting

name: reporting.asn_behavior_profile_mart
type: bq.sql
connection: bigquery-default

description: |
  Behavioral observability profile for Kenyan ASNs using
  normalized OONI-derived blocking signal distributions.

depends:
  - marts.fact_network_blocking_daily
  - marts.dim_asn

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ============================================
-- ASN DAILY BASELINE
-- ============================================
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
),

-- ============================================
-- NORMALIZED SIGNAL SCALE
-- ============================================
scaled AS (

    SELECT
        *,

        SAFE_DIVIDE(
            avg_weighted_blocking,
            MAX(avg_weighted_blocking) OVER ()
        ) AS normalized_weighted_signal

    FROM base
)

-- ============================================
-- FINAL OUTPUT
-- ============================================
SELECT
    s.asn,

    d.asn AS display_asn,
    d.network_class,
    d.is_kenya_observability_core,
    d.censorship_sensitivity_score,

    s.observation_days,

    s.avg_blocking_rate,
    s.avg_weighted_blocking,
    s.normalized_weighted_signal,

    s.blocking_variability,
    s.total_blocked_events,

    ROUND(
        (
            s.normalized_weighted_signal
            * LOG(1 + s.total_blocked_events)
            * d.censorship_sensitivity_score
        ),
        4
    ) AS anomaly_score,

    CASE

        WHEN normalized_weighted_signal >= 0.75
            THEN 'HIGH_SIGNAL_PROVIDER'

        WHEN normalized_weighted_signal >= 0.45
            THEN 'ELEVATED_SIGNAL_PROVIDER'

        WHEN normalized_weighted_signal >= 0.20
            THEN 'VARIABLE_BEHAVIOR'

        ELSE 'STABLE'

    END AS behavioral_class,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM scaled s

LEFT JOIN
    `encoded-joy-485413-k5.marts.dim_asn` d
ON CAST(s.asn AS STRING) = CAST(d.asn_numeric AS STRING)

ORDER BY anomaly_score DESC