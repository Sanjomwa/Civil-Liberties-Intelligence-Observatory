/* @bruin
tags:
  - marts_bq

name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level probabilistic repression observability index.

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
-- ASN-GRAIN NETWORK OBSERVABILITY
-- ============================================
WITH ooni AS (

    SELECT
        measurement_date,
        asn,

        measurement_count,
        blocked_events,
        blocking_rate,
        confidence_weighted_blocking

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
),

-- ============================================
-- COUNTRY PRESSURE CONTEXT
-- ============================================
country_pressure AS (

    SELECT
        measurement_date,
        country,

        conflict_events,
        fatalities,
        takedown_requests,
        composite_pressure_score

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
),

-- ============================================
-- ASN ↔ COUNTRY MAP
-- ============================================
asn_country AS (

    SELECT DISTINCT
        asn,
        country

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
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

        COALESCE(cp.conflict_events,0)
            AS conflict_events,

        COALESCE(cp.fatalities,0)
            AS fatalities,

        COALESCE(cp.takedown_requests,0)
            AS takedown_requests,

        COALESCE(cp.composite_pressure_score,0)
            AS country_pressure_score,

        q.quality_weight

    FROM ooni o

    LEFT JOIN asn_country ac
        ON o.asn = ac.asn

    LEFT JOIN country_pressure cp
        ON cp.country = ac.country
       AND cp.measurement_date = o.measurement_date

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

    blocking_rate,
    confidence_weighted_blocking,
    weighted_signal,

    conflict_events,
    fatalities,
    takedown_requests,
    country_pressure_score,

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