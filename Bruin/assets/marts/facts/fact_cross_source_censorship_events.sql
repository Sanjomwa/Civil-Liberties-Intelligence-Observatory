/* @bruin
tags:
  - marts_bq
name: fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default
description: |
  Unified censorship event spine combining OONI, ACLED, Google Transparency, and Lumen.
  This is the observatory core dataset.

  Each row represents a normalized "digital repression event window"
  across network + platform + legal + real-world protest signals.

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals
  - marts.fact_conflict_events
  - marts.fact_takedown_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni AS (

    SELECT
        measurement_id AS event_id,
        measurement_date,
        asn,
        probe_asn,
        test_name,
        blocking_signal_type,
        blocking_confidence,
        is_blocked,
        'OONI' AS source_system,
        1 AS ooni_flag
    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`

),

conflict AS (

    SELECT
        CAST(measurement_date AS DATE) AS measurement_date,
        COUNT(*) AS conflict_events,
        SUM(fatalities) AS fatalities,
        SUM(population_exposure) AS population_exposure,
        1 AS acled_flag
    FROM `encoded-joy-485413-k5.marts.fact_conflict_events`
    GROUP BY measurement_date

),

takedowns AS (

    SELECT
        measurement_date,
        SUM(number_of_requests) AS takedown_count,
        SUM(items_requested_removal) AS items_targeted,
        COUNT(DISTINCT platform) AS platforms_affected,
        1 AS takedown_flag
    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
    GROUP BY measurement_date

)

SELECT

    -- =========================
    -- CORE EVENT IDENTITY
    -- =========================
    ooni.event_id,
    ooni.measurement_date,
    ooni.source_system,

    ooni.asn,
    ooni.probe_asn,
    ooni.test_name,

    -- =========================
    -- OONI SIGNAL LAYER
    -- =========================
    ooni.is_blocked,
    ooni.blocking_signal_type,
    ooni.blocking_confidence,

    -- =========================
    -- ACLED CONTEXT
    -- =========================
    c.conflict_events,
    c.fatalities,
    c.population_exposure,

    -- =========================
    -- TAKEDOWN CONTEXT
    -- =========================
    t.takedown_count,
    t.items_targeted,
    t.platforms_affected,

    -- =========================
    -- CROSS-SOURCE FLAGS
    -- =========================
    COALESCE(ooni.ooni_flag, 0) AS has_ooni_signal,
    COALESCE(c.acled_flag, 0) AS has_conflict_signal,
    COALESCE(t.takedown_flag, 0) AS has_takedown_signal,

    -- =========================
    -- SPINE EVENT TYPE
    -- =========================
    CASE
        WHEN ooni.is_blocked = TRUE
         AND c.conflict_events > 0
         AND t.takedown_count > 0
        THEN 'FULL_SUPPRESSION_WINDOW'

        WHEN ooni.is_blocked = TRUE
         AND c.conflict_events > 0
        THEN 'NETWORK + CIVIL_UNREST'

        WHEN ooni.is_blocked = TRUE
         AND t.takedown_count > 0
        THEN 'NETWORK + PLATFORM_SUPPRESSION'

        WHEN c.conflict_events > 0
        THEN 'CIVIL_UNREST_ONLY'

        WHEN t.takedown_count > 0
        THEN 'PLATFORM_SUPPRESSION_ONLY'

        WHEN ooni.is_blocked = TRUE
        THEN 'NETWORK_BLOCKING_ONLY'

        ELSE 'LOW_SIGNAL'
    END AS event_classification,

    CURRENT_TIMESTAMP() AS extracted_at

FROM ooni

LEFT JOIN conflict c
    ON ooni.measurement_date = c.measurement_date

LEFT JOIN takedowns t
    ON ooni.measurement_date = t.measurement_date
