/* @bruin
tags:
  - reporting

name: reporting.mart_pressure_attribution_daily
type: bq.sql
connection: bigquery-default

description: |
  Pressure-attribution decomposition, daily headline layer (ADR-0006;
  fulfills Project Zero Review Recommendation #4).

  One row per calendar date. Decomposes composite_pressure_score into its
  ONLY two arithmetic terms (ADR-0004 weights):

      composite = conflict_pressure_score * 0.75
                + platform_pressure_score * 0.25

  and states, per term, the contribution (score x weight), the share of
  the composite, and -- critically -- the term's REAL temporal grain,
  because neither term is actually day-resolved:

  - conflict_pressure_score is a WEEKLY ACLED aggregate broadcast across
    the 7 days of its Saturday-anchored week (see
    marts.fact_country_pressure_daily's acled CTE).
  - platform_pressure_score is a SEMIANNUAL Google Transparency period
    broadcast across ~6 months of days (see int.google_pressure_periodized).

  Consequently composite_pressure_score is a weekly step function within
  any half-year period, and week-over-week movement is attributable
  exactly via the *_delta_7d columns. Day-to-day movement within a week
  is always zero by construction -- any dashboard reading suggesting
  otherwise is a bug, not a signal.

  WHAT IS DELIBERATELY NOT HERE:
  - No OONI term. OONI measurement does not feed composite_pressure_score
    arithmetically (verified directly against
    marts.fact_country_pressure_daily for ADR-0006 -- the "platform" term
    is Google Transparency, not OONI). OONI evidence for a date lives in
    reporting.mart_pressure_attribution_ooni_daily as corroboration,
    clearly labeled as NOT a composite input.
  - No legal term. Lumen is benched (ADR-0004); legal_pressure_score and
    its synthetic flag are passed through for transparency but carry
    weight 0 and are excluded from contributions/shares.

  attribution_residual = composite - (conflict_contribution +
  platform_contribution) should be rounding noise only (|residual| <
  0.001). A larger residual means the hardcoded weights here have
  drifted from marts.fact_country_pressure_daily's -- keep the two in
  sync (both cite ADR-0004).

  The per-term evidence pointers (conflict_week_start_date,
  platform_period_start) are join keys into the two driver marts:
  reporting.mart_pressure_attribution_conflict_drivers (week grain) and
  reporting.mart_pressure_attribution_platform_drivers (period grain).

owner: civil-liberties-pipeline

depends:
  - marts.fact_country_pressure_daily
  - stg.google_transparency_requests
  - stg.google_transparency_detailed

materialization:
  type: table
  strategy: create+replace

# TD-57 follow-up (2026-07-06): the weights-drift alarm, enforced at
# materialization time rather than display-side. attribution_residual is
# ROUND()ed to 4dp and is rounding noise (<= 0.0001 verified live) while
# the hardcoded 0.75/0.25 weights here agree with
# marts.fact_country_pressure_daily's composite formula (ADR-0004). Any
# row at or above 0.001 means the two sites have drifted -- fail the run
# instead of waiting for a dashboard viewer to notice.
custom_checks:
  - name: attribution_residual_within_rounding
    description: composite minus (conflict + platform contributions) must stay rounding-level; drift means the ADR-0004 weights are out of sync with fact_country_pressure_daily
    query: |
      SELECT COUNTIF(ABS(attribution_residual) >= 0.001)
      FROM `{{ var.project_id }}.reporting.mart_pressure_attribution_daily`
    value: 0

columns:
  - name: measurement_date
    type: date
    description: Calendar date (daily grain, from the fact table).
    checks:
      - name: not_null
      - name: unique

  - name: composite_pressure_score
    type: float
    description: Passed through from marts.fact_country_pressure_daily.
    checks:
      - name: not_null

  - name: conflict_week_start_date
    type: date
    description: |
      Saturday anchor of the ACLED week whose aggregate this date's
      conflict term broadcasts. Join key into
      reporting.mart_pressure_attribution_conflict_drivers.
    checks:
      - name: not_null
@bruin */

-- Google period anchors: replicates int.google_pressure_periodized's
-- period construction EXACTLY (requests' period_date is already a
-- 06-01/12-01 anchor; detailed's period_date is a period-ENDING date
-- normalized via the same month-6/month-12 CASE; anchors unioned, then
-- LEAD gives each period's exclusive end). Keep in sync with that asset
-- -- if its periodization changes, this must change with it, or
-- platform_period_start will stop matching the score being attributed.

WITH detailed_periods AS (

    SELECT DISTINCT
        CASE
            WHEN EXTRACT(MONTH FROM period_date) = 6
                THEN DATE(EXTRACT(YEAR FROM period_date), 6, 1)
            WHEN EXTRACT(MONTH FROM period_date) = 12
                THEN DATE(EXTRACT(YEAR FROM period_date), 12, 1)
        END AS period_start
    FROM `{{ var.project_id }}.stg.google_transparency_detailed`

),

request_periods AS (

    SELECT DISTINCT period_date AS period_start
    FROM `{{ var.project_id }}.stg.google_transparency_requests`

),

periods AS (

    SELECT
        period_start,
        LEAD(period_start) OVER (ORDER BY period_start) AS next_period_start
    FROM (
        SELECT period_start FROM detailed_periods
        WHERE period_start IS NOT NULL
        UNION DISTINCT
        SELECT period_start FROM request_periods
    )

),

fact AS (

    SELECT *
    FROM `{{ var.project_id }}.marts.fact_country_pressure_daily`

),

attributed AS (

    SELECT
        f.measurement_date,
        f.country,
        f.iso2,

        f.composite_pressure_score,
        f.pressure_level,

        -- ── CONFLICT TERM (ACLED, weekly broadcast) ────────────────────
        f.conflict_pressure_score,
        0.75 AS conflict_weight,  -- ADR-0004; keep in sync with fact_country_pressure_daily
        ROUND(f.conflict_pressure_score * 0.75, 4) AS conflict_contribution,
        f.conflict_events,
        f.fatalities,
        DATE_TRUNC(f.measurement_date, WEEK(SATURDAY)) AS conflict_week_start_date,
        'WEEKLY_AGGREGATE_BROADCAST' AS conflict_data_grain,

        -- ── PLATFORM TERM (Google Transparency, semiannual broadcast) ──
        f.platform_pressure_score,
        0.25 AS platform_weight,  -- ADR-0004; keep in sync with fact_country_pressure_daily
        ROUND(f.platform_pressure_score * 0.25, 4) AS platform_contribution,
        f.google_requests,
        f.requested_items,
        f.legal_removed,
        f.policy_removed,
        f.detailed_total,
        p.period_start AS platform_period_start,
        DATE_SUB(p.next_period_start, INTERVAL 1 DAY) AS platform_period_end,
        'SEMIANNUAL_BROADCAST' AS platform_data_grain,

        -- ── LEGAL TERM: benched, weight 0 (ADR-0004) ───────────────────
        f.legal_pressure_score,
        f.legal_pressure_is_synthetic,

        -- ── REGIME OVERLAY (weekly categorical, ADR-0002 step (e)) ─────
        f.regime_primary_regime,
        f.regime_confidence_level,
        f.regime_transition_detected,
        f.regime_transition_type,
        f.regime_previous_regime,
        f.regime_protest_band,
        f.regime_violence_band,
        f.regime_suppression_band,
        f.regime_disorder_band

    FROM fact f
    LEFT JOIN periods p
        ON f.measurement_date >= p.period_start
       AND (p.next_period_start IS NULL
            OR f.measurement_date < p.next_period_start)

)

SELECT
    *,

    ROUND(SAFE_DIVIDE(conflict_contribution, composite_pressure_score), 4)
        AS conflict_share,
    ROUND(SAFE_DIVIDE(platform_contribution, composite_pressure_score), 4)
        AS platform_share,

    ROUND(
        composite_pressure_score
        - (conflict_contribution + platform_contribution),
        4
    ) AS attribution_residual,

    -- Week-over-week movement, attributable exactly per term. LAG(...,7)
    -- is safe because the fact table is built on dim_dates' contiguous
    -- daily spine (one row per date, no gaps).
    ROUND(
        composite_pressure_score
        - LAG(composite_pressure_score, 7)
            OVER (ORDER BY measurement_date),
        4
    ) AS composite_delta_7d,
    ROUND(
        conflict_contribution
        - LAG(conflict_contribution, 7)
            OVER (ORDER BY measurement_date),
        4
    ) AS conflict_contribution_delta_7d,
    ROUND(
        platform_contribution
        - LAG(platform_contribution, 7)
            OVER (ORDER BY measurement_date),
        4
    ) AS platform_contribution_delta_7d,

    'PRESSURE_ATTRIBUTION_V1' AS attribution_methodology_version,
    'pressure_attribution_daily_v1' AS reporting_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM attributed
ORDER BY measurement_date
