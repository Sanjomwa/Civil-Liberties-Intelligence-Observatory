/* @bruin
tags:
  - marts_bq
name: marts.fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default
description: |
  Unified daily Kenya censorship spine combining:
  - OONI censorship signals
  - ACLED conflict pressure
  - Google + Lumen takedown governance pressure

  This is the core temporal observatory dataset used for:
  - escalation modeling
  - censorship timeline dashboards
  - protest correlation analysis

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals
  - marts.fact_conflict_events
  - marts.fact_takedown_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni_daily AS (
    SELECT
        measurement_date AS date,

        COUNT(*) AS ooni_measurements,
        COUNTIF(is_blocked) AS blocked_count,
        COUNTIF(is_confirmed_block) AS confirmed_block_count,

        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS blocking_rate,
        SAFE_DIVIDE(COUNTIF(is_confirmed_block), COUNT(*)) AS confirmed_blocking_rate

    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
    GROUP BY measurement_date
),

acled_daily AS (
    SELECT
        measurement_date AS date,

        COUNT(*) AS conflict_events,
        SUM(fatalities) AS fatalities,
        SUM(population_exposure) AS population_exposure,

        COUNTIF(event_type IN ('Protests', 'Riots')) AS protest_events

    FROM `encoded-joy-485413-k5.marts.fact_conflict_events`
    GROUP BY measurement_date
),

takedown_daily AS (
    SELECT
        measurement_date AS date,

        COUNT(*) AS takedown_requests,
        SUM(number_of_requests) AS total_requests,
        SUM(items_requested_removal) AS total_items_targeted

    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
    GROUP BY measurement_date
),

spine AS (
    SELECT
        COALESCE(o.date, a.date, t.date) AS date,

        -- OONI SIGNALS
        COALESCE(o.ooni_measurements, 0) AS ooni_measurements,
        COALESCE(o.blocked_count, 0) AS blocked_count,
        COALESCE(o.confirmed_block_count, 0) AS confirmed_block_count,
        COALESCE(o.blocking_rate, 0) AS blocking_rate,
        COALESCE(o.confirmed_blocking_rate, 0) AS confirmed_blocking_rate,

        -- ACLED SIGNALS
        COALESCE(a.conflict_events, 0) AS conflict_events,
        COALESCE(a.fatalities, 0) AS fatalities,
        COALESCE(a.population_exposure, 0) AS population_exposure,
        COALESCE(a.protest_events, 0) AS protest_events,

        -- TAKEDOWN SIGNALS
        COALESCE(t.takedown_requests, 0) AS takedown_requests,
        COALESCE(t.total_requests, 0) AS total_takedown_requests,
        COALESCE(t.total_items_targeted, 0) AS total_items_targeted

    FROM ooni_daily o
    FULL OUTER JOIN acled_daily a USING (date)
    FULL OUTER JOIN takedown_daily t USING (date)
)

SELECT
    *,
    
    -- =========================
    -- NORMALIZED SCORES (0–1)
    -- =========================

    LEAST(blocking_rate, 1.0) AS censorship_score,

    LEAST(
        SAFE_DIVIDE(conflict_events, 10) +
        SAFE_DIVIDE(fatalities, 50),
        1.0
    ) AS conflict_pressure_score,

    LEAST(
        SAFE_DIVIDE(total_takedown_requests, 100),
        1.0
    ) AS governance_pressure_score,

    -- =========================
    -- ESCALATION SCORE
    -- =========================
    LEAST(
        (blocking_rate * 0.5) +
        (SAFE_DIVIDE(conflict_events, 10) * 0.3) +
        (SAFE_DIVIDE(total_takedown_requests, 100) * 0.2),
        1.0
    ) AS escalation_score,

    -- =========================
    -- EVENT CLASSIFICATION
    -- =========================
    CASE
        WHEN blocking_rate > 0.4 AND conflict_events > 5 THEN 'High Suppression + Protest Activity'
        WHEN blocking_rate > 0.4 THEN 'High Censorship Period'
        WHEN conflict_events > 5 THEN 'Conflict Escalation Period'
        WHEN total_takedown_requests > 50 THEN 'Governance Pressure Spike'
        ELSE 'Baseline Activity'
    END AS event_classification,

    CURRENT_TIMESTAMP() AS extracted_at

FROM spine;
