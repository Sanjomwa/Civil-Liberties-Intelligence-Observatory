/* @bruin
tags:
  - marts_bq

name: marts.fact_country_pressure_daily
type: bq.sql
connection: bigquery-default

description: |
  Daily Kenya pressure observability fact.

  Blends:
  - ACLED political conflict intensity
  - Lumen legal takedown activity
  - Google transparency pressure

  Rebalanced so political stress dominates severity.

depends:
  - marts.dim_dates
  - stg.acled_conflict_events
  - stg.lumen_requests
  - int.google_pressure_periodized
  - intelligence.acled_pressure_regimes

materialization:
  type: table
  strategy: create+replace
@bruin */

-- ADR-0002 step (e): additive ACLED path A join.
-- intelligence.acled_pressure_regimes is grain country x week_start_date,
-- anchored to Saturday (verified empirically against the materialized
-- table -- the asset's own upstream staging comment claiming a Monday
-- anchor does not match the actual parsed data). DATE_TRUNC(..., WEEK(SATURDAY))
-- maps any calendar day back to the Saturday that starts its ACLED week.
-- regime_* columns are a nullable passthrough, not COALESCEd: NULL here
-- means no regime classification exists yet for that week (e.g. before
-- backfill start or after the latest processed week), which is a
-- different and more honest signal than a fabricated default.

WITH dates AS (

    SELECT date_key AS measurement_date
    FROM `{{ var.project_id }}.marts.dim_dates`

),

acled AS (

    -- TD-40 fix: event_date is hardcoded CAST(NULL AS DATE) for every row
    -- in stg.acled_conflict_events.sql (weekly-aggregate source, reserved
    -- for a future event-level pipeline that does not exist yet). The
    -- real join key is week_start_date, Saturday-anchored (verified
    -- empirically for ADR-0002 step (e); the staging header's own
    -- Monday-anchor claim was stale and has been corrected).
    --
    -- This broadcasts one weekly ACLED value across all 7 days of that
    -- week: conflict_events, fatalities, and therefore
    -- conflict_pressure_score are CONSTANT within a calendar week and
    -- only step at week boundaries. Despite this table's nominal daily
    -- grain, ACLED's 60%-weighted contribution to composite_pressure_score
    -- is NOT day-resolved -- only legal_pressure_score (25%) and
    -- platform_pressure_score (15%) vary within a week. Do not assume
    -- day-to-day movement in composite_pressure_score reflects daily
    -- conflict data; it does not, 6 days out of 7.

    SELECT
        week_start_date,
        SUM(events) AS conflict_events,
        SUM(fatalities) AS fatalities
    FROM `{{ var.project_id }}.stg.acled_conflict_events`
    WHERE country = 'Kenya'
    GROUP BY week_start_date

),

lumen AS (

    SELECT
        measurement_date,
        SUM(request_count) AS takedown_requests,
        SUM(item_count) AS takedown_items
    FROM `{{ var.project_id }}.stg.lumen_requests`
    GROUP BY measurement_date

),

google AS (

    SELECT *
    FROM `{{ var.project_id }}.int.google_pressure_periodized`

),

regime AS (

    SELECT
        week_start_date,
        primary_regime,
        confidence_level,
        transition_detected,
        transition_type,
        previous_regime,
        protest_band,
        violence_band,
        suppression_band,
        disorder_band,
        weeks_in_current_regime,
        regime_methodology_version
    FROM `{{ var.project_id }}.intelligence.acled_pressure_regimes`
    WHERE country = 'Kenya'

),

joined AS (

    SELECT
        d.measurement_date,

        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,

        COALESCE(l.takedown_requests,0) AS takedown_requests,
        COALESCE(l.takedown_items,0) AS takedown_items,

        COALESCE(g.google_requests,0) AS google_requests,
        COALESCE(g.requested_items,0) AS requested_items,
        COALESCE(g.legal_removed,0) AS legal_removed,
        COALESCE(g.policy_removed,0) AS policy_removed,
        COALESCE(g.detailed_total,0) AS detailed_total,

        r.primary_regime              AS regime_primary_regime,
        r.confidence_level            AS regime_confidence_level,
        r.transition_detected         AS regime_transition_detected,
        r.transition_type             AS regime_transition_type,
        r.previous_regime             AS regime_previous_regime,
        r.protest_band                AS regime_protest_band,
        r.violence_band               AS regime_violence_band,
        r.suppression_band            AS regime_suppression_band,
        r.disorder_band               AS regime_disorder_band,
        r.weeks_in_current_regime     AS regime_weeks_in_current_regime,
        r.regime_methodology_version  AS regime_methodology_version

    FROM dates d
    LEFT JOIN acled a
        ON DATE_TRUNC(d.measurement_date, WEEK(SATURDAY)) = a.week_start_date
    LEFT JOIN lumen l USING(measurement_date)
    LEFT JOIN google g USING(measurement_date)
    LEFT JOIN regime r
        ON DATE_TRUNC(d.measurement_date, WEEK(SATURDAY)) = r.week_start_date

),

scored AS (

    SELECT
        *,

        ROUND(LOG(1 + conflict_events + (fatalities * 3)),4)
            AS conflict_pressure_score,

        ROUND(LOG(1 + takedown_requests + takedown_items),4)
            AS legal_pressure_score,

        ROUND(LOG(1 + google_requests + detailed_total),4)
            AS platform_pressure_score

    FROM joined

)

SELECT
    measurement_date,

    'Kenya' AS country,
    'KE' AS iso2,

    conflict_events,
    fatalities,

    takedown_requests,
    takedown_items,

    google_requests,
    requested_items,
    legal_removed,
    policy_removed,
    detailed_total,

    conflict_pressure_score,
    legal_pressure_score,
    platform_pressure_score,

    regime_primary_regime,
    regime_confidence_level,
    regime_transition_detected,
    regime_transition_type,
    regime_previous_regime,
    regime_protest_band,
    regime_violence_band,
    regime_suppression_band,
    regime_disorder_band,
    regime_weeks_in_current_regime,
    regime_methodology_version,

    ROUND(
          (conflict_pressure_score * 0.60)
        + (legal_pressure_score * 0.25)
        + (platform_pressure_score * 0.15),
        4
    ) AS composite_pressure_score,

    CASE
        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 6.5
            THEN 'SEVERE'

        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 4.0
            THEN 'ELEVATED'

        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 2.0
            THEN 'MODERATE'

        ELSE 'LOW'
    END AS pressure_level,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM scored
ORDER BY measurement_date