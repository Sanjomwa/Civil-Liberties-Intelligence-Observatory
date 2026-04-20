/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level repression index (v3 FIXED).
  Built directly from atomic fact tables:
    - fact_network_blocking_daily (OONI)
    - fact_conflict_events (ACLED)
    - fact_country_pressure_daily (Lumen/Google)

  Grain: measurement_date × asn

owner: civil-liberties-pipeline

depends:
  - marts.fact_network_blocking_daily
  - marts.fact_conflict_events
  - marts.fact_country_pressure_daily
  - marts.dim_measurement_quality

materialization:
  type: table
  strategy: create+replace
@bruin */


WITH ooni AS (

    SELECT
        measurement_date,
        asn,
        ooni_tests,
        blocked_tests,
        block_rate
    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
),

acled AS (

    SELECT
        measurement_date,
        country,
        conflict_events,
        fatalities
    FROM `encoded-joy-485413-k5.marts.fact_conflict_events`
),

lumen AS (

    SELECT
        measurement_date,
        country,
        takedown_requests
    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
),

quality AS (

    SELECT
        weight AS quality_weight
    FROM `encoded-joy-485413-k5.marts.dim_measurement_quality`
    WHERE quality_level = 'MEDIUM'
    LIMIT 1
),

-- =========================
-- ALIGN EVERYTHING TO ASN SPINE
-- =========================
base AS (

    SELECT
        o.measurement_date,
        o.asn,

        o.ooni_tests,
        o.blocked_tests,
        o.block_rate,

        COALESCE(a.conflict_events, 0) AS conflict_events,
        COALESCE(l.takedown_requests, 0) AS takedown_requests,

        q.quality_weight

    FROM ooni o

    LEFT JOIN acled a
        ON o.measurement_date = a.measurement_date
        AND a.country = 'Kenya'

    LEFT JOIN lumen l
        ON o.measurement_date = l.measurement_date
        AND l.country = 'Kenya'

    CROSS JOIN quality q
),

normalized AS (

    SELECT
        *,

        SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests, 0)) * quality_weight AS q_block_rate

    FROM base
)

SELECT
    measurement_date,
    asn,

    ooni_tests,
    blocked_tests,

    q_block_rate,

    conflict_events,
    takedown_requests,

    -- =========================
    -- NORMALIZED COMPONENTS
    -- =========================
    LEAST(q_block_rate, 1.0) AS block_norm,
    LEAST(conflict_events / 10.0, 1.0) AS conflict_norm,
    LEAST(takedown_requests / 100.0, 1.0) AS takedown_norm,

    -- =========================
    -- FINAL INDEX
    -- =========================
    (
        0.60 * LEAST(q_block_rate, 1.0) +
        0.25 * LEAST(conflict_events / 10.0, 1.0) +
        0.15 * LEAST(takedown_requests / 100.0, 1.0)
    ) AS asn_repression_index_v3

FROM normalized;
