/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level repression index derived from cross-source censorship spine.
  Combines OONI network blocking + ACLED conflict pressure + Lumen takedown pressure.

  Grain:
    measurement_date × country × asn

owner: civil-liberties-pipeline

depends:
  - marts.fact_cross_source_censorship_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        measurement_date,
        country,
        asn,

        ooni_tests,
        blocked_tests,
        block_rate,
        high_conf_block_present,
        network_block_signals,

        conflict_events,
        fatalities,
        population_exposure,
        event_diversity,

        takedown_requests,
        takedown_items,
        takedown_events
    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events`
),

scored AS (
    SELECT
        *,

        -- =========================
        -- NORMALIZED PRESSURE COMPONENTS
        -- =========================

        -- Conflict pressure (bounded)
        LEAST(conflict_events / 10.0, 1.0) AS conflict_pressure,

        -- Takedown pressure (bounded)
        LEAST(takedown_requests / 100.0, 1.0) AS takedown_pressure,

        -- High confidence boost
        CASE
            WHEN high_conf_block_present = 1 THEN 1.0
            ELSE 0.0
        END AS high_conf_bonus,

        -- Network signal intensity
        LEAST(network_block_signals / 5.0, 1.0) AS network_intensity

    FROM base
)

SELECT
    measurement_date,
    country,
    asn,

    ooni_tests,
    blocked_tests,
    block_rate,

    conflict_events,
    fatalities,
    population_exposure,

    takedown_requests,
    takedown_items,

    high_conf_block_present,
    network_block_signals,

    -- =========================
    -- FINAL INDEX COMPONENTS
    -- =========================

    ROUND(
        (
            COALESCE(block_rate, 0) * 0.55
          + COALESCE(conflict_pressure, 0) * 0.25
          + COALESCE(takedown_pressure, 0) * 0.15
          + COALESCE(high_conf_bonus, 0) * 0.05
        ),
    4) AS asn_repression_index,

    -- =========================
    -- INTERPRETATION BAND
    -- =========================

    CASE
        WHEN block_rate >= 0.7 AND conflict_events > 0 THEN 'HIGH_REPRESSION'
        WHEN block_rate >= 0.7 THEN 'NETWORK_REPRESSION'
        WHEN conflict_events > 0 THEN 'CIVIC_PRESSURE_ONLY'
        WHEN takedown_requests > 0 THEN 'LEGAL_PRESSURE_ONLY'
        ELSE 'BASELINE'
    END AS repression_category

FROM scored;