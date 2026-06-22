/* @bruin
name: intelligence.acled_pressure_regimes
type: bq.sql
connection: bigquery-default
tags:
  - intelligence
  - intelligence_bq
  - dataset_acled
  - acled_intelligence_phase_1

description: |
  ACLED Physical Pressure Regime Classification.
  Specification: ACLED Pressure Regime Specification Stack v1.1
  Governance: ACLED Pressure Regime Taxonomy v1 (frozen doctrine)
  Decision logic: ACLED Pressure Regime Decision Engine Specification v1
  Implementation: ACLED Pressure Regime Implementation Specification v1
  Validation: ACLED Pressure Regime Reference Test Suite & Implementation Contract v1

  GRAIN: country × week_start_date
  One row per country-week.

  UPSTREAM: features.acled_pressure_signals
  DOWNSTREAM: AI narrative layer, reporting marts, Streamlit dashboards

  ARCHITECTURE FREEZE: ACTIVE as of June 2026. No regime, hierarchy, or
  structural changes permitted without architecture review and
  specification version increment.

  MATERIALIZATION NOTE:
  This asset uses a merge-or-replace strategy against a persistent output
  table (intelligence.acled_regime_history) to support the self-referential
  lag join required for persistence state tracking. A create-and-replace
  strategy MUST NOT be used — it destroys prior output before new output is
  complete, causing NULL persistence state for all rows.

  EXECUTION CONTRACT (AUTHORITATIVE):
  This asset is designed and MUST be invoked as exactly:

      one country  ×  one new week  ×  one execution

  Multi-week backfills for a single country MUST be executed as N
  sequential single-week invocations, each fully merged into
  intelligence.acled_pressure_regimes before the next week's invocation
  begins.

  RATIONALE:
  The self-referential lag join in CTE-03 (persistence_context) reads ONLY
  from the already-materialised output table as it exists BEFORE this
  execution begins — it cannot see rows computed earlier in the same
  execution. If multiple new weeks for one country are present in
  source_features for a single execution, every week after the first will
  find no corresponding row in the output table for its immediate
  predecessor and will fall back to first-observation defaults
  (prior_regime_state = 'STABLE', is_first_observation_week = TRUE, all
  counters reset to 0 / FALSE). This silently affects:
    - transition_detected (forced FALSE, reported as transition_type INITIAL)
    - weeks_in_current_regime (resets to 1)
    - exit persistence for CRISIS / ESCALATION / REPRESSION (cannot hold)
    - validity gap continuation for CRISIS / ESCALATION (cannot hold)
    - entry persistence for MOBILISATION / CONTESTATION / REPRESSION /
      CONFLICT (cannot be satisfied across batch-internal weeks)

  This failure mode produces NO error and NO NULL output (Rule 5 is still
  satisfied), and is therefore invisible to standard data-quality checks.
  It can only be detected via anomalous transition_detected = FALSE runs
  and weeks_in_current_regime = 1 resets across a backfill range.

  This is an ACCEPTED OPERATIONAL CONSTRAINT of the current architecture,
  NOT a defect, and is NOT being redesigned as part of implementation
  hardening. Any orchestration that performs historical backfill or
  recovery MUST enforce strictly sequential single-week invocations with
  merge completion between weeks.

  BLOCKER RESOLUTIONS IMPLEMENTED (v1.1):
  BLOCKER-001: Zero variance downgrade = exactly -1 level per
               dominant-family flag, cumulative. See CTE-15.
  BLOCKER-002: stable_precheck_passes=FALSE + no fallback activation →
               STABLE + INSUFFICIENT_DATA. No directional regime from
               INDEX_ACTIVE alone. See CTE-10 Step 7 Case C and CTE-14.
  BLOCKER-003: CONTESTATION persistence waived for {MOBILISATION,
               CONTESTATION, ESCALATION, CRISIS}. Required for {STABLE,
               CONFLICT, REPRESSION}. See CTE-09.
  BLOCKER-004: CRISIS fallback: fallback-active families treated as SEVERE
               only during CRISIS evaluation. Retain UNKNOWN band
               everywhere else. See CTE-08 and CTE-10 Step 1.

  IMPLEMENTATION HARDENING NOTES (this revision):
  - CTE-10 Step 1 (crisis_conditions_met): corrected parenthesization so
    the expression unambiguously represents
    (Condition 1a) OR (Condition 1b) OR (Condition 1c), matching the
    documented CRISIS-first evaluation order (Rule 4). This is a
    correction to match documented/specified behaviour, not a logic
    change.
  - CTE-11 / CTE-16: hierarchy ordinal mapping (CRISIS=7 ... STABLE=1) is
    now computed once per needed regime value and reused, instead of
    being re-derived inline multiple times. No output values change.
  - Added inline comments documenting BLOCKER-002 wiring, the
    coexistence of exit-persistence and validity-gap continuation flags,
    the intentionally-redundant OR in the duration computation, and the
    persistence/execution-contract assumptions.
  - CTE-02 (source_features): added optional target_week filter to support
    sequential historical backfill via backfill_acled_pressure_regimes.py.
    When target_week = '' (the default), behaviour is IDENTICAL to all
    prior versions of this asset. No classification logic changes.
    target_week is declared in pipeline.yml (variables block) — NOT in
    this asset's @bruin header (Bruin does not support per-asset variable
    declarations; variables are pipeline-scoped).

depends:
  - features.acled_pressure_signals

materialization:
  type: table
  strategy: merge

columns:
  - name: week_start_date
    type: date
    description: ACLED week anchor. Grain is WEEKLY_AGGREGATE.
    primary_key: true
    checks:
      - name: not_null

  - name: country
    type: string
    primary_key: true
    checks:
      - name: not_null

  - name: iso2
    type: string
    checks:
      - name: not_null

  - name: data_grain
    type: string

  - name: primary_regime
    type: string
    description: |
      Assigned regime state. One of: STABLE / MOBILISATION / CONTESTATION /
      ESCALATION / CRISIS / REPRESSION / CONFLICT
    checks:
      - name: not_null

  - name: confidence_level
    type: string
    description: HIGH / MEDIUM / LOW / INSUFFICIENT_DATA
    checks:
      - name: not_null

  - name: methodology_caveat_required
    type: boolean

  - name: transition_detected
    type: boolean
    checks:
      - name: not_null

  - name: previous_regime
    type: string

  - name: regime_duration_weeks
    type: integer

  - name: transition_type
    type: string

  - name: transition_significance
    type: string

  - name: transition_confidence
    type: string

  - name: escalation_entry_pathway
    type: string

  - name: secondary_regime_characteristics
    type: string

  - name: pre_transition_flag
    type: boolean

  - name: pre_transition_target
    type: string

  - name: regime_continuation_flag
    type: boolean

  - name: regime_held_by_exit_persistence
    type: boolean

  - name: protest_band
    type: string

  - name: violence_band
    type: string

  - name: suppression_band
    type: string

  - name: disorder_band
    type: string

  - name: velocity_band
    type: string

  - name: conversion_band
    type: string

  - name: classification_reason
    type: string

  - name: regime_explanation
    type: string

  - name: supporting_signal_summary
    type: string

  - name: thresholds_active_json
    type: string

  - name: fallback_used
    type: boolean

  - name: consecutive_lower_weeks
    type: integer

  - name: consecutive_invalid_weeks
    type: integer

  - name: is_first_observation_week
    type: boolean

  - name: weeks_in_current_regime
    type: integer

  - name: regime_methodology_version
    type: string
    checks:
      - name: not_null

  - name: feature_version
    type: string

  - name: classification_methodology_version
    type: string

  - name: severity_methodology_version
    type: string

  - name: computed_at
    type: timestamp
@bruin */

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-01: REGIME THRESHOLDS
-- Single source of truth for all configurable constants.
-- No threshold literal may appear anywhere else in this asset.
-- Update values here only. thresholds_active_json serialises per row.
-- All values: PROVISIONAL_CALIBRATION_VALUES pending Kenya calibration.
-- ═══════════════════════════════════════════════════════════════════════════
WITH regime_thresholds AS (
    SELECT
        -- Band boundaries (PROVISIONAL — calibrate against Kenya data)
        1.0   AS z_elevated,              -- Lower boundary of ELEVATED band
        2.0   AS z_severe,                -- Lower boundary of SEVERE band
        0.15  AS z_adjacency_margin,      -- Threshold-adjacent zone width

        -- Dynamic signal thresholds (PROVISIONAL)
        0.30  AS velocity_high_threshold, -- escalation_velocity_score HIGH
        0.50  AS conversion_high_threshold, -- pressure_conversion_rate HIGH

        -- Fallback thresholds
        3.0   AS index_fallback_multiplier, -- index > multiplier × 12w mean
        4     AS index_fallback_min_weeks,  -- min non-zero prior weeks for fallback

        -- Disorder band
        1.5   AS k_disorder,              -- disorder_index > K × 12w mean

        -- Persistence windows (ARCHITECTURE-STABLE — do not change)
        3     AS crisis_exit_weeks,
        2     AS escalation_exit_weeks,
        2     AS repression_exit_weeks,
        2     AS validity_gap_max_weeks,
        2     AS entry_persistence_weeks,

        -- Methodology risk gate (PROVISIONAL)
        0.40  AS methodology_cap_threshold,

        -- Version
        'ACLED_REGIME_ENGINE_V1' AS regime_methodology_version
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-02: SOURCE FEATURES
-- Single read from features.acled_pressure_signals for target country.
-- All feature-layer fields are consumed as authoritative.
-- The intelligence layer DOES NOT recompute any z-score or baseline.
--
-- TARGET_WEEK FILTER: when target_week = '' (default, steady-state), the
-- second condition is always TRUE — the filter is a no-op and behaviour is
-- identical to all prior versions of this asset. When target_week is set
-- (sequential backfill mode), exactly one week's row is returned, which is
-- the precondition for correct single-week persistence chaining. This is
-- the ONLY part of this asset that is aware of the backfill variable.
-- ═══════════════════════════════════════════════════════════════════════════
source_features AS (
    SELECT
        week_start_date,
        country,
        '{{ var.iso2 }}' AS iso2,
        data_grain,

        -- Protest family
        protest_pressure_index,
        protest_pressure_z,
        sparse_protest_baseline_flag,
        protest_zero_variance_flag,
        protest_active_baseline_weeks,

        -- Violence family
        violence_pressure_index,
        violence_pressure_z,
        sparse_violence_baseline_flag,
        violence_zero_variance_flag,
        violence_active_baseline_weeks,

        -- Suppression family
        suppression_intensity_index,
        suppression_z,                             -- << FIXED: matched to feature layer column name
        sparse_suppression_baseline_flag,
        suppression_zero_variance_flag,
        suppression_active_baseline_weeks,

        -- Cross-family signals
        disorder_pressure_index,
        pressure_conversion_rate,
        escalation_velocity_score,
        event_diversity_index,

        -- Quality signals
        signal_valid,
        low_event_density_flag,
        high_methodology_risk_flag,
        methodology_risk_share,
        ambiguous_event_share,

        -- Version passthrough
        feature_version,
        classification_methodology_version,
        severity_methodology_version

    FROM `{{ var.project_id }}.features.acled_pressure_signals`
    WHERE country = '{{ var.country }}'
      AND (
            '{{ var.target_week }}' = ''
            OR week_start_date = SAFE.PARSE_DATE('%Y-%m-%d', '{{ var.target_week }}')
          )
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-03: PERSISTENCE CONTEXT
-- Lag join against prior materialised output of this asset.
-- LEFT JOIN ensures NULL-safe handling for first observation week.
-- All persistence fields default to safe values when NULL (first week).
-- CRITICAL: This join requires merge-or-replace materialisation strategy.
-- A create-and-replace strategy would destroy prior output before
-- the new run completes, producing NULL persistence state for all rows.
--
-- EXECUTION CONTRACT: this join target is the OUTPUT table as it exists
-- BEFORE this execution began. It does NOT see rows produced earlier in
-- the same execution. Correctness of all persistence-dependent fields
-- (weeks_in_current_regime, pre_transition_flag / pre_transition_target,
-- regime_continuation_flag, consecutive_lower_weeks,
-- consecutive_invalid_weeks) for week N depends on week N-1 having
-- ALREADY BEEN MERGED into this table by a prior, completed execution.
-- This asset MUST be invoked as one country × one new week × one
-- execution — see EXECUTION CONTRACT in the asset description header.
-- ═══════════════════════════════════════════════════════════════════════════
persistence_context AS (
    SELECT
        sf.week_start_date,
        sf.country,

        -- Prior regime state (NULL on first observation week)
        COALESCE(pr.primary_regime, 'STABLE')                               AS prior_regime_state,
        COALESCE(pr.confidence_level, 'HIGH')                               AS prior_confidence_level,
        COALESCE(pr.pre_transition_flag, FALSE)                             AS prior_pre_transition_flag,
        COALESCE(pr.pre_transition_target, NULL)                            AS prior_pre_transition_target,
        COALESCE(pr.regime_continuation_flag, FALSE)                        AS prior_regime_continuation_flag,
        COALESCE(pr.weeks_in_current_regime, 0)                             AS weeks_in_current_regime_prior,
        COALESCE(pr.consecutive_lower_weeks, 0)                             AS consecutive_lower_weeks_prior,
        COALESCE(pr.consecutive_invalid_weeks, 0)                           AS consecutive_invalid_weeks_prior,

        -- Flag whether this is the first observation week
        (pr.primary_regime IS NULL)                                         AS is_first_observation_week

    FROM source_features sf
    LEFT JOIN `{{ var.project_id }}.intelligence.acled_pressure_regimes` pr
        ON  pr.country        = sf.country
        AND pr.week_start_date = DATE_SUB(sf.week_start_date, INTERVAL 1 WEEK)
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-04: PRIMARY BAND ASSIGNMENT
-- Translates z-scores into discrete signal bands.
-- Applied identically to protest, violence, and suppression families.
-- NULL z-score ALWAYS maps to UNKNOWN — never to NORMAL.
-- UNKNOWN + pressure_index > 0 = INDEX_ACTIVE.
-- UNKNOWN + pressure_index = 0 = INDEX_ZERO.
-- Threshold-adjacent zone: within z_adjacency_margin above z_elevated.
-- ═══════════════════════════════════════════════════════════════════════════
primary_band_assignment AS (
    SELECT
        sf.*,
        t.z_elevated,
        t.z_severe,
        t.z_adjacency_margin,
        t.velocity_high_threshold,
        t.conversion_high_threshold,
        t.index_fallback_multiplier,
        t.index_fallback_min_weeks,
        t.k_disorder,
        t.crisis_exit_weeks,
        t.escalation_exit_weeks,
        t.repression_exit_weeks,
        t.validity_gap_max_weeks,
        t.entry_persistence_weeks,
        t.methodology_cap_threshold,
        t.regime_methodology_version,

        -- ── PROTEST BAND ────────────────────────────────────────────────
        CASE
            WHEN sf.protest_pressure_z IS NULL THEN 'UNKNOWN'
            WHEN sf.protest_pressure_z >= t.z_severe THEN 'SEVERE'
            WHEN sf.protest_pressure_z >= t.z_elevated THEN 'ELEVATED'
            ELSE 'NORMAL'
        END AS protest_band,

        CASE
            WHEN sf.protest_pressure_z IS NULL AND sf.protest_pressure_index > 0 THEN 'INDEX_ACTIVE'
            WHEN sf.protest_pressure_z IS NULL AND sf.protest_pressure_index = 0 THEN 'INDEX_ZERO'
            ELSE 'INDEX_ACTIVE'  -- valid z-score implies events
        END AS protest_index_status,

        -- Threshold-adjacent: within adjacency margin above z_elevated
        (sf.protest_pressure_z IS NOT NULL
            AND sf.protest_pressure_z >= t.z_elevated
            AND sf.protest_pressure_z < (t.z_elevated + t.z_adjacency_margin)) AS protest_threshold_adjacent,

        -- ── VIOLENCE BAND ────────────────────────────────────────────────
        CASE
            WHEN sf.violence_pressure_z IS NULL THEN 'UNKNOWN'
            WHEN sf.violence_pressure_z >= t.z_severe THEN 'SEVERE'
            WHEN sf.violence_pressure_z >= t.z_elevated THEN 'ELEVATED'
            ELSE 'NORMAL'
        END AS violence_band,

        CASE
            WHEN sf.violence_pressure_z IS NULL AND sf.violence_pressure_index > 0 THEN 'INDEX_ACTIVE'
            WHEN sf.violence_pressure_z IS NULL AND sf.violence_pressure_index = 0 THEN 'INDEX_ZERO'
            ELSE 'INDEX_ACTIVE'
        END AS violence_index_status,

        (sf.violence_pressure_z IS NOT NULL
            AND sf.violence_pressure_z >= t.z_elevated
            AND sf.violence_pressure_z < (t.z_elevated + t.z_adjacency_margin)) AS violence_threshold_adjacent,

        -- ── SUPPRESSION BAND ─────────────────────────────────────────────
        CASE
            WHEN sf.suppression_z IS NULL THEN 'UNKNOWN'                   -- << FIXED
            WHEN sf.suppression_z >= t.z_severe THEN 'SEVERE'             -- << FIXED
            WHEN sf.suppression_z >= t.z_elevated THEN 'ELEVATED'         -- << FIXED
            ELSE 'NORMAL'
        END AS suppression_band,

        CASE
            WHEN sf.suppression_z IS NULL AND sf.suppression_intensity_index > 0 THEN 'INDEX_ACTIVE'  -- << FIXED
            WHEN sf.suppression_z IS NULL AND sf.suppression_intensity_index = 0 THEN 'INDEX_ZERO'
            ELSE 'INDEX_ACTIVE'
        END AS suppression_index_status,

        (sf.suppression_z IS NOT NULL                                      -- << FIXED
            AND sf.suppression_z >= t.z_elevated                            -- << FIXED
            AND sf.suppression_z < (t.z_elevated + t.z_adjacency_margin)) AS suppression_threshold_adjacent  -- << FIXED

    FROM source_features sf
    CROSS JOIN regime_thresholds t
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-05: DYNAMIC BAND ASSIGNMENT
-- Velocity and conversion rate → HIGH / NORMAL / NULL bands.
-- NULL source value → NULL band (not NORMAL).
-- ═══════════════════════════════════════════════════════════════════════════
dynamic_band_assignment AS (
    SELECT
        b.*,
        CASE
            WHEN b.escalation_velocity_score IS NULL THEN NULL
            WHEN b.escalation_velocity_score >= b.velocity_high_threshold THEN 'HIGH'
            ELSE 'NORMAL'
        END AS velocity_band,

        -- NULL when protest_events = 0 (inherited from feature layer)
        CASE
            WHEN b.pressure_conversion_rate IS NULL THEN NULL
            WHEN b.pressure_conversion_rate >= b.conversion_high_threshold THEN 'HIGH'
            ELSE 'NORMAL'
        END AS conversion_band

    FROM primary_band_assignment b
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-06: STABLE PRECHECK
-- Determines whether STABLE can be positively confirmed.
-- STABLE requires all UNKNOWN families to have INDEX_ZERO.
-- BLOCKER-002: When precheck fails and no fallback activates → STABLE +
-- INSUFFICIENT_DATA. This is enforced in CTE-10 regime_candidate.
-- ═══════════════════════════════════════════════════════════════════════════
stable_precheck AS (
    SELECT
        d.*,

        -- stable_precheck_passes = TRUE when no UNKNOWN family has INDEX_ACTIVE
        NOT (
               (d.protest_band     = 'UNKNOWN' AND d.protest_index_status     = 'INDEX_ACTIVE')
            OR (d.violence_band    = 'UNKNOWN' AND d.violence_index_status    = 'INDEX_ACTIVE')
            OR (d.suppression_band = 'UNKNOWN' AND d.suppression_index_status = 'INDEX_ACTIVE')
        ) AS stable_precheck_passes

    FROM dynamic_band_assignment d
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-07: FALLBACK ASSESSMENT
-- Computes per-family index fallback activation and disorder band.
-- Fallback activates when: pressure_index > INDEX_FALLBACK_MULTIPLIER ×
-- 12-week rolling mean of pressure_index AND ≥ 4 prior non-zero index weeks.
-- Disorder band: ratio comparison against 12-week mean (no z-score available).
-- ═══════════════════════════════════════════════════════════════════════════
fallback_assessment AS (
    SELECT
        sp.*,

        -- 12-week rolling means for fallback comparison
        AVG(sp.protest_pressure_index)          OVER w12 AS protest_index_mean_12w,
        AVG(sp.violence_pressure_index)         OVER w12 AS violence_index_mean_12w,
        AVG(sp.suppression_intensity_index)     OVER w12 AS suppression_index_mean_12w,

        -- Active (non-zero) prior weeks for each family
        COUNTIF(sp.protest_pressure_index > 0)     OVER w12 AS protest_nonzero_prior_weeks,
        COUNTIF(sp.violence_pressure_index > 0)    OVER w12 AS violence_nonzero_prior_weeks,
        COUNTIF(sp.suppression_intensity_index > 0) OVER w12 AS suppression_nonzero_prior_weeks,

        -- Disorder 12-week mean (for disorder band)
        AVG(sp.disorder_pressure_index) OVER w12 AS disorder_index_mean_12w

    FROM stable_precheck sp
    WINDOW w12 AS (
        PARTITION BY sp.country
        ORDER BY sp.week_start_date
        ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING
    )
),

-- Separate CTE to apply fallback logic after window functions
fallback_flags AS (
    SELECT
        fa.*,

        -- Protest fallback: index > multiplier × mean AND ≥ min_weeks prior non-zero
        (fa.protest_pressure_z IS NULL
            AND fa.protest_index_mean_12w IS NOT NULL
            AND fa.protest_nonzero_prior_weeks >= fa.index_fallback_min_weeks
            AND fa.protest_pressure_index > (fa.index_fallback_multiplier * fa.protest_index_mean_12w)) AS protest_fallback_active,

        -- Violence fallback
        (fa.violence_pressure_z IS NULL
            AND fa.violence_index_mean_12w IS NOT NULL
            AND fa.violence_nonzero_prior_weeks >= fa.index_fallback_min_weeks
            AND fa.violence_pressure_index > (fa.index_fallback_multiplier * fa.violence_index_mean_12w)) AS violence_fallback_active,

        -- Suppression fallback (uses suppression_z column name, already fixed above)
        (fa.suppression_z IS NULL                                             -- << FIXED
            AND fa.suppression_index_mean_12w IS NOT NULL
            AND fa.suppression_nonzero_prior_weeks >= fa.index_fallback_min_weeks
            AND fa.suppression_intensity_index > (fa.index_fallback_multiplier * fa.suppression_index_mean_12w)) AS suppression_fallback_active,

        -- Disorder band: ratio comparison (no z-score from feature layer)
        CASE
            WHEN fa.disorder_index_mean_12w IS NULL THEN NULL -- insufficient history
            WHEN fa.disorder_pressure_index > (fa.k_disorder * fa.disorder_index_mean_12w) THEN 'ELEVATED'
            ELSE 'NORMAL'
        END AS disorder_band

    FROM fallback_assessment fa
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-08: CRISIS FALLBACK EVALUATION
-- BLOCKER-004: Fallback-active families treated as SEVERE for CRISIS only.
-- Outside CRISIS, they retain UNKNOWN band.
-- Constructs the combined band state and tests primary CRISIS conditions.
-- ═══════════════════════════════════════════════════════════════════════════
crisis_fallback_eval AS (
    SELECT
        ff.*,

        -- Combined bands for CRISIS evaluation:
        -- fallback-active families → SEVERE
        -- non-fallback families → actual band from CTE-04
        CASE WHEN ff.protest_fallback_active     THEN 'SEVERE' ELSE ff.protest_band     END AS protest_band_crisis,
        CASE WHEN ff.violence_fallback_active    THEN 'SEVERE' ELSE ff.violence_band    END AS violence_band_crisis,
        CASE WHEN ff.suppression_fallback_active THEN 'SEVERE' ELSE ff.suppression_band END AS suppression_band_crisis,

        -- Whether any fallback was used
        (ff.protest_fallback_active OR ff.violence_fallback_active OR ff.suppression_fallback_active) AS fallback_used

    FROM fallback_flags ff
),

-- Test CRISIS conditions against combined bands
crisis_fallback_result AS (
    SELECT
        cf.*,

        -- CRISIS condition 1a: two or more primary families at SEVERE (using combined crisis bands)
        (
            (cf.protest_band_crisis     = 'SEVERE' AND cf.suppression_band_crisis = 'SEVERE')
            OR
            (cf.protest_band_crisis     = 'SEVERE' AND cf.violence_band_crisis    = 'SEVERE')
            OR
            (cf.suppression_band_crisis = 'SEVERE' AND cf.violence_band_crisis    = 'SEVERE')
        ) AS crisis_cond_1a_combined,

        -- CRISIS condition 1b: protest SEVERE + suppression SEVERE + velocity HIGH
        (cf.protest_band_crisis     = 'SEVERE'
            AND cf.suppression_band_crisis = 'SEVERE'
            AND cf.velocity_band           = 'HIGH') AS crisis_cond_1b_combined,

        -- CRISIS fallback qualifies = any crisis condition met via combined bands
        -- AND at least one family was a fallback (otherwise regular CRISIS applies)
        -- AND signal_valid = FALSE
        (cf.fallback_used
            AND cf.signal_valid = FALSE
            AND (
                (cf.protest_band_crisis     = 'SEVERE' AND cf.suppression_band_crisis = 'SEVERE')
                OR
                (cf.protest_band_crisis     = 'SEVERE' AND cf.violence_band_crisis    = 'SEVERE')
                OR
                (cf.suppression_band_crisis = 'SEVERE' AND cf.violence_band_crisis    = 'SEVERE')
                OR
                (cf.protest_band_crisis     = 'SEVERE' AND cf.suppression_band_crisis = 'SEVERE' AND cf.velocity_band = 'HIGH')
            )
        ) AS crisis_fallback_qualifies

    FROM crisis_fallback_eval cf
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-09: PERSISTENCE RESOLUTION
-- Determines entry persistence status for each lower-severity regime.
-- BLOCKER-003: Explicit set membership for CONTESTATION persistence.
-- Persistence waived: {MOBILISATION, CONTESTATION, ESCALATION, CRISIS}
-- Persistence required: {STABLE, CONFLICT, REPRESSION}
-- Persistence logic: if prior_pre_transition_target matches AND prior flag TRUE
-- → second consecutive week → persistence met.
--
-- PERSISTENCE ASSUMPTION: prior_pre_transition_flag / prior_pre_transition_target
-- / prior_regime_state below are sourced from persistence_context (CTE-03),
-- which in turn reflects the previously-merged output row for week N-1.
-- Per the EXECUTION CONTRACT, this is only meaningful when this asset is
-- invoked one country × one new week × one execution, with week N-1 already
-- merged. See CTE-03 for details.
-- ═══════════════════════════════════════════════════════════════════════════
persistence_resolution AS (
    SELECT
        cf.*,
        pc.prior_regime_state,
        pc.prior_confidence_level,
        pc.prior_pre_transition_flag,
        pc.prior_pre_transition_target,
        pc.prior_regime_continuation_flag,
        pc.weeks_in_current_regime_prior,
        pc.consecutive_lower_weeks_prior,
        pc.consecutive_invalid_weeks_prior,
        pc.is_first_observation_week,

        -- ── MOBILISATION PERSISTENCE ─────────────────────────────────────
        -- Required from: {STABLE}
        -- Waived from: {MOBILISATION, CONTESTATION, ESCALATION, CRISIS,
        --              CONFLICT, REPRESSION} (all non-STABLE prior regimes)
        -- Note: MOBILISATION uses "STABLE requires persistence" logic —
        -- all other prior regimes waive persistence because they already
        -- represent active political environments.
        CASE
            WHEN pc.prior_regime_state IN (
                    'MOBILISATION', 'CONTESTATION', 'ESCALATION',
                    'CRISIS', 'CONFLICT', 'REPRESSION'
                ) THEN TRUE -- waived
            WHEN pc.prior_regime_state = 'STABLE'
                AND pc.prior_pre_transition_flag = TRUE
                AND pc.prior_pre_transition_target = 'MOBILISATION' THEN TRUE -- second consecutive qualifying week
            ELSE FALSE -- first qualifying week from STABLE
        END AS mobilisation_persistence_met,

        -- ── CONTESTATION PERSISTENCE (BLOCKER-003) ───────────────────────
        -- Waived from: {MOBILISATION, CONTESTATION, ESCALATION, CRISIS}
        -- Required from: {STABLE, CONFLICT, REPRESSION}
        CASE
            WHEN pc.prior_regime_state IN (
                    'MOBILISATION', 'CONTESTATION', 'ESCALATION', 'CRISIS'
                ) THEN TRUE -- waived per BLOCKER-003
            WHEN pc.prior_regime_state IN ('STABLE', 'CONFLICT', 'REPRESSION')
                AND pc.prior_pre_transition_flag = TRUE
                AND pc.prior_pre_transition_target = 'CONTESTATION' THEN TRUE -- second consecutive qualifying week
            ELSE FALSE
        END AS contestation_persistence_met,

        -- ── REPRESSION PERSISTENCE ───────────────────────────────────────
        -- Required from: {STABLE, CONFLICT, MOBILISATION, CONTESTATION,
        --                ESCALATION, CRISIS} (all — first REPRESSION requires
        --                two consecutive qualifying weeks from any prior state
        --                except REPRESSION itself which is continuation)
        CASE
            WHEN pc.prior_regime_state = 'REPRESSION' THEN TRUE -- continuation
            WHEN pc.prior_pre_transition_flag = TRUE
                AND pc.prior_pre_transition_target = 'REPRESSION' THEN TRUE -- second consecutive qualifying week
            ELSE FALSE
        END AS repression_persistence_met,

        -- ── CONFLICT PERSISTENCE ─────────────────────────────────────────
        CASE
            WHEN pc.prior_regime_state IN ('CONFLICT', 'ESCALATION', 'CRISIS') THEN TRUE -- continuation or de-escalation from higher violent regimes
            WHEN pc.prior_pre_transition_flag = TRUE
                AND pc.prior_pre_transition_target = 'CONFLICT' THEN TRUE -- second consecutive qualifying week
            ELSE FALSE
        END AS conflict_persistence_met

    FROM crisis_fallback_result cf
    JOIN persistence_context pc
        ON  pc.week_start_date = cf.week_start_date
        AND pc.country         = cf.country
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-10: REGIME CANDIDATE EVALUATION
-- Core classification logic. Evaluated in exact hierarchy order:
-- CRISIS → ESCALATION → CONTESTATION → REPRESSION → CONFLICT →
-- MOBILISATION → STABLE
-- First matching condition assigns regime. No re-evaluation after match.
-- BLOCKER-002 Case C implemented in STABLE Step 7.
-- BLOCKER-004: CRISIS uses crisis_band_* (combined) for evaluation.
-- ESCALATION uses actual bands (protest_band, etc.).
-- ═══════════════════════════════════════════════════════════════════════════
regime_candidate AS (
    SELECT
        pr.*,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 1: CRISIS EVALUATION
        -- Condition 1a: two+ primary families at SEVERE (combined bands)
        -- Condition 1b: protest SEVERE + suppression SEVERE + velocity HIGH
        -- Condition 1c: crisis_fallback_qualifies (BLOCKER-004)
        --
        -- IMPLEMENTATION FIX: the full expression is wrapped in a single
        -- enclosing pair of parentheses so that crisis_conditions_met
        -- unambiguously represents:
        --     (Condition 1a) OR (Condition 1b) OR (Condition 1c)
        -- This matches Rule 4 (CRISIS evaluated first, using all three
        -- documented sub-conditions) and the CTE-08 commentary. This is
        -- a correction to restore the documented/specified evaluation,
        -- not a behavioural redesign.
        --
        -- Note: crisis_band_* = SEVERE when fallback active (BLOCKER-004,
        -- consumed via crisis_fallback_qualifies for condition 1c).
        -- ────────────────────────────────────────────────────────────────
        (
            (
                -- 1a: two primary families at SEVERE (regular, no fallback needed)
                (pr.protest_band     = 'SEVERE' AND pr.suppression_band = 'SEVERE')
                OR
                (pr.protest_band     = 'SEVERE' AND pr.violence_band    = 'SEVERE')
                OR
                (pr.suppression_band = 'SEVERE' AND pr.violence_band    = 'SEVERE')
            )
            OR
            (
                -- 1b: protest SEVERE + suppression SEVERE + velocity HIGH (regular)
                pr.protest_band     = 'SEVERE'
                AND pr.suppression_band = 'SEVERE'
                AND pr.velocity_band    = 'HIGH'
            )
            OR
            -- 1c: CRISIS via index fallback (BLOCKER-004)
            pr.crisis_fallback_qualifies
        ) AS crisis_conditions_met,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 2: ESCALATION EVALUATION
        -- Uses ACTUAL bands (not crisis combined bands) — BLOCKER-004
        -- Pathway A: all three ELEVATED+
        -- Pathway B: suppression ELEVATED+ AND violence ELEVATED+
        -- Pathway C: protest ELEVATED+ AND conversion HIGH AND velocity HIGH
        -- ────────────────────────────────────────────────────────────────
        CASE
            WHEN (pr.protest_band     IN ('ELEVATED','SEVERE')
                AND pr.suppression_band IN ('ELEVATED','SEVERE')
                AND pr.violence_band    IN ('ELEVATED','SEVERE')) THEN 'PATHWAY_A'
            WHEN (pr.suppression_band IN ('ELEVATED','SEVERE')
                AND pr.violence_band  IN ('ELEVATED','SEVERE')) THEN 'PATHWAY_B'
            WHEN (pr.protest_band     IN ('ELEVATED','SEVERE')
                AND pr.conversion_band = 'HIGH'
                AND pr.velocity_band   = 'HIGH') THEN 'PATHWAY_C'
            ELSE NULL
        END AS escalation_pathway,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 3: CONTESTATION CONDITIONS
        -- protest ELEVATED+ AND suppression ELEVATED+
        -- violence must NOT be ELEVATED or SEVERE (UNKNOWN OK — see below)
        -- ────────────────────────────────────────────────────────────────
        (pr.protest_band       IN ('ELEVATED','SEVERE')
            AND pr.suppression_band IN ('ELEVATED','SEVERE')
            AND pr.violence_band    NOT IN ('ELEVATED','SEVERE')
        -- UNKNOWN with INDEX_ACTIVE is permitted for violence in CONTESTATION
        -- (assigned CONTESTATION with confidence cap at MEDIUM)
        ) AS contestation_conditions_met,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 4: REPRESSION CONDITIONS
        -- suppression ELEVATED+ AND suppression_z NOT NULL (hard gate)
        -- protest NOT ELEVATED, violence NOT ELEVATED
        -- ────────────────────────────────────────────────────────────────
        (pr.suppression_band IN ('ELEVATED','SEVERE')
            AND pr.suppression_z IS NOT NULL -- hard gate (BLOCKER-004 rationale)  -- << FIXED
            AND pr.protest_band  NOT IN ('ELEVATED','SEVERE')
            AND pr.violence_band NOT IN ('ELEVATED','SEVERE')
        ) AS repression_conditions_met,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 5: CONFLICT CONDITIONS
        -- violence ELEVATED+ AND protest NOT ELEVATED AND suppression NOT ELEVATED
        -- ────────────────────────────────────────────────────────────────
        (pr.violence_band IN ('ELEVATED','SEVERE')
            AND pr.protest_band     NOT IN ('ELEVATED','SEVERE')
            AND pr.suppression_band NOT IN ('ELEVATED','SEVERE')
        ) AS conflict_conditions_met,

        -- ────────────────────────────────────────────────────────────────
        -- STEP 6: MOBILISATION CONDITIONS
        -- protest ELEVATED+ AND suppression NOT ELEVATED AND violence NOT ELEVATED
        -- ────────────────────────────────────────────────────────────────
        (pr.protest_band IN ('ELEVATED','SEVERE')
            AND pr.suppression_band NOT IN ('ELEVATED','SEVERE')
            AND pr.violence_band    NOT IN ('ELEVATED','SEVERE')
        ) AS mobilisation_conditions_met

    FROM persistence_resolution pr
),

-- Apply evaluation order to produce candidate regime
regime_candidate_assigned AS (
    SELECT
        rc.*,

        -- Ordered evaluation: first TRUE wins
        CASE
            -- STEP 1: CRISIS (no persistence required)
            WHEN rc.crisis_conditions_met THEN 'CRISIS'

            -- STEP 2: ESCALATION (no persistence required)
            WHEN rc.escalation_pathway IS NOT NULL THEN 'ESCALATION'

            -- STEP 3: CONTESTATION (persistence logic applied)
            WHEN rc.contestation_conditions_met AND rc.contestation_persistence_met THEN 'CONTESTATION'

            -- STEP 4: REPRESSION (persistence logic applied)
            WHEN rc.repression_conditions_met AND rc.repression_persistence_met THEN 'REPRESSION'

            -- STEP 5: CONFLICT (persistence logic applied)
            WHEN rc.conflict_conditions_met AND rc.conflict_persistence_met THEN 'CONFLICT'

            -- STEP 6: MOBILISATION (persistence logic applied)
            WHEN rc.mobilisation_conditions_met AND rc.mobilisation_persistence_met THEN 'MOBILISATION'

            -- STEP 7: STABLE
            -- Case A: standard (precheck passes, no higher regime)
            -- Case B: fallback active → handled as MOBILISATION/CONFLICT above
            -- Case C (BLOCKER-002): precheck fails + NO fallback activation
            --   → STABLE + INSUFFICIENT_DATA (confidence applied in CTE-15
            --   via the stable_insufficient_data_case flag below, which is
            --   consumed in CTE-14's confidence_ceiling computation)
            ELSE 'STABLE'
        END AS candidate_regime,

        -- Pre-transition flag: conditions met but persistence not yet satisfied
        -- Records which regime this week is approaching for next week's persistence check
        CASE
            -- CONTESTATION approaching: conditions met, persistence NOT met
            WHEN rc.contestation_conditions_met AND NOT rc.contestation_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL THEN TRUE

            -- REPRESSION approaching
            WHEN rc.repression_conditions_met AND NOT rc.repression_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met THEN TRUE

            -- CONFLICT approaching
            WHEN rc.conflict_conditions_met AND NOT rc.conflict_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met
                AND NOT rc.repression_conditions_met THEN TRUE

            -- MOBILISATION approaching
            WHEN rc.mobilisation_conditions_met AND NOT rc.mobilisation_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met
                AND NOT rc.repression_conditions_met
                AND NOT rc.conflict_conditions_met THEN TRUE

            ELSE FALSE
        END AS pre_transition_flag,

        -- Which regime is being approached
        CASE
            WHEN rc.contestation_conditions_met AND NOT rc.contestation_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL THEN 'CONTESTATION'

            WHEN rc.repression_conditions_met AND NOT rc.repression_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met THEN 'REPRESSION'

            WHEN rc.conflict_conditions_met AND NOT rc.conflict_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met
                AND NOT rc.repression_conditions_met THEN 'CONFLICT'

            WHEN rc.mobilisation_conditions_met AND NOT rc.mobilisation_persistence_met
                AND NOT rc.crisis_conditions_met
                AND rc.escalation_pathway IS NULL
                AND NOT rc.contestation_conditions_met
                AND NOT rc.repression_conditions_met
                AND NOT rc.conflict_conditions_met THEN 'MOBILISATION'

            ELSE NULL
        END AS pre_transition_target,

        -- Flag: BLOCKER-002 Case C — precheck failed but no fallback
        -- (used in confidence engine to assign INSUFFICIENT_DATA).
        -- WIRING: this flag is consumed in CTE-14 (confidence_ceiling_computed)
        -- as the FIRST-evaluated branch of confidence_ceiling — when TRUE,
        -- confidence_ceiling is forced to 'INSUFFICIENT_DATA' regardless of
        -- any other condition. candidate_regime for these rows is 'STABLE'
        -- via the ELSE branch above (no higher-regime condition can be met
        -- when stable_precheck_passes = FALSE and no fallback is active, by
        -- construction of the UNKNOWN/INDEX_ACTIVE band logic in CTE-04).
        (NOT rc.stable_precheck_passes
            AND NOT rc.protest_fallback_active
            AND NOT rc.violence_fallback_active
            AND NOT rc.suppression_fallback_active) AS stable_insufficient_data_case,

        -- Secondary regime characteristics (qualifying conditions overridden by primary)
        TO_JSON_STRING(
            ARRAY(
                SELECT r FROM UNNEST([
                    IF(rc.crisis_conditions_met, 'CRISIS', NULL),
                    IF(rc.escalation_pathway IS NOT NULL, 'ESCALATION', NULL),
                    IF(rc.contestation_conditions_met, 'CONTESTATION', NULL),
                    IF(rc.repression_conditions_met, 'REPRESSION', NULL),
                    IF(rc.conflict_conditions_met, 'CONFLICT', NULL),
                    IF(rc.mobilisation_conditions_met, 'MOBILISATION', NULL)
                ]) r
                WHERE r IS NOT NULL
            )
        ) AS qualifying_regimes_json

    FROM regime_candidate rc
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-11: EXIT PERSISTENCE
-- Prevents premature de-escalation from high-severity regimes.
-- CRISIS: 3 consecutive lower weeks required
-- ESCALATION: 2 consecutive lower weeks required
-- REPRESSION: 2 consecutive lower weeks required
-- consecutive_lower_weeks counter: increments when candidate is lower
-- than prior regime; resets to 0 otherwise.
--
-- MAINTAINABILITY: the regime → hierarchy-ordinal mapping (CRISIS=7 ...
-- STABLE=1) is computed ONCE here for both candidate_regime and
-- prior_regime_state (as candidate_hierarchy / prior_hierarchy) and reused
-- below and in CTE-16, instead of being re-derived inline at each use site.
-- The mapping itself is unchanged and frozen — only the number of times it
-- is written out has been reduced. No output values change.
-- ═══════════════════════════════════════════════════════════════════════════
exit_persistence AS (
    SELECT
        rca.*,

        -- Hierarchy values for comparison (higher number = higher severity)
        CASE rca.candidate_regime
            WHEN 'CRISIS' THEN 7
            WHEN 'ESCALATION' THEN 6
            WHEN 'CONTESTATION' THEN 5
            WHEN 'REPRESSION' THEN 4
            WHEN 'CONFLICT' THEN 3
            WHEN 'MOBILISATION' THEN 2
            WHEN 'STABLE' THEN 1
        END AS candidate_hierarchy,

        CASE rca.prior_regime_state
            WHEN 'CRISIS' THEN 7
            WHEN 'ESCALATION' THEN 6
            WHEN 'CONTESTATION' THEN 5
            WHEN 'REPRESSION' THEN 4
            WHEN 'CONFLICT' THEN 3
            WHEN 'MOBILISATION' THEN 2
            WHEN 'STABLE' THEN 1
            ELSE 1
        END AS prior_hierarchy

    FROM regime_candidate_assigned rca
),

exit_persistence_ranked AS (
    SELECT
        ep.*,

        -- Increment consecutive_lower_weeks when candidate is lower than prior.
        -- Reuses candidate_hierarchy / prior_hierarchy computed above instead
        -- of re-deriving the hierarchy mapping a second time. Equivalent to
        -- the original inline CASE/CASE comparison (same mapping, same
        -- result), since prior_hierarchy already defaults to 1 for any
        -- prior_regime_state not in the explicit list (matching the
        -- original inline ELSE 1 branch on the prior side, and STABLE=1 on
        -- the candidate side).
        CASE
            WHEN ep.candidate_hierarchy < ep.prior_hierarchy
            THEN ep.consecutive_lower_weeks_prior + 1
            ELSE 0
        END AS consecutive_lower_weeks

    FROM exit_persistence ep
),

exit_persistence_applied AS (
    SELECT
        ep.*,

        -- Apply exit persistence gates
        CASE
            -- CRISIS exit: requires 3 consecutive lower weeks
            WHEN ep.prior_regime_state = 'CRISIS'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.crisis_exit_weeks THEN 'CRISIS'

            -- ESCALATION exit: requires 2 consecutive lower weeks
            WHEN ep.prior_regime_state = 'ESCALATION'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.escalation_exit_weeks THEN 'ESCALATION'

            -- REPRESSION exit: requires 2 consecutive lower weeks
            WHEN ep.prior_regime_state = 'REPRESSION'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.repression_exit_weeks THEN 'REPRESSION'

            -- All other cases: candidate regime is accepted
            ELSE ep.candidate_regime
        END AS persistence_adjusted_regime,

        -- Whether regime is being held by exit persistence
        (
            (ep.prior_regime_state = 'CRISIS'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.crisis_exit_weeks)
            OR
            (ep.prior_regime_state = 'ESCALATION'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.escalation_exit_weeks)
            OR
            (ep.prior_regime_state = 'REPRESSION'
                AND ep.candidate_hierarchy < ep.prior_hierarchy
                AND ep.consecutive_lower_weeks < ep.repression_exit_weeks)
        ) AS regime_held_by_exit_persistence

    FROM exit_persistence_ranked ep
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-12: VALIDITY GAP CONTINUATION
-- When signal_valid = FALSE during CRISIS or ESCALATION:
-- Hold the prior regime for up to validity_gap_max_weeks (2) consecutive
-- invalid weeks. After that limit, transition to STABLE + INSUFFICIENT_DATA.
-- consecutive_invalid_weeks counter:
--   increments when signal_valid=FALSE AND prior regime is high-severity.
--   resets to 0 otherwise.
--
-- COEXISTENCE NOTE: regime_continuation_flag (this CTE) and
-- regime_held_by_exit_persistence (CTE-11) are independent flags and MAY
-- both be TRUE for the same row — e.g. when signal_valid = FALSE AND the
-- candidate regime is lower than a CRISIS/ESCALATION/REPRESSION prior.
-- In that case gap_adjusted_regime below takes precedence (holds
-- prior_regime_state directly), and persistence_adjusted_regime from
-- CTE-11 — which would ALSO hold the same prior regime via exit
-- persistence — becomes the (unused-in-this-branch) ELSE fallback. Both
-- flags are independently meaningful for the audit trail
-- (classification_reason in CTE-17 may list both "exit_persistence" and
-- "continuation"); this is expected and not a defect.
-- ═══════════════════════════════════════════════════════════════════════════
validity_gap_continuation AS (
    SELECT
        ep.*,

        -- Increment consecutive_invalid_weeks counter
        CASE
            WHEN ep.signal_valid = FALSE
                AND ep.prior_regime_state IN ('CRISIS', 'ESCALATION')
            THEN ep.consecutive_invalid_weeks_prior + 1
            ELSE 0
        END AS consecutive_invalid_weeks,

        -- Apply validity gap continuation
        CASE
            WHEN ep.signal_valid = FALSE
                AND ep.prior_regime_state IN ('CRISIS', 'ESCALATION')
                AND (ep.consecutive_invalid_weeks_prior + 1) <= ep.validity_gap_max_weeks
            THEN ep.prior_regime_state -- hold prior regime
            ELSE ep.persistence_adjusted_regime
        END AS gap_adjusted_regime,

        -- Flag: regime held due to validity gap
        (ep.signal_valid = FALSE
            AND ep.prior_regime_state IN ('CRISIS', 'ESCALATION')
            AND (ep.consecutive_invalid_weeks_prior + 1) <= ep.validity_gap_max_weeks) AS regime_continuation_flag

    FROM exit_persistence_applied ep
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-13: FINAL REGIME STATE
-- Resolves the final primary_regime from the gap-adjusted output.
-- Computes regime_duration_weeks counter.
-- ═══════════════════════════════════════════════════════════════════════════
final_regime AS (
    SELECT
        vg.*,
        vg.gap_adjusted_regime AS final_regime_state,

        -- Regime duration counter: increments when regime is same as prior
        -- (including continuation weeks).
        --
        -- NOTE ON REDUNDANCY: when regime_continuation_flag = TRUE, CTE-12
        -- sets gap_adjusted_regime := prior_regime_state by construction, so
        -- "vg.gap_adjusted_regime = vg.prior_regime_state" is already TRUE in
        -- that case and "OR vg.regime_continuation_flag = TRUE" is logically
        -- redundant. It is retained intentionally: it documents that
        -- continuation weeks ALWAYS count toward regime duration even if the
        -- equality condition's truth were ever to depend on a future change
        -- to CTE-12's construction. Removing it has no effect on any output
        -- given the current CTE-12 logic; it is kept for clarity / defensive
        -- documentation, not because it changes behaviour.
        CASE
            WHEN vg.gap_adjusted_regime = vg.prior_regime_state
                OR vg.regime_continuation_flag = TRUE
            THEN vg.weeks_in_current_regime_prior + 1
            ELSE 1
        END AS weeks_in_current_regime                     -- << FIXED: renamed for self-join compatibility

    FROM validity_gap_continuation vg
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-14: CONFIDENCE CEILING
-- Dominant family mapping per specification Section 6.1.
-- For ESCALATION, escalation_pathway determines dominant families.
-- Assesses z_available, baseline_sufficient, variance_meaningful
-- for each dominant family.
-- ═══════════════════════════════════════════════════════════════════════════
confidence_ceiling AS (
    SELECT
        fr.*,

        -- ── Dominant family assessments ─────────────────────────────────
        -- Protest
        (fr.protest_pressure_z IS NOT NULL)    AS protest_z_available,
        (NOT fr.sparse_protest_baseline_flag)  AS protest_baseline_sufficient,
        (NOT fr.protest_zero_variance_flag)    AS protest_variance_meaningful,
        (fr.protest_band = 'UNKNOWN' AND fr.protest_index_status = 'INDEX_ACTIVE') AS protest_unknown_active,

        -- Violence
        (fr.violence_pressure_z IS NOT NULL)   AS violence_z_available,
        (NOT fr.sparse_violence_baseline_flag) AS violence_baseline_sufficient,
        (NOT fr.violence_zero_variance_flag)   AS violence_variance_meaningful,
        (fr.violence_band = 'UNKNOWN' AND fr.violence_index_status = 'INDEX_ACTIVE') AS violence_unknown_active,

        -- Suppression
        (fr.suppression_z IS NOT NULL)              AS suppression_z_available,       -- << FIXED
        (NOT fr.sparse_suppression_baseline_flag)   AS suppression_baseline_sufficient,
        (NOT fr.suppression_zero_variance_flag)     AS suppression_variance_meaningful,
        (fr.suppression_band = 'UNKNOWN' AND fr.suppression_index_status = 'INDEX_ACTIVE') AS suppression_unknown_active,

        -- ── Dominant family set for final regime ─────────────────────────
        -- Used in ceiling and downgrade computations
        CASE fr.final_regime_state
            WHEN 'CRISIS'        THEN 'ALL_THREE'
            WHEN 'ESCALATION'    THEN CASE fr.escalation_pathway
                                        WHEN 'PATHWAY_A' THEN 'ALL_THREE'
                                        WHEN 'PATHWAY_B' THEN 'SUPPRESSION_VIOLENCE'
                                        WHEN 'PATHWAY_C' THEN 'PROTEST_ONLY'
                                        ELSE 'ALL_THREE'
                                      END
            WHEN 'CONTESTATION'  THEN 'PROTEST_SUPPRESSION'
            WHEN 'REPRESSION'    THEN 'SUPPRESSION_ONLY'
            WHEN 'CONFLICT'      THEN 'VIOLENCE_ONLY'
            WHEN 'MOBILISATION'  THEN 'PROTEST_ONLY'
            WHEN 'STABLE'        THEN 'ALL_THREE'
            ELSE 'ALL_THREE'
        END AS dominant_family_set

    FROM final_regime fr
),

-- Compute ceiling based on dominant family assessments
confidence_ceiling_computed AS (
    SELECT
        cc.*,

        -- ── Compute ceiling ──────────────────────────────────────────────
        -- INSUFFICIENT_DATA: all dominant families INDEX_ZERO + signal_valid FALSE
        --   + low_event_density_flag TRUE
        -- LOW: two+ dominant families UNKNOWN+INDEX_ACTIVE
        --   OR one dominant UNKNOWN+INDEX_ACTIVE + methodology risk TRUE
        --   OR fallback used + signal_valid FALSE
        -- MEDIUM: one dominant UNKNOWN+INDEX_ACTIVE
        --   OR methodology risk TRUE (with valid z-scores)
        --   OR any dominant sparse flag TRUE (z-score exists but thin)
        --   OR threshold_adjacent on dominant family
        -- HIGH: all dominant conditions satisfied
        CASE
            -- BLOCKER-002 WIRING: stable_insufficient_data_case is computed
            -- in CTE-10 (regime_candidate_assigned). When TRUE, this is the
            -- FIRST branch evaluated here, forcing confidence_ceiling =
            -- 'INSUFFICIENT_DATA' unconditionally. Combined with
            -- final_regime_state = 'STABLE' (guaranteed by CTE-10's
            -- candidate logic whenever this flag is TRUE, and unchanged by
            -- any persistence/validity-gap adjustment since STABLE cannot
            -- trigger exit-persistence or validity-gap holds), this
            -- satisfies BLOCKER-002: primary_regime = STABLE,
            -- confidence_level = INSUFFICIENT_DATA, with no directional
            -- regime assigned from INDEX_ACTIVE alone.
            WHEN cc.stable_insufficient_data_case THEN 'INSUFFICIENT_DATA'

            WHEN (cc.signal_valid = FALSE
                    AND cc.low_event_density_flag = TRUE
                    AND CASE cc.dominant_family_set
                            WHEN 'ALL_THREE'             THEN (cc.protest_index_status     = 'INDEX_ZERO'
                                                              AND cc.violence_index_status    = 'INDEX_ZERO'
                                                              AND cc.suppression_index_status = 'INDEX_ZERO')
                            WHEN 'PROTEST_SUPPRESSION'    THEN (cc.protest_index_status     = 'INDEX_ZERO'
                                                              AND cc.suppression_index_status = 'INDEX_ZERO')
                            WHEN 'SUPPRESSION_VIOLENCE'   THEN (cc.suppression_index_status = 'INDEX_ZERO'
                                                              AND cc.violence_index_status    = 'INDEX_ZERO')
                            WHEN 'PROTEST_ONLY'           THEN cc.protest_index_status       = 'INDEX_ZERO'
                            WHEN 'VIOLENCE_ONLY'          THEN cc.violence_index_status      = 'INDEX_ZERO'
                            WHEN 'SUPPRESSION_ONLY'       THEN cc.suppression_index_status   = 'INDEX_ZERO'
                            ELSE FALSE
                        END
                ) THEN 'INSUFFICIENT_DATA'

            -- LOW conditions
            WHEN cc.fallback_used AND cc.signal_valid = FALSE THEN 'LOW'

            WHEN (CASE cc.dominant_family_set
                    WHEN 'ALL_THREE'           THEN (CAST(cc.protest_unknown_active     AS INT64)
                                                   + CAST(cc.violence_unknown_active    AS INT64)
                                                   + CAST(cc.suppression_unknown_active AS INT64)) >= 2
                    WHEN 'PROTEST_SUPPRESSION'  THEN (CAST(cc.protest_unknown_active     AS INT64)
                                                   + CAST(cc.suppression_unknown_active AS INT64)) >= 2
                    WHEN 'SUPPRESSION_VIOLENCE' THEN (CAST(cc.suppression_unknown_active AS INT64)
                                                   + CAST(cc.violence_unknown_active    AS INT64)) >= 2
                    ELSE FALSE
                  END) THEN 'LOW'

            WHEN (cc.high_methodology_risk_flag = TRUE
                    AND ((cc.dominant_family_set = 'ALL_THREE'       AND cc.protest_unknown_active)
                        OR (cc.dominant_family_set = 'SUPPRESSION_ONLY' AND cc.suppression_unknown_active)
                        OR (cc.dominant_family_set = 'VIOLENCE_ONLY'   AND cc.violence_unknown_active))
                ) THEN 'LOW'

            -- MEDIUM conditions
            WHEN (CASE cc.dominant_family_set
                    WHEN 'ALL_THREE'           THEN (cc.protest_unknown_active
                                                    OR cc.violence_unknown_active
                                                    OR cc.suppression_unknown_active)
                    WHEN 'PROTEST_SUPPRESSION'  THEN (cc.protest_unknown_active
                                                    OR cc.suppression_unknown_active)
                    WHEN 'SUPPRESSION_VIOLENCE' THEN (cc.suppression_unknown_active
                                                    OR cc.violence_unknown_active)
                    WHEN 'PROTEST_ONLY'         THEN cc.protest_unknown_active
                    WHEN 'VIOLENCE_ONLY'        THEN cc.violence_unknown_active
                    WHEN 'SUPPRESSION_ONLY'     THEN cc.suppression_unknown_active
                    ELSE FALSE
                  END) THEN 'MEDIUM'

            WHEN cc.high_methodology_risk_flag = TRUE THEN 'MEDIUM'

            WHEN (CASE cc.dominant_family_set
                    WHEN 'ALL_THREE'           THEN (cc.sparse_protest_baseline_flag
                                                    OR cc.sparse_violence_baseline_flag
                                                    OR cc.sparse_suppression_baseline_flag)
                    WHEN 'PROTEST_SUPPRESSION'  THEN (cc.sparse_protest_baseline_flag
                                                    OR cc.sparse_suppression_baseline_flag)
                    WHEN 'SUPPRESSION_VIOLENCE' THEN (cc.sparse_suppression_baseline_flag
                                                    OR cc.sparse_violence_baseline_flag)
                    WHEN 'PROTEST_ONLY'         THEN cc.sparse_protest_baseline_flag
                    WHEN 'VIOLENCE_ONLY'        THEN cc.sparse_violence_baseline_flag
                    WHEN 'SUPPRESSION_ONLY'     THEN cc.sparse_suppression_baseline_flag
                    ELSE FALSE
                  END) THEN 'MEDIUM'

            WHEN (CASE cc.dominant_family_set
                    WHEN 'ALL_THREE'           THEN (cc.protest_threshold_adjacent
                                                    OR cc.violence_threshold_adjacent
                                                    OR cc.suppression_threshold_adjacent)
                    WHEN 'PROTEST_SUPPRESSION'  THEN (cc.protest_threshold_adjacent
                                                    OR cc.suppression_threshold_adjacent)
                    WHEN 'SUPPRESSION_VIOLENCE' THEN (cc.suppression_threshold_adjacent
                                                    OR cc.violence_threshold_adjacent)
                    WHEN 'PROTEST_ONLY'         THEN cc.protest_threshold_adjacent
                    WHEN 'VIOLENCE_ONLY'        THEN cc.violence_threshold_adjacent
                    WHEN 'SUPPRESSION_ONLY'     THEN cc.suppression_threshold_adjacent
                    ELSE FALSE
                  END) THEN 'MEDIUM'

            -- HIGH: all dominant conditions satisfied
            ELSE 'HIGH'
        END AS confidence_ceiling

    FROM confidence_ceiling cc
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-15: CONFIDENCE DOWNGRADE
-- BLOCKER-001: Zero variance downgrade = exactly -1 level per dominant
-- family flag, cumulative. Applied after ceiling computation.
-- Downgrade sequence: HIGH → MEDIUM → LOW → INSUFFICIENT_DATA.
-- Additional downgrades: regime_continuation_flag = -1 level.
-- ═══════════════════════════════════════════════════════════════════════════
confidence_downgrade AS (
    SELECT
        cc.*,

        -- Count downgrade units from dominant-family zero variance flags
        (CASE cc.dominant_family_set
            WHEN 'ALL_THREE'           THEN CAST(cc.protest_zero_variance_flag     AS INT64)
                                         + CAST(cc.violence_zero_variance_flag    AS INT64)
                                         + CAST(cc.suppression_zero_variance_flag AS INT64)
            WHEN 'PROTEST_SUPPRESSION'  THEN CAST(cc.protest_zero_variance_flag     AS INT64)
                                         + CAST(cc.suppression_zero_variance_flag AS INT64)
            WHEN 'SUPPRESSION_VIOLENCE' THEN CAST(cc.suppression_zero_variance_flag AS INT64)
                                         + CAST(cc.violence_zero_variance_flag    AS INT64)
            WHEN 'PROTEST_ONLY'         THEN CAST(cc.protest_zero_variance_flag     AS INT64)
            WHEN 'VIOLENCE_ONLY'        THEN CAST(cc.violence_zero_variance_flag    AS INT64)
            WHEN 'SUPPRESSION_ONLY'     THEN CAST(cc.suppression_zero_variance_flag AS INT64)
            ELSE 0
        END
        -- Continuation flag: additional -1
        + CAST(cc.regime_continuation_flag AS INT64)
        ) AS total_downgrade_units

    FROM confidence_ceiling_computed cc
),

confidence_final AS (
    SELECT
        cd.*,

        -- Map ceiling → ordinal → apply downgrade → map back to label
        -- Ordinal: HIGH=3, MEDIUM=2, LOW=1, INSUFFICIENT_DATA=0
        -- Ceiling cannot degrade below INSUFFICIENT_DATA (0)
        CASE GREATEST(
            0,
            CASE cd.confidence_ceiling
                WHEN 'HIGH'                THEN 3
                WHEN 'MEDIUM'              THEN 2
                WHEN 'LOW'                 THEN 1
                WHEN 'INSUFFICIENT_DATA'   THEN 0
                ELSE 3
            END - cd.total_downgrade_units
        )
            WHEN 3 THEN 'HIGH'
            WHEN 2 THEN 'MEDIUM'
            WHEN 1 THEN 'LOW'
            ELSE 'INSUFFICIENT_DATA'
        END AS confidence_level,

        -- Methodology caveat: REPRESSION + elevated methodology risk
        (cd.final_regime_state = 'REPRESSION'
            AND cd.methodology_risk_share > cd.methodology_cap_threshold) AS methodology_caveat_required

    FROM confidence_downgrade cd
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-16: TRANSITION DETECTION
-- Compares final_regime_state to prior_regime_state.
-- Computes transition_type, significance, confidence.
--
-- MAINTAINABILITY: final_regime_state can differ from candidate_regime
-- (CTE-10) due to exit-persistence (CTE-11) and validity-gap (CTE-12)
-- adjustments, so the hierarchy ordinals for final_regime_state and
-- prior_regime_state cannot simply reuse candidate_hierarchy /
-- prior_hierarchy from CTE-11 as-is for final_regime_state. prior_hierarchy
-- IS reusable directly (prior_regime_state is unchanged from CTE-11 onward).
-- The mapping for final_regime_state is computed once below
-- (final_regime_hierarchy) and reused for both the ESCALATION and
-- DE_ESCALATION comparisons, instead of being written out twice inline.
-- The mapping values themselves (CRISIS=7 ... STABLE=1) are unchanged and
-- identical to CTE-11.
-- ═══════════════════════════════════════════════════════════════════════════
transition_hierarchy AS (
    SELECT
        cf.*,

        CASE cf.final_regime_state
            WHEN 'CRISIS'        THEN 7
            WHEN 'ESCALATION'    THEN 6
            WHEN 'CONTESTATION'  THEN 5
            WHEN 'REPRESSION'    THEN 4
            WHEN 'CONFLICT'      THEN 3
            WHEN 'MOBILISATION'  THEN 2
            ELSE 1
        END AS final_regime_hierarchy

    FROM confidence_final cf
),

transition_detection AS (
    SELECT
        th.*,

        -- Transition detected when regime changes and continuation is not active
        (th.final_regime_state <> th.prior_regime_state
            AND th.regime_continuation_flag = FALSE
            AND th.regime_held_by_exit_persistence = FALSE
            AND th.is_first_observation_week = FALSE) AS transition_detected,

        -- Transition type
        CASE
            WHEN th.is_first_observation_week THEN 'INITIAL'
            WHEN th.final_regime_state = th.prior_regime_state
                OR th.regime_continuation_flag = TRUE
                OR th.regime_held_by_exit_persistence = TRUE THEN 'PERSISTENCE'
            WHEN th.final_regime_hierarchy > th.prior_hierarchy THEN 'ESCALATION'
            WHEN th.final_regime_hierarchy < th.prior_hierarchy THEN 'DE_ESCALATION'
            ELSE 'LATERAL'
        END AS transition_type,

        -- Transition significance
        CASE
            WHEN th.final_regime_state IN ('CRISIS', 'ESCALATION')
                AND th.prior_regime_state NOT IN ('CRISIS', 'ESCALATION') THEN 'HIGH'
            WHEN th.final_regime_state = 'STABLE'
                AND th.prior_regime_state = 'MOBILISATION' THEN 'LOW'
            WHEN th.final_regime_state <> th.prior_regime_state
                AND th.regime_continuation_flag = FALSE THEN 'MEDIUM'
            ELSE NULL
        END AS transition_significance,

        -- Transition confidence: minimum of prior and current
        CASE
            WHEN LEAST(
                CASE th.confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END,
                CASE th.prior_confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END
            ) = 3 THEN 'HIGH'
            WHEN LEAST(
                CASE th.confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END,
                CASE th.prior_confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END
            ) = 2 THEN 'MEDIUM'
            WHEN LEAST(
                CASE th.confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END,
                CASE th.prior_confidence_level
                    WHEN 'HIGH'                THEN 3
                    WHEN 'MEDIUM'              THEN 2
                    WHEN 'LOW'                 THEN 1
                    ELSE 0
                END
            ) = 1 THEN 'LOW'
            ELSE 'INSUFFICIENT_DATA'
        END AS transition_confidence

    FROM transition_hierarchy th
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-17: CLASSIFICATION REASON ASSEMBLY
-- Format: {REGIME}:{PATHWAY_OR_CONDITION}|{DOMINANT_BANDS}|
--          {CONFIDENCE_DRIVER}|{FLAGS}
-- ═══════════════════════════════════════════════════════════════════════════
reason_assembly AS (
    SELECT
        td.*,

        CONCAT(
            -- Regime and condition
            td.final_regime_state, ':',
            CASE td.final_regime_state
                WHEN 'CRISIS'        THEN CASE
                                            WHEN td.crisis_fallback_qualifies THEN 'INDEX_FALLBACK'
                                            WHEN td.protest_band = 'SEVERE' AND td.suppression_band = 'SEVERE' AND td.velocity_band = 'HIGH' THEN 'PROTEST_SUPPRESSION_SEVERE_VELOCITY'
                                            ELSE 'THREE_FAMILY_SEVERE'
                                          END
                WHEN 'ESCALATION'    THEN COALESCE(td.escalation_pathway, 'PATHWAY_A')
                WHEN 'CONTESTATION'  THEN 'BOTH_ELEVATED'
                WHEN 'REPRESSION'    THEN 'SUPPRESSION_DISPROPORTIONATE'
                WHEN 'CONFLICT'      THEN 'VIOLENCE_ONLY'
                WHEN 'MOBILISATION'  THEN 'PROTEST_ELEVATED'
                WHEN 'STABLE'        THEN IF(td.stable_insufficient_data_case, 'NO_EVIDENCE', 'ALL_NORMAL')
                ELSE 'UNKNOWN'
            END,
            -- Dominant bands
            '|protest=', td.protest_band,
            IF(td.protest_pressure_z IS NOT NULL,
               CONCAT('(z=', CAST(ROUND(td.protest_pressure_z, 2) AS STRING), ')'),
               CONCAT('(idx=', CAST(ROUND(td.protest_pressure_index, 2) AS STRING), ')')),
            ',suppression=', td.suppression_band,
            IF(td.suppression_z IS NOT NULL,                          -- << FIXED
               CONCAT('(z=', CAST(ROUND(td.suppression_z, 2) AS STRING), ')'),  -- << FIXED
               CONCAT('(idx=', CAST(ROUND(td.suppression_intensity_index, 2) AS STRING), ')')),
            ',violence=', td.violence_band,
            IF(td.violence_pressure_z IS NOT NULL,
               CONCAT('(z=', CAST(ROUND(td.violence_pressure_z, 2) AS STRING), ')'),
               CONCAT('(idx=', CAST(ROUND(td.violence_pressure_index, 2) AS STRING), ')')),
            -- Confidence driver
            '|', td.confidence_level, ':', td.confidence_ceiling,
            IF(td.total_downgrade_units > 0, CONCAT('-', CAST(td.total_downgrade_units AS STRING), 'lvl'), ''),
            -- Flags
            '|',
            ARRAY_TO_STRING(
                ARRAY(SELECT f FROM UNNEST([
                    IF(td.fallback_used, 'fallback_applied', NULL),
                    IF(td.regime_continuation_flag, 'continuation', NULL),
                    IF(td.regime_held_by_exit_persistence, 'exit_persistence', NULL),
                    IF(td.pre_transition_flag, CONCAT('pre_transition:', td.pre_transition_target), NULL),
                    IF(td.methodology_caveat_required, 'caveat_required', NULL)
                ]) f WHERE f IS NOT NULL),
                ','
            )
        ) AS classification_reason,

        -- Regime explanation (human-readable)
        CONCAT(
            td.final_regime_state, ' assigned because ',
            CASE td.final_regime_state
                WHEN 'CRISIS'        THEN 'severe convergence of primary pressure families'
                WHEN 'ESCALATION'    THEN CONCAT('ESCALATION via ', COALESCE(td.escalation_pathway, 'PATHWAY_A'))
                WHEN 'CONTESTATION'  THEN 'protest and suppression both elevated'
                WHEN 'REPRESSION'    THEN 'suppression elevated without proportionate protest or violence'
                WHEN 'CONFLICT'      THEN 'violence elevated without civic contestation dynamics'
                WHEN 'MOBILISATION'  THEN 'protest elevated without state response'
                WHEN 'STABLE'        THEN 'all signal families within historical norms'
                ELSE 'default'
            END,
            '. Confidence: ', td.confidence_level,
            IF(td.methodology_caveat_required, ' [METHODOLOGY CAVEAT REQUIRED — ACLED-RQ-004]', '')
        ) AS regime_explanation

    FROM transition_detection td
),

-- ═══════════════════════════════════════════════════════════════════════════
-- CTE-18: SUPPORTING SIGNAL SUMMARY AND THRESHOLDS JSON
-- All signals, bands, flags, and active thresholds serialised per row.
-- ═══════════════════════════════════════════════════════════════════════════
signal_summary_assembly AS (
    SELECT
        ra.*,

        TO_JSON_STRING(STRUCT(
            ra.protest_band,
            ra.violence_band,
            ra.suppression_band,
            COALESCE(ra.disorder_band, 'NULL') AS disorder_band,
            COALESCE(ra.velocity_band, 'NULL') AS velocity_band,
            COALESCE(ra.conversion_band, 'NULL') AS conversion_band,
            ra.protest_pressure_z,
            ra.violence_pressure_z,
            ra.suppression_z,                               -- << FIXED
            ra.protest_pressure_index,
            ra.violence_pressure_index,
            ra.suppression_intensity_index,
            ra.protest_index_status,
            ra.violence_index_status,
            ra.suppression_index_status,
            ra.escalation_velocity_score,
            ra.pressure_conversion_rate,
            ra.event_diversity_index,
            ra.signal_valid,
            ra.sparse_protest_baseline_flag,
            ra.sparse_violence_baseline_flag,
            ra.sparse_suppression_baseline_flag,
            ra.protest_zero_variance_flag,
            ra.violence_zero_variance_flag,
            ra.suppression_zero_variance_flag,
            ra.high_methodology_risk_flag,
            ra.methodology_risk_share,
            ra.fallback_used,
            ra.protest_fallback_active,
            ra.violence_fallback_active,
            ra.suppression_fallback_active,
            ra.z_elevated AS z_elevated_threshold,
            ra.z_severe   AS z_severe_threshold,
            ra.z_adjacency_margin,
            ra.confidence_ceiling,
            ra.total_downgrade_units
        )) AS supporting_signal_summary,

        TO_JSON_STRING(STRUCT(
            ra.z_elevated,
            ra.z_severe,
            ra.z_adjacency_margin,
            ra.velocity_high_threshold,
            ra.conversion_high_threshold,
            ra.index_fallback_multiplier,
            ra.index_fallback_min_weeks,
            ra.k_disorder,
            ra.crisis_exit_weeks,
            ra.escalation_exit_weeks,
            ra.repression_exit_weeks,
            ra.validity_gap_max_weeks,
            ra.entry_persistence_weeks,
            ra.methodology_cap_threshold,
            'PROVISIONAL_CALIBRATION_VALUES' AS calibration_status,
            ra.regime_methodology_version
        )) AS thresholds_active_json,

        -- Secondary regime characteristics excluding primary regime
        (SELECT TO_JSON_STRING(ARRAY(
                SELECT r FROM UNNEST(JSON_VALUE_ARRAY(ra.qualifying_regimes_json)) r
                WHERE r <> ra.final_regime_state
        ))) AS secondary_regime_characteristics

    FROM reason_assembly ra
)

-- ═══════════════════════════════════════════════════════════════════════════
-- FINAL SELECT
-- Assembles all output fields per Implementation Specification Section 9.1.
-- Column names match the self-referential lag join expectations.
--
-- PERSISTENCE OUTPUT CONTRACT: the columns weeks_in_current_regime,
-- pre_transition_flag, pre_transition_target, regime_continuation_flag,
-- consecutive_lower_weeks, and consecutive_invalid_weeks emitted below are
-- read back by CTE-03 (persistence_context) on the NEXT invocation of this
-- asset for week N+1, via the merge-materialised output table. Renaming,
-- removing, or changing the semantics of any of these columns breaks the
-- persistence state machine for all downstream weeks. See EXECUTION
-- CONTRACT in the asset description header.
-- ═══════════════════════════════════════════════════════════════════════════
SELECT
    -- ── GRAIN ─────────────────────────────────────────────────────────────
    sa.week_start_date,
    sa.country,
    sa.iso2,
    sa.data_grain,

    -- ── PRIMARY CLASSIFICATION ────────────────────────────────────────────
    sa.final_regime_state AS primary_regime,
    sa.confidence_level,
    sa.methodology_caveat_required,

    -- ── TRANSITION ────────────────────────────────────────────────────────
    sa.transition_detected,
    sa.prior_regime_state      AS previous_regime,
    sa.weeks_in_current_regime AS regime_duration_weeks,   -- user-friendly alias, original column still exists for self-join
    sa.transition_type,
    sa.transition_significance,
    sa.transition_confidence,

    -- ── ESCALATION PATHWAY ───────────────────────────────────────────────
    CASE WHEN sa.final_regime_state = 'ESCALATION'
         THEN sa.escalation_pathway
         ELSE NULL
    END AS escalation_entry_pathway,

    -- ── SECONDARY CHARACTERISTICS ─────────────────────────────────────────
    sa.secondary_regime_characteristics,

    -- ── PERSISTENCE FLAGS ─────────────────────────────────────────────────
    sa.pre_transition_flag,                       -- << FIXED: self-join expects this name
    sa.pre_transition_target,                     -- << FIXED
    sa.regime_continuation_flag,
    sa.regime_held_by_exit_persistence,

    -- ── SIGNAL BANDS ─────────────────────────────────────────────────────
    sa.protest_band,
    sa.violence_band,
    sa.suppression_band,
    sa.disorder_band,
    sa.velocity_band,
    sa.conversion_band,

    -- ── AUDIT FIELDS ─────────────────────────────────────────────────────
    sa.classification_reason,
    sa.regime_explanation,
    sa.supporting_signal_summary,
    sa.thresholds_active_json,
    sa.fallback_used,
    sa.consecutive_lower_weeks,
    sa.consecutive_invalid_weeks,
    sa.is_first_observation_week,

    -- ── PERSISTENCE STATE FOR NEXT WEEK'S LAG JOIN ──────────────────────
    -- weeks_in_current_regime is the only column needed here that is not
    -- already emitted above under its own name/alias. pre_transition_flag,
    -- pre_transition_target, consecutive_lower_weeks, and
    -- consecutive_invalid_weeks are each emitted exactly once already
    -- (PERSISTENCE FLAGS / AUDIT FIELDS sections above) and map 1:1 to the
    -- single corresponding column in the merge target DDL. Re-emitting them
    -- here would duplicate column names in the SELECT output, which causes
    -- positional column misalignment against the merge target (observed as
    -- a null-majority materialised table).
    sa.weeks_in_current_regime,                   -- raw column for self-join (same value as regime_duration_weeks)

    -- ── VERSION ──────────────────────────────────────────────────────────
    sa.regime_methodology_version,
    sa.feature_version,
    sa.classification_methodology_version,
    sa.severity_methodology_version,
    CURRENT_TIMESTAMP() AS computed_at

FROM signal_summary_assembly sa
ORDER BY sa.week_start_date