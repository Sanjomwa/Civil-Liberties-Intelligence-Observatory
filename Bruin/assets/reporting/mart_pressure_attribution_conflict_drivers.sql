/* @bruin
tags:
  - reporting

name: reporting.mart_pressure_attribution_conflict_drivers
type: bq.sql
connection: bigquery-default

description: |
  Pressure-attribution decomposition, conflict evidence layer (ADR-0006;
  fulfills Project Zero Review Recommendation #4).

  GRAIN: one row per source row of int.acled_event_classification for the
  target country -- week_start_date x admin1 x event_type x sub_event_type
  (x disorder_type), i.e. ACLED's own weekly-aggregate grain, preserved
  verbatim rather than re-aggregated. This is deliberate: the point of
  this mart is traceability to the specific classified ACLED rows behind
  a week's conflict score, so nothing is grouped away. severity_tier,
  classification_confidence, methodology_risk_level, and
  classification_note keep their exact per-row meaning.

  ATTRIBUTION ARITHMETIC:
  conflict_pressure_score = LOG(1 + events + fatalities*3), computed over
  the week's country total in marts.fact_country_pressure_daily (keep the
  3x fatality weighting in sync with that asset). The LOG is nonlinear,
  so per-row shares of the *score* would be fabricated precision. What IS
  exact: each row's share of the score's linear argument
  ("intensity mass" = events + 3*fatalities). weekly_intensity_share is
  therefore labeled a share of the week's pre-log conflict intensity
  mass, never a share of the score itself.

  This mart answers: "which classified ACLED rows -- what type of event,
  where, how severe, at what classification confidence -- made up this
  week's conflict pressure input." Join from
  reporting.mart_pressure_attribution_daily via conflict_week_start_date
  = week_start_date.

  Remember the grain warning that applies to everything ACLED-derived
  here (stg.acled_conflict_events): rows are weekly aggregates anchored
  to Saturday; event_date is NULL by design; nothing here distinguishes
  which DAY within the week an event happened.

owner: civil-liberties-pipeline

depends:
  - int.acled_event_classification

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week_start_date
    type: date
    description: Saturday anchor of the ACLED week (weekly-aggregate grain).
    checks:
      - name: not_null

  - name: event_type
    type: string
    description: ACLED top-level event classification, verbatim.
    checks:
      - name: not_null

  - name: weekly_intensity_share
    type: float
    description: |
      This row's share of the week's pre-log conflict intensity mass
      (events + 3*fatalities), across all of the country's rows that
      week. Shares within a week sum to 1. NOT a share of the (log-scale)
      conflict_pressure_score.
@bruin */

WITH classified AS (

    SELECT
        week_start_date,
        data_grain,
        country,
        admin1,
        event_type,
        sub_event_type,
        disorder_type,
        events,
        fatalities,

        pressure_domain,
        is_suppression_marker,
        is_civic_response,
        severity_tier,
        is_high_severity,
        classification_confidence,
        is_ambiguous_event,
        methodology_risk_level,
        classification_note,
        classification_methodology_version,

        population_exposure_missing,
        low_event_density,

        id AS acled_source_id,

        -- Keep the 3x fatality weighting in sync with
        -- marts.fact_country_pressure_daily's conflict_pressure_score
        -- (LOG(1 + conflict_events + fatalities*3)).
        events + (fatalities * 3) AS intensity_mass

    FROM `{{ var.project_id }}.int.acled_event_classification`
    WHERE country = '{{ var.country }}'

)

SELECT
    *,

    SUM(intensity_mass) OVER (PARTITION BY week_start_date)
        AS week_intensity_mass,
    SUM(events) OVER (PARTITION BY week_start_date)
        AS week_conflict_events,
    SUM(fatalities) OVER (PARTITION BY week_start_date)
        AS week_fatalities,

    ROUND(
        SAFE_DIVIDE(
            intensity_mass,
            SUM(intensity_mass) OVER (PARTITION BY week_start_date)
        ),
        4
    ) AS weekly_intensity_share,

    ROW_NUMBER() OVER (
        PARTITION BY week_start_date
        ORDER BY intensity_mass DESC, admin1, event_type, sub_event_type
    ) AS weekly_intensity_rank,

    'PRESSURE_ATTRIBUTION_V1' AS attribution_methodology_version,
    'pressure_attribution_conflict_drivers_v1' AS reporting_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM classified
ORDER BY week_start_date, weekly_intensity_rank
