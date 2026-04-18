/* @bruin
tags:
  - marts_bq
name: fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default
description: |
  v2 Cross-source censorship spine with temporal clustering.
  Converts daily signals into suppression "episodes" using rolling windows.

  This is the core observatory event model powering all dashboards.

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals
  - marts.fact_conflict_events
  - marts.fact_takedown_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base_daily AS (

    SELECT
        measurement_date,

        -- OONI
        COUNTIF(is_blocked = TRUE) AS blocked_count,
        COUNT(*) AS total_measurements,

        AVG(CASE
            WHEN blocking_confidence = 'HIGH' THEN 3
            WHEN blocking_confidence = 'MEDIUM' THEN 2
            WHEN blocking_confidence = 'LOW' THEN 1
            ELSE 0
        END) AS avg_blocking_confidence,

        -- ACLED
        MAX(conflict_events) AS conflict_events,
        SUM(fatalities) AS fatalities,
        SUM(population_exposure) AS population_exposure,

        -- TAKEDOWNS
        SUM(takedown_count) AS takedown_count,
        SUM(items_targeted) AS items_targeted,

        COUNT(DISTINCT asn) AS affected_asns

    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events`
    GROUP BY measurement_date

),

rolling AS (

    SELECT
        a.*,

        -- =========================
        -- 3-DAY ROLLING WINDOWS
        -- =========================
        SUM(blocked_count) OVER (
            ORDER BY measurement_date
            RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW
        ) AS blocked_3d,

        SUM(conflict_events) OVER (
            ORDER BY measurement_date
            RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW
        ) AS conflict_3d,

        SUM(takedown_count) OVER (
            ORDER BY measurement_date
            RANGE BETWEEN INTERVAL 2 DAY PRECEDING AND CURRENT ROW
        ) AS takedown_3d

    FROM base_daily a

),

scored AS (

    SELECT
        *,

        -- =========================
        -- SUPPRESSION INTENSITY SCORE
        -- =========================
        (
            LEAST(blocked_count * 0.4, 1.0)
            + LEAST(conflict_events * 0.2, 1.0)
            + LEAST(takedown_count * 0.2, 1.0)
            + LEAST(blocked_3d * 0.2, 1.0)
        ) AS daily_intensity_score,

        -- =========================
        -- EVENT TRIGGER FLAG
        -- =========================
        CASE
            WHEN blocked_3d > 50
             AND conflict_3d > 0
            THEN 1 ELSE 0
        END AS is_suppression_episode_day

    FROM rolling

),

episodes AS (

    SELECT
        *,
        SUM(is_suppression_episode_day) OVER (
            ORDER BY measurement_date
        ) AS episode_group_id
    FROM scored

)

SELECT

    -- =========================
    -- EVENT IDENTITY
    -- =========================
    CONCAT('EP-', CAST(episode_group_id AS STRING)) AS episode_id,
    measurement_date,

    episode_group_id,

    -- =========================
    -- CORE SIGNALS
    -- =========================
    blocked_count,
    conflict_events,
    fatalities,
    population_exposure,
    takedown_count,

    affected_asns,

    -- =========================
    -- ROLLING CONTEXT
    -- =========================
    blocked_3d,
    conflict_3d,
    takedown_3d,

    -- =========================
    -- INTENSITY MODEL
    -- =========================
    daily_intensity_score,

    CASE
        WHEN daily_intensity_score > 1.5 THEN 'HIGH INTENSITY EPISODE'
        WHEN daily_intensity_score > 0.8 THEN 'MEDIUM INTENSITY EPISODE'
        ELSE 'LOW INTENSITY ACTIVITY'
    END AS episode_severity,

    -- =========================
    -- CROSS-SOURCE ALIGNMENT
    -- =========================
    CASE
        WHEN blocked_count > 0
         AND conflict_events > 0
         AND takedown_count > 0
        THEN 'FULL CROSS-SOURCE ALIGNMENT'

        WHEN blocked_count > 0
         AND conflict_events > 0
        THEN 'NETWORK + CIVIL UNREST'

        WHEN blocked_count > 0
         AND takedown_count > 0
        THEN 'NETWORK + PLATFORM ACTION'

        WHEN conflict_events > 0
        THEN 'CIVIL UNREST ONLY'

        WHEN blocked_count > 0
        THEN 'NETWORK ONLY'

        ELSE 'LOW SIGNAL'
    END AS cross_source_pattern,

    CURRENT_TIMESTAMP() AS extracted_at

FROM episodes
