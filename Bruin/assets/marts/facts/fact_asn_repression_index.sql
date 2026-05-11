/* @bruin
tags:
  - marts_bq

name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level probabilistic repression observability index.

  Grain:
    1 row per measurement_date × ASN

  Integrates:
  - confidence-weighted OONI blocking behavior
  - political conflict stress
  - takedown escalation pressure
  - measurement reliability weighting

depends:
  - marts.fact_network_blocking_daily
  - marts.fact_country_pressure_daily
  - marts.dim_measurement_quality

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ============================================
-- ASN-DAY AGGREGATION (STRICT GRAIN)
-- ============================================
WITH ooni AS (

    SELECT
        measurement_date,
        asn,

        SUM(measurement_count) AS measurement_count,
        SUM(blocked_events) AS blocked_events,

        SAFE_DIVIDE(
            SUM(blocked_events),
            SUM(measurement_count)
        ) AS blocking_rate,

        AVG(confidence_weighted_blocking)
            AS confidence_weighted_blocking

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country = 'KE'

    GROUP BY
        measurement_date,
        asn
),

-- ============================================
-- COUNTRY PRESSURE
-- ============================================
country_pressure AS (

    SELECT
        measurement_date,

        COALESCE(conflict_events,0)
            AS conflict_events,

        COALESCE(fatalities,0)
            AS fatalities,

        COALESCE(takedown_requests,0)
            AS takedown_requests,

        COALESCE(
            composite_pressure_score,
            0
        ) AS country_pressure_score

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`

    WHERE iso2 = 'KE'
),

-- ============================================
-- QUALITY BASELINE
-- ============================================
quality AS (

    SELECT
        weight AS quality_weight

    FROM `encoded-joy-485413-k5.marts.dim_measurement_quality`

    WHERE quality_level = 'PARTIAL'

    LIMIT 1
),

-- ============================================
-- JOINED CONTEXT
-- ============================================
base AS (

    SELECT
        o.measurement_date,
        o.asn,

        o.measurement_count,
        o.blocked_events,

        o.blocking_rate,
        o.confidence_weighted_blocking,

        cp.conflict_events,
        cp.fatalities,
        cp.takedown_requests,
        cp.country_pressure_score,

        q.quality_weight

    FROM ooni o

    LEFT JOIN country_pressure cp
        ON cp.measurement_date = o.measurement_date

    CROSS JOIN quality q
),

-- ============================================
-- RELIABILITY-WEIGHTED SIGNAL
-- ============================================
normalized AS (

    SELECT
        *,

        confidence_weighted_blocking
            * quality_weight
            AS weighted_signal

    FROM base
)

-- ============================================
-- FINAL INDEX
-- ============================================
SELECT
    measurement_date,
    asn,

    measurement_count,
    blocked_events,

    ROUND(blocking_rate,8)
        AS blocking_rate,

    ROUND(confidence_weighted_blocking,8)
        AS confidence_weighted_blocking,

    ROUND(weighted_signal,8)
        AS weighted_signal,

    conflict_events,
    fatalities,
    takedown_requests,

    ROUND(country_pressure_score,4)
        AS country_pressure_score,

    LEAST(weighted_signal,1.0)
        AS block_norm,

    LEAST(conflict_events / 10.0,1.0)
        AS conflict_norm,

    LEAST(fatalities / 25.0,1.0)
        AS fatality_norm,

    LEAST(takedown_requests / 100.0,1.0)
        AS takedown_norm,

    LEAST(country_pressure_score / 10.0,1.0)
        AS country_pressure_norm,

    ROUND(
        (
            0.45 * LEAST(weighted_signal,1.0)
          + 0.20 * LEAST(conflict_events / 10.0,1.0)
          + 0.10 * LEAST(fatalities / 25.0,1.0)
          + 0.10 * LEAST(takedown_requests / 100.0,1.0)
          + 0.15 * LEAST(country_pressure_score / 10.0,1.0)
        ),
        4
    ) AS asn_repression_index

FROM normalized

ORDER BY
    measurement_date,
    asn