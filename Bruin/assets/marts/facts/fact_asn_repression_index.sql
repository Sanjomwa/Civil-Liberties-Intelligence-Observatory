/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level repression index (v3 FIXED).
  Uses ONLY ASN-grain OONI + country-projected pressure signals.

depends:
  - marts.fact_network_blocking_daily
  - marts.fact_country_pressure_daily
  - marts.dim_measurement_quality

materialization:
  type: table
  strategy: create+replace
@bruin */

-- =========================
-- OONI (TRUE ASN GRAIN)
-- =========================
WITH ooni AS (

    SELECT
        measurement_date,
        asn,
        ooni_tests,
        blocked_tests,
        block_rate
    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
),

-- =========================
-- COUNTRY PRESSURE (ACLED + LUMEN)
-- =========================
country_pressure AS (

    SELECT
        measurement_date,
        country,
        conflict_events,
        fatalities,
        takedown_requests
    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
),

-- =========================
-- ASN ↔ COUNTRY MAPPING (FROM OONI)
-- =========================
asn_country AS (

    SELECT DISTINCT
        asn,
        country
    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
),

-- =========================
-- QUALITY WEIGHT
-- =========================
quality AS (

    SELECT
        weight AS quality_weight
    FROM `encoded-joy-485413-k5.marts.dim_measurement_quality`
    WHERE quality_level = 'MEDIUM'
    LIMIT 1
),

-- =========================
-- JOINED ASN CONTEXT
-- =========================
base AS (

    SELECT
        o.measurement_date,
        o.asn,

        o.ooni_tests,
        o.blocked_tests,
        o.block_rate,

        COALESCE(cp.conflict_events, 0) AS conflict_events,
        COALESCE(cp.takedown_requests, 0) AS takedown_requests,

        q.quality_weight

    FROM ooni o

    LEFT JOIN asn_country ac
        ON o.asn = ac.asn

    LEFT JOIN country_pressure cp
        ON cp.country = ac.country
       AND cp.measurement_date = o.measurement_date

    CROSS JOIN quality q
),

-- =========================
-- NORMALIZATION
-- =========================
normalized AS (

    SELECT
        *,

        SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests, 0)) * quality_weight AS q_block_rate

    FROM base
)

-- =========================
-- FINAL INDEX
-- =========================
SELECT
    measurement_date,
    asn,

    ooni_tests,
    blocked_tests,

    q_block_rate,

    conflict_events,
    takedown_requests,

    LEAST(q_block_rate, 1.0) AS block_norm,
    LEAST(conflict_events / 10.0, 1.0) AS conflict_norm,
    LEAST(takedown_requests / 100.0, 1.0) AS takedown_norm,

    (
        0.60 * LEAST(q_block_rate, 1.0) +
        0.25 * LEAST(conflict_events / 10.0, 1.0) +
        0.15 * LEAST(takedown_requests / 100.0, 1.0)
    ) AS asn_repression_index_v3

FROM normalized;