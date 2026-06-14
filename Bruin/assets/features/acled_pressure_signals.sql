/* @bruin
name: features.acled_pressure_signals
type: bq.sql
connection: bigquery-default
tags:
  - features
  - features_bq
  - dataset_acled
  - acled_intelligence_phase_1

description: |
  Weekly ACLED physical-pressure signal features.
  Version: ACLED_PRESSURE_SIGNALS_V1

  GRAIN: country × week_start_date
  One row per country-week. No admin1 grain. No event-level grain.

  DEPENDENCY CHAIN:
    stg.acled_conflict_events → int.acled_event_classification
    → features.acled_pressure_signals ← this asset
    → int.acled_pressure_regimes

  ──────────────────────────────────────────────────────────────────────
  SOFT GATING ARCHITECTURE — GOVERNING DESIGN PRINCIPLE
  ──────────────────────────────────────────────────────────────────────
  Signal validity is a two-dimensional question:
    (1) Did pressure exist? → raw counts and pressure indices
    (2) Is statistical inference valid? → z-scores, flags, signal_valid

  Observations (event counts, pressure indices) are ALWAYS emitted when
  events exist. They are never suppressed by baseline conditions.

  Inferences (z-scores) are gated independently per signal family.
  A family z-score is NULL when that family's own validity conditions
  are not met — regardless of whether other families are valid.

  signal_valid is a summary indicator derived from all family-level and
  global quality flags. It is consumed by int.acled_pressure_regimes to
  produce INSUFFICIENT_DATA or LOW_CONFIDENCE regime states.
  It must not be the sole mechanism controlling z-score output.

  ──────────────────────────────────────────────────────────────────────
  PER-FAMILY VALIDITY ARCHITECTURE
  ──────────────────────────────────────────────────────────────────────
  Each signal family has fully independent validity tracking:

    Baseline depth (active weeks):
      protest_active_baseline_weeks
      violence_active_baseline_weeks
      suppression_active_baseline_weeks
      Active = prior weeks where that family's pressure index > 0.
      Distinguishes window rows (not useful) from meaningful activity
      (required for valid z-score). A 12-week window filled with zeros
      has 12 rows but 0 active weeks.

    Sparse baseline flags:
      sparse_protest_baseline_flag
      sparse_violence_baseline_flag
      sparse_suppression_baseline_flag
      Each uses its own family's active-week count.
      Failure in one family does not invalidate another.

    Zero-variance flags:
      protest_zero_variance_flag
      violence_zero_variance_flag
      suppression_zero_variance_flag
      Fires when family stddev < min_meaningful_stddev AND current value
      deviates from baseline. Prevents artefactual z-scores from flat
      baselines. Each family evaluated independently.

    Z-score gating:
      protest_pressure_z requires:
        NOT sparse_protest_baseline_flag
        AND NOT protest_zero_variance_flag
        AND NOT (signal_valid = FALSE due to global conditions)
      Equivalent per-family logic applies to violence and suppression.

  ──────────────────────────────────────────────────────────────────────
  VARIANCE GOVERNANCE
  ──────────────────────────────────────────────────────────────────────
  stddev_floor (PROVISIONAL: 0.10):
    Numerical safety denominator. Prevents division by zero.
    Calibrated for log-scale ACLED indices, not OONI rate-scale.
    OONI floor of 0.001 is invalid here — ACLED indices are unbounded.

  min_meaningful_stddev (PROVISIONAL: 0.15):
    Analytical validity gate. Independent of stddev_floor.
    When family stddev < min_meaningful_stddev, z-score is suppressed
    entirely. Do not use denominator flooring as a substitute.
    Expected calibration target after Kenya analysis: 0.10–0.30.

  ──────────────────────────────────────────────────────────────────────
  METHODOLOGY RISK GOVERNANCE
  ──────────────────────────────────────────────────────────────────────
  high_methodology_risk_flag drives validity gating.
  Derived from methodology_risk_share (events with risk level HIGH).
  Strategic developments dominance is the primary analytical risk.

  ambiguous_event_share is retained as metadata only.
  It does not participate in validity gating.

  ──────────────────────────────────────────────────────────────────────
  CALENDAR SPINE — INTERNAL IMPLEMENTATION
  ──────────────────────────────────────────────────────────────────────
  This asset generates an internal weekly calendar spine.

  PRODUCTION DEPLOYMENT PREREQUISITE:
    Rolling windows require complete weekly continuity. Without a spine,
    weeks with zero events are absent from the source table. Rolling
    windows silently skip those weeks and treat surrounding rows as
    consecutive, producing incorrect baseline calculations.

    The internal spine is correct for Phase 1 single‑country deployment.
    Before multi‑country expansion, extract spine generation to a shared
    upstream asset (stg.acled_calendar_spine) to avoid coupling
    infrastructure to feature computation across multiple country assets.

  ──────────────────────────────────────────────────────────────────────
  DUAL CONTRIBUTION — SUPPRESSION
  ──────────────────────────────────────────────────────────────────────
  Suppression is orthogonal to pressure_domain.
  Derived from is_suppression_marker = TRUE (any domain).
  A PROTEST row with is_suppression_marker = TRUE contributes to:
    - protest_events / protest_pressure_index
    - suppression_events / suppression_intensity_index
  Validated markers: Protest with intervention (9,441 events),
    Arrests (4,199), Excessive force against protesters (2,769).

  ──────────────────────────────────────────────────────────────────────
  DOWNSTREAM CONTRACT — int.acled_pressure_regimes
  ──────────────────────────────────────────────────────────────────────
  MUST:
    - consume signal_valid and per-family flags from this asset
    - produce INSUFFICIENT_DATA regime state when signal_valid = FALSE
    - produce LOW_CONFIDENCE regime state when
      high_methodology_risk_flag
    - consume family-level flags for family-specific regime
      classification

  MUST NOT:
    - recompute z-scores from raw event counts
    - recompute validity thresholds independently
    - treat signal_valid = FALSE as zero pressure
    - suppress regime outputs for weeks with non-zero pressure indices

  Feature layer owns validity assessment.
  Intelligence layer owns regime interpretation.

depends:
  - int.acled_event_classification

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week_start_date
    type: date
    description: ACLED week anchor. Grain is WEEKLY_AGGREGATE.
    checks:
      - name: not_null

  - name: country
    type: string
    description: Country name. Parameterised via {{ var.country }}.
    checks:
      - name: not_null

  - name: iso2
    type: string
    description: ISO 3166-1 alpha-2 country code from {{ var.iso2 }}.
    checks:
      - name: not_null

  - name: data_grain
    type: string
    description: Always WEEKLY_AGGREGATE for this pipeline.
    checks:
      - name: not_null

  # ── RAW COUNTS — always populated regardless of signal_valid ────────
  - name: total_events
    type: integer
    description: Total events across all pressure domains this country-week.

  - name: total_fatalities
    type: integer
    description: Total fatalities across all pressure domains.

  - name: protest_events
    type: integer
    description: Events where pressure_domain = PROTEST.

  - name: protest_fatalities
    type: integer
    description: Fatalities from PROTEST domain events.

  - name: disorder_events
    type: integer
    description: Events where pressure_domain = DISORDER.

  - name: disorder_fatalities
    type: integer
    description: Fatalities from DISORDER domain events.

  - name: violence_events
    type: integer
    description: Events where pressure_domain = VIOLENCE.

  - name: violence_fatalities
    type: integer
    description: Fatalities from VIOLENCE domain events.

  - name: strategic_events
    type: integer
    description: Events where pressure_domain = STRATEGIC.

  - name: suppression_events
    type: integer
    description: |
      Events where is_suppression_marker = TRUE (any pressure_domain).
      Dual-contribution: PROTEST rows with marker TRUE count here AND in
      protest_events simultaneously.

  - name: suppression_fatalities
    type: integer
    description: Fatalities from is_suppression_marker = TRUE events.

  - name: civic_response_events
    type: integer
    description: |
      Events where is_civic_response = TRUE.
      Subset of suppression: physical protest intervention only.

  - name: high_severity_events
    type: integer
    description: Events where is_high_severity = TRUE (HIGH or EXTREME tier).

  - name: event_diversity_index
    type: integer
    description: Count of distinct active pressure_domain values this week.

  # ── PRESSURE INDICES — always populated (soft gating) ───────────────
  - name: protest_pressure_index
    type: float
    description: |
      LOG(1 + protest_events). Preserved regardless of signal_valid.

  - name: disorder_pressure_index
    type: float
    description: |
      LOG(1 + disorder_events). Preserved regardless of signal_valid.

  - name: violence_pressure_index
    type: float
    description: |
      LOG(1 + violence_events) + LOG(1 + violence_fatalities) × 0.50.
      Fatality-weighted. Preserved regardless of signal_valid.

  - name: suppression_intensity_index
    type: float
    description: |
      LOG(1 + suppression_events). Derived from is_suppression_marker.
      Orthogonal to pressure_domain. Preserved regardless of signal_valid.

  - name: escalation_velocity_score
    type: float
    description: |
      Week-on-week delta of protest_pressure_index.
      Preserved regardless of signal_valid.
      NULL only for the first week in country history.

  - name: pressure_conversion_rate
    type: float
    description: |
      (disorder_events + violence_events) / NULLIF(protest_events, 0).
      Ratio of two raw counts. Observational metric.
      Preserved regardless of signal_valid.
      NULL when protest_events = 0.

  # ── Z-SCORES — per-family gated ──────────────────────────────────────
  - name: protest_pressure_z
    type: float
    description: |
      Z-score of protest_pressure_index vs 12-week active baseline.
      NULL when signal_valid = FALSE
      OR sparse_protest_baseline_flag = TRUE
      OR protest_zero_variance_flag = TRUE.
      Gated by protest family conditions only.

  - name: violence_pressure_z
    type: float
    description: |
      Z-score of violence_pressure_index vs 12-week active baseline.
      NULL when signal_valid = FALSE
      OR sparse_violence_baseline_flag = TRUE
      OR violence_zero_variance_flag = TRUE.
      Gated by violence family conditions only.

  - name: suppression_z
    type: float
    description: |
      Z-score of suppression_intensity_index vs 12-week active baseline.
      NULL when signal_valid = FALSE
      OR sparse_suppression_baseline_flag = TRUE
      OR suppression_zero_variance_flag = TRUE.
      Gated by suppression family conditions only.

  # ── BASELINE METADATA ────────────────────────────────────────────────
  - name: protest_baseline_12w
    type: float
    description: 12-week rolling mean of protest_pressure_index.

  - name: violence_baseline_12w
    type: float
    description: 12-week rolling mean of violence_pressure_index.

  - name: suppression_baseline_12w
    type: float
    description: 12-week rolling mean of suppression_intensity_index.

  - name: protest_active_baseline_weeks
    type: integer
    description: |
      Prior weeks in 12w window where protest_pressure_index > 0.
      Counts meaningful activity weeks, not just populated rows.
      A window of 12 consecutive zero-event weeks = 0 active weeks.

  - name: violence_active_baseline_weeks
    type: integer
    description: |
      Prior weeks in 12w window where violence_pressure_index > 0.
      Independent of protest_active_baseline_weeks.

  - name: suppression_active_baseline_weeks
    type: integer
    description: |
      Prior weeks in 12w window where suppression_intensity_index > 0.
      Independent of protest and violence baseline counts.

  # ── PER-FAMILY SPARSE BASELINE FLAGS ─────────────────────────────────
  - name: sparse_protest_baseline_flag
    type: boolean
    description: |
      TRUE when protest_active_baseline_weeks < min_active_baseline_weeks.
      PROVISIONAL threshold: 4.
      Gates protest_pressure_z independently of other families.
    checks:
      - name: not_null

  - name: sparse_violence_baseline_flag
    type: boolean
    description: |
      TRUE when violence_active_baseline_weeks < min_active_baseline_weeks.
      PROVISIONAL threshold: 4.
      Gates violence_pressure_z independently of other families.
    checks:
      - name: not_null

  - name: sparse_suppression_baseline_flag
    type: boolean
    description: |
      TRUE when suppression_active_baseline_weeks < min_active_baseline_weeks.
      PROVISIONAL threshold: 4.
      Gates suppression_z independently of other families.
    checks:
      - name: not_null

  # ── PER-FAMILY ZERO-VARIANCE FLAGS ───────────────────────────────────
  - name: protest_zero_variance_flag
    type: boolean
    description: |
      TRUE when protest stddev_12w < min_meaningful_stddev AND
      protest_pressure_index deviates materially from its baseline.
      Suppresses protest_pressure_z to prevent artefactual z-scores
      from flat baselines. Evaluated independently of other families.
    checks:
      - name: not_null

  - name: violence_zero_variance_flag
    type: boolean
    description: |
      TRUE when violence stddev_12w < min_meaningful_stddev AND
      violence_pressure_index deviates materially from its baseline.
      Evaluated independently of protest and suppression families.
    checks:
      - name: not_null

  - name: suppression_zero_variance_flag
    type: boolean
    description: |
      TRUE when suppression stddev_12w < min_meaningful_stddev AND
      suppression_intensity_index deviates materially from baseline.
      Evaluated independently of protest and violence families.
    checks:
      - name: not_null

  # ── GLOBAL COMPOSITE FLAGS ───────────────────────────────────────────
  - name: zero_variance_flag
    type: boolean
    description: |
      TRUE when any per-family zero_variance_flag is TRUE.
      Global audit summary. Per-family flags drive z-score gating.
    checks:
      - name: not_null

  - name: low_event_density_flag
    type: boolean
    description: |
      TRUE when total_events < min_events_per_week.
      PROVISIONAL threshold: 3. Calibrate against Kenya p10.
    checks:
      - name: not_null

  - name: high_methodology_risk_flag
    type: boolean
    description: |
      TRUE when methodology_risk_share > max_methodology_risk_share.
      Strategic developments dominance is the primary analytical risk.
      PROVISIONAL threshold: 0.40. Replaces ambiguity-based gating.
    checks:
      - name: not_null

  - name: signal_valid
    type: boolean
    description: |
      Summary validity indicator. TRUE when all family-level and global
      quality conditions are satisfied. Does NOT suppress pressure
      indices (soft gating preserved). Does contribute to z-score gating
      alongside per-family flags.
      int.acled_pressure_regimes must consume this field.
      Must not be recomposed independently in downstream assets.
    checks:
      - name: not_null

  # ── QUALITY METADATA ─────────────────────────────────────────────────
  - name: low_event_density_rate
    type: float
    description: Share of source rows flagged as low_event_density by staging.

  - name: population_exposure_missing_rate
    type: float
    description: |
      Share of source rows missing population_exposure.
      Systematically high pre-2017. Not a quality failure.

  - name: ambiguous_event_share
    type: float
    description: |
      Share of events with classification_confidence = LOW.
      Metadata only. Does not participate in validity gating.

  - name: methodology_risk_share
    type: float
    description: |
      Share of events with methodology_risk_level = HIGH.
      Feeds high_methodology_risk_flag. Primary quality gate input.

  # ── AUDIT ─────────────────────────────────────────────────────────────
  - name: guardrail_config_json
    type: string
    description: |
      Serialised threshold values active for this row.
      Derived directly from feature_thresholds CTE values.
      All values are PROVISIONAL_CALIBRATION_VALUES.
      Enables retrospective methodology audit per row.
    checks:
      - name: not_null

  - name: feature_version
    type: string
    description: ACLED_PRESSURE_SIGNALS_V1.
    checks:
      - name: not_null

  - name: classification_methodology_version
    type: string
    description: Passed through from int.acled_event_classification.

  - name: severity_methodology_version
    type: string
    description: Passed through from int.acled_event_classification.

  - name: computed_at
    type: timestamp
    description: Pipeline execution timestamp.
    checks:
      - name: not_null
@bruin */

-- ═══════════════════════════════════════════════════════════════════════════
-- FEATURE THRESHOLDS
-- All values: PROVISIONAL_CALIBRATION_VALUES
-- Update values here only. guardrail_config_json serialises per row.
--
-- stddev_floor          → numerical safety. Prevents division by zero.
--                          Calibrated for log-scale ACLED indices.
--                          Do NOT inherit OONI value of 0.001.
--
-- min_meaningful_stddev → analytical gate. Distinct from stddev_floor.
--                          When family stddev < this value, z-score
--                          is suppressed entirely. Not floored.
--
-- Calibration target after Kenya empirical analysis: 0.10–0.30.
-- Run APPROX_QUANTILES on rolling stddev distributions before prod.
-- ═══════════════════════════════════════════════════════════════════════════
WITH feature_thresholds AS (
    SELECT
        3    AS min_events_per_week,       -- PROVISIONAL: replace with Kenya p10
        4    AS min_active_baseline_weeks, -- PROVISIONAL: active-activity weeks required
        0.10 AS stddev_floor,              -- PROVISIONAL: log-scale floor, not OONI value
        0.15 AS min_meaningful_stddev,    -- PROVISIONAL: analytical suppression threshold
        0.40 AS max_methodology_risk_share -- PROVISIONAL: Strategic events dominance gate
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CALENDAR SPINE
-- Generates a complete weekly sequence for the target country.
-- Ensures rolling windows operate on calendar time, not event-presence rows.
-- Weeks with zero events are represented as explicit zero-fill rows.
--
-- PHASE 1 TECHNICAL DEBT:
-- This spine is internal to this asset. Before multi-country expansion,
-- extract to a shared stg.acled_calendar_spine asset to avoid coupling
-- infrastructure logic to feature computation across country assets.
-- ═══════════════════════════════════════════════════════════════════════════
observation_window AS (
    SELECT
        MIN(week_start_date) AS first_week,
        MAX(week_start_date) AS last_week
    FROM `{{ var.project_id }}.int.acled_event_classification`
    WHERE country = '{{ var.country }}'
),

calendar_spine AS (
    SELECT DATE_ADD(first_week, INTERVAL n WEEK) AS week_start_date
    FROM observation_window
    CROSS JOIN UNNEST(
        GENERATE_ARRAY(0, DATE_DIFF(last_week, first_week, WEEK))
    ) AS n
),

-- ═══════════════════════════════════════════════════════════════════════════
-- SOURCE
-- Single read. Filters to target country and valid parse state only.
-- ═══════════════════════════════════════════════════════════════════════════
source AS (
    SELECT
        week_start_date,
        data_grain,
        country,
        pressure_domain,
        is_suppression_marker,
        is_civic_response,
        is_high_severity,
        is_ambiguous_event,
        methodology_risk_level,
        events,
        fatalities,
        population_exposure,
        population_exposure_missing,
        low_event_density,
        classification_methodology_version,
        severity_methodology_version
    FROM `{{ var.project_id }}.int.acled_event_classification`
    WHERE country = '{{ var.country }}'
      AND week_parse_failed = FALSE
),

-- ═══════════════════════════════════════════════════════════════════════════
-- SINGLE AGGREGATION PASS
-- All signal families derived in one GROUP BY against the calendar spine.
-- No self-joins. No repeated source scans.
-- Calendar spine LEFT JOIN ensures zero-fill rows for inactive weeks.
-- Suppression uses is_suppression_marker, not pressure_domain.
-- Dual-contribution: PROTEST rows with is_suppression_marker = TRUE
-- increment both protest_events and suppression_events.
-- ═══════════════════════════════════════════════════════════════════════════
weekly_aggregated AS (
    SELECT
        cs.week_start_date,
        '{{ var.country }}' AS country,
        '{{ var.iso2 }}'    AS iso2,
        'WEEKLY_AGGREGATE'  AS data_grain,

        ANY_VALUE(s.classification_methodology_version) AS classification_methodology_version,
        ANY_VALUE(s.severity_methodology_version)       AS severity_methodology_version,

        -- totals
        COALESCE(SUM(s.events), 0)     AS total_events,
        COALESCE(SUM(s.fatalities), 0) AS total_fatalities,

        -- protest
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'PROTEST'  THEN s.events     ELSE 0 END), 0) AS protest_events,
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'PROTEST'  THEN s.fatalities ELSE 0 END), 0) AS protest_fatalities,

        -- disorder
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'DISORDER' THEN s.events     ELSE 0 END), 0) AS disorder_events,
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'DISORDER' THEN s.fatalities ELSE 0 END), 0) AS disorder_fatalities,

        -- violence
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'VIOLENCE' THEN s.events     ELSE 0 END), 0) AS violence_events,
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'VIOLENCE' THEN s.fatalities ELSE 0 END), 0) AS violence_fatalities,

        -- strategic
        COALESCE(SUM(CASE WHEN s.pressure_domain = 'STRATEGIC' THEN s.events    ELSE 0 END), 0) AS strategic_events,

        -- suppression: from is_suppression_marker, NOT pressure_domain
        COALESCE(SUM(CASE WHEN s.is_suppression_marker THEN s.events     ELSE 0 END), 0) AS suppression_events,
        COALESCE(SUM(CASE WHEN s.is_suppression_marker THEN s.fatalities ELSE 0 END), 0) AS suppression_fatalities,

        -- civic response (subset of suppression)
        COALESCE(SUM(CASE WHEN s.is_civic_response THEN s.events ELSE 0 END), 0) AS civic_response_events,

        -- severity
        COALESCE(SUM(CASE WHEN s.is_high_severity THEN s.events ELSE 0 END), 0) AS high_severity_events,

        -- event diversity
        COALESCE(COUNT(DISTINCT CASE WHEN s.events > 0 THEN s.pressure_domain END), 0) AS event_diversity_index,

        -- quality metadata
        COALESCE(SAFE_DIVIDE(
            COUNTIF(s.low_event_density),
            COUNT(s.events)
        ), 0) AS low_event_density_rate,

        COALESCE(SAFE_DIVIDE(
            COUNTIF(s.population_exposure_missing),
            COUNT(s.events)
        ), 0) AS population_exposure_missing_rate,

        -- ambiguity: metadata only, not a validity gate
        COALESCE(SAFE_DIVIDE(
            SUM(CASE WHEN s.is_ambiguous_event THEN s.events ELSE 0 END),
            NULLIF(SUM(s.events), 0)
        ), 0) AS ambiguous_event_share,

        -- methodology risk: validity gate input
        COALESCE(SAFE_DIVIDE(
            SUM(CASE WHEN s.methodology_risk_level = 'HIGH' THEN s.events ELSE 0 END),
            NULLIF(SUM(s.events), 0)
        ), 0) AS methodology_risk_share

    FROM calendar_spine cs
    LEFT JOIN source s
        ON cs.week_start_date = s.week_start_date
    GROUP BY cs.week_start_date
),

-- ═══════════════════════════════════════════════════════════════════════════
-- PRESSURE INDICES
-- Log-scaled. Computed before rolling windows so baselines are comparable.
-- Soft gating: all indices preserved regardless of signal_valid.
-- LOG(1 + 0) = 0 for zero-fill weeks from calendar spine.
-- pressure_conversion_rate is an observational ratio of raw counts.
-- It is preserved regardless of signal_valid.
-- ═══════════════════════════════════════════════════════════════════════════
with_indices AS (
    SELECT
        *,
        ROUND(LOG(1 + protest_events), 4)    AS protest_pressure_index,
        ROUND(LOG(1 + disorder_events), 4)   AS disorder_pressure_index,
        ROUND(
            LOG(1 + violence_events) + LOG(1 + violence_fatalities) * 0.50,
            4
        ) AS violence_pressure_index,
        ROUND(LOG(1 + suppression_events), 4) AS suppression_intensity_index,
        SAFE_DIVIDE(
            CAST(disorder_events + violence_events AS FLOAT64),
            NULLIF(protest_events, 0)
        ) AS pressure_conversion_rate
    FROM weekly_aggregated
),

-- ═══════════════════════════════════════════════════════════════════════════
-- ROLLING BASELINES — 12-week prior window, all three families independent
-- ROWS BETWEEN operates on complete calendar-spine sequence.
-- COUNTIF(index > 0) counts active weeks, not just populated rows.
-- A 12-row window filled with zeros returns 0 active weeks.
-- ═══════════════════════════════════════════════════════════════════════════
with_baselines AS (
    SELECT
        *,

        -- protest family
        AVG(protest_pressure_index)         OVER w12 AS protest_baseline_12w,
        STDDEV_SAMP(protest_pressure_index) OVER w12 AS protest_stddev_12w,
        COUNTIF(protest_pressure_index > 0) OVER w12 AS protest_active_baseline_weeks,

        -- violence family
        AVG(violence_pressure_index)         OVER w12 AS violence_baseline_12w,
        STDDEV_SAMP(violence_pressure_index) OVER w12 AS violence_stddev_12w,
        COUNTIF(violence_pressure_index > 0) OVER w12 AS violence_active_baseline_weeks,

        -- suppression family
        AVG(suppression_intensity_index)         OVER w12 AS suppression_baseline_12w,
        STDDEV_SAMP(suppression_intensity_index) OVER w12 AS suppression_stddev_12w,
        COUNTIF(suppression_intensity_index > 0) OVER w12 AS suppression_active_baseline_weeks,

        -- escalation velocity: week-on-week delta in protest pressure
        -- observational metric, preserved regardless of signal_valid
        ROUND(
            protest_pressure_index - LAG(protest_pressure_index) OVER (
                PARTITION BY country ORDER BY week_start_date
            ),
            4
        ) AS escalation_velocity_score

    FROM with_indices
    WINDOW w12 AS (
        PARTITION BY country
        ORDER BY week_start_date
        ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING
    )
),

-- ═══════════════════════════════════════════════════════════════════════════
-- EFFECTIVE VARIANCE + THRESHOLD JOIN
-- stddev_floor          → numerical safety. Used only as z-score denominator.
-- min_meaningful_stddev → analytical gate. Suppresses z-score entirely.
-- These are different mechanisms and must not be conflated.
-- ═══════════════════════════════════════════════════════════════════════════
with_variance AS (
    SELECT
        b.*,
        t.min_events_per_week,
        t.min_active_baseline_weeks,
        t.stddev_floor,
        t.min_meaningful_stddev,
        t.max_methodology_risk_share,

        -- effective stddev: floor applied for numerical safety only
        -- used in z-score denominator after family gate clears
        GREATEST(COALESCE(b.protest_stddev_12w, 0),    t.stddev_floor) AS protest_stddev_eff,
        GREATEST(COALESCE(b.violence_stddev_12w, 0),   t.stddev_floor) AS violence_stddev_eff,
        GREATEST(COALESCE(b.suppression_stddev_12w, 0), t.stddev_floor) AS suppression_stddev_eff

    FROM with_baselines b
    CROSS JOIN feature_thresholds t
),

-- ═══════════════════════════════════════════════════════════════════════════
-- PER-FAMILY VALIDITY FLAGS
-- Each flag evaluates its own family only.
-- No family's validity depends on another family's conditions.
-- ═══════════════════════════════════════════════════════════════════════════
with_flags AS (
    SELECT
        *,

        -- global density gate
        total_events < min_events_per_week AS low_event_density_flag,

        -- per-family sparse baseline flags
        -- active-week count: not row count
        COALESCE(protest_active_baseline_weeks, 0)    < min_active_baseline_weeks AS sparse_protest_baseline_flag,
        COALESCE(violence_active_baseline_weeks, 0)   < min_active_baseline_weeks AS sparse_violence_baseline_flag,
        COALESCE(suppression_active_baseline_weeks, 0) < min_active_baseline_weeks AS sparse_suppression_baseline_flag,

        -- per-family zero-variance flags
        -- fires when stddev < min_meaningful_stddev AND current deviates
        -- this is the analytical suppression gate, not the numerical floor
        (
            COALESCE(protest_stddev_12w, 0) < min_meaningful_stddev
            AND ABS(
                protest_pressure_index
                - COALESCE(protest_baseline_12w, protest_pressure_index)
            ) > min_meaningful_stddev
        ) AS protest_zero_variance_flag,

        (
            COALESCE(violence_stddev_12w, 0) < min_meaningful_stddev
            AND ABS(
                violence_pressure_index
                - COALESCE(violence_baseline_12w, violence_pressure_index)
            ) > min_meaningful_stddev
        ) AS violence_zero_variance_flag,

        (
            COALESCE(suppression_stddev_12w, 0) < min_meaningful_stddev
            AND ABS(
                suppression_intensity_index
                - COALESCE(suppression_baseline_12w, suppression_intensity_index)
            ) > min_meaningful_stddev
        ) AS suppression_zero_variance_flag,

        -- methodology risk gate
        COALESCE(methodology_risk_share, 0) > max_methodology_risk_share AS high_methodology_risk_flag

    FROM with_variance
),

-- ═══════════════════════════════════════════════════════════════════════════
-- COMPOSITE VALIDITY GATE
-- signal_valid is a summary indicator derived from all per-family flags.
-- It is NOT the sole z-score gate — per-family flags gate independently.
-- Composed here and consumed by int.acled_pressure_regimes.
-- Must not be recomposed downstream.
-- ═══════════════════════════════════════════════════════════════════════════
with_signal_valid AS (
    SELECT
        *,

        -- global zero-variance summary: OR of family flags
        (
            protest_zero_variance_flag
            OR violence_zero_variance_flag
            OR suppression_zero_variance_flag
        ) AS zero_variance_flag,

        -- signal_valid: summary of all validity conditions
        NOT (
            low_event_density_flag
            OR sparse_protest_baseline_flag
            OR sparse_violence_baseline_flag
            OR sparse_suppression_baseline_flag
            OR protest_zero_variance_flag
            OR violence_zero_variance_flag
            OR suppression_zero_variance_flag
            OR high_methodology_risk_flag
        ) AS signal_valid

    FROM with_flags
)

-- ═══════════════════════════════════════════════════════════════════════════
-- FINAL SELECT
-- SOFT GATING:
--   Raw counts: always populated
--   Pressure indices: always populated
--   Z-scores: per-family gated
--
-- Z-SCORE GATING per family:
--   Uses signal_valid AND family-specific sparse + variance flags.
--   A globally valid signal does not emit a z-score for a family
--   whose own validity conditions are not met.
--   A family failure does not suppress other families' z-scores.
-- ═══════════════════════════════════════════════════════════════════════════
SELECT
    -- grain
    week_start_date,
    country,
    iso2,
    data_grain,

    -- raw counts (always populated)
    total_events,
    total_fatalities,
    protest_events,
    protest_fatalities,
    disorder_events,
    disorder_fatalities,
    violence_events,
    violence_fatalities,
    strategic_events,
    suppression_events,
    suppression_fatalities,
    civic_response_events,
    high_severity_events,
    event_diversity_index,

    -- pressure indices (always populated — soft gating)
    protest_pressure_index,
    disorder_pressure_index,
    violence_pressure_index,
    suppression_intensity_index,
    escalation_velocity_score,
    ROUND(pressure_conversion_rate, 4) AS pressure_conversion_rate,

    -- z-scores (per-family gated)

    -- protest: gated by protest family conditions
    CASE
        WHEN signal_valid
            AND NOT sparse_protest_baseline_flag
            AND NOT protest_zero_variance_flag
        THEN ROUND(SAFE_DIVIDE(
            protest_pressure_index - COALESCE(protest_baseline_12w, 0),
            protest_stddev_eff
        ), 4)
        ELSE NULL
    END AS protest_pressure_z,

    -- violence: gated by violence family conditions
    CASE
        WHEN signal_valid
            AND NOT sparse_violence_baseline_flag
            AND NOT violence_zero_variance_flag
        THEN ROUND(SAFE_DIVIDE(
            violence_pressure_index - COALESCE(violence_baseline_12w, 0),
            violence_stddev_eff
        ), 4)
        ELSE NULL
    END AS violence_pressure_z,

    -- suppression: gated by suppression family conditions
    CASE
        WHEN signal_valid
            AND NOT sparse_suppression_baseline_flag
            AND NOT suppression_zero_variance_flag
        THEN ROUND(SAFE_DIVIDE(
            suppression_intensity_index - COALESCE(suppression_baseline_12w, 0),
            suppression_stddev_eff
        ), 4)
        ELSE NULL
    END AS suppression_z,

    -- baseline metadata
    ROUND(protest_baseline_12w, 4)     AS protest_baseline_12w,
    ROUND(violence_baseline_12w, 4)    AS violence_baseline_12w,
    ROUND(suppression_baseline_12w, 4) AS suppression_baseline_12w,

    protest_active_baseline_weeks,
    violence_active_baseline_weeks,
    suppression_active_baseline_weeks,

    -- per-family sparse baseline flags
    sparse_protest_baseline_flag,
    sparse_violence_baseline_flag,
    sparse_suppression_baseline_flag,

    -- per-family zero-variance flags
    protest_zero_variance_flag,
    violence_zero_variance_flag,
    suppression_zero_variance_flag,

    -- global composite flags
    zero_variance_flag,
    low_event_density_flag,
    high_methodology_risk_flag,
    signal_valid,

    -- quality metadata
    ROUND(low_event_density_rate, 4)           AS low_event_density_rate,
    ROUND(population_exposure_missing_rate, 4)  AS population_exposure_missing_rate,
    ROUND(ambiguous_event_share, 4)            AS ambiguous_event_share,
    ROUND(methodology_risk_share, 4)           AS methodology_risk_share,

    -- audit
    TO_JSON_STRING(STRUCT(
        min_events_per_week,
        min_active_baseline_weeks,
        stddev_floor,
        min_meaningful_stddev,
        max_methodology_risk_share,
        'PROVISIONAL_CALIBRATION_VALUES'  AS calibration_status,
        'INTERNAL_CALENDAR_SPINE'         AS spine_architecture,
        'EXTRACT_BEFORE_MULTI_COUNTRY'    AS spine_debt
    )) AS guardrail_config_json,

    'ACLED_PRESSURE_SIGNALS_V1' AS feature_version,

    COALESCE(
        classification_methodology_version,
        'ACLED_INTELLIGENCE_FRAMEWORK_V1'
    ) AS classification_methodology_version,

    COALESCE(
        severity_methodology_version,
        'FATALITY_ONLY_V1'
    ) AS severity_methodology_version,

    CURRENT_TIMESTAMP() AS computed_at

FROM with_signal_valid
ORDER BY week_start_date;