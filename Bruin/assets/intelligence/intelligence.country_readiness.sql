/* @bruin
name: intelligence.country_readiness
type: bq.sql
connection: bigquery-default
tags:
  - intelligence
  - intelligence_bq
  - orchestration_metadata

description: |
  Convenience view exposing only production-ready intelligence data.

  PURPOSE:
  Filters intelligence.acled_pressure_regimes to rows belonging to
  countries whose full historical backfill is COMPLETE. Partial
  initialization (PENDING, IN_PROGRESS, FAILED, or no status row)
  is excluded entirely.

  RATIONALE:
  Countries with initialization_status != 'COMPLETE' have at least some
  rows where is_first_observation_week = TRUE across their full history,
  meaning persistence-dependent regimes (REPRESSION, CONTESTATION,
  MOBILISATION, CONFLICT) are systematically under-reported and
  transition_detected is unreliable. Such rows must never be mixed with
  production-ready data in historical analysis, dashboards, or AI
  narrative generation.

  Downstream consumers SHOULD query this view rather than the base table
  directly. Any asset or dashboard that queries acled_pressure_regimes
  directly must explicitly document why it bypasses the readiness gate.

  GRAIN: identical to intelligence.acled_pressure_regimes
         (country × week_start_date), restricted to COMPLETE countries.

  UPSTREAM:
    - intelligence.acled_pressure_regimes
    - intelligence.country_initialization_status

  NOTE ON SEPARATION:
  This view is the ONLY place where country_initialization_status and
  acled_pressure_regimes are joined. The intelligence asset itself
  never reads country_initialization_status — this view exists
  specifically to enforce the readiness gate at the consumption layer,
  not the production layer.

depends:
  - intelligence.acled_pressure_regimes
  - intelligence.country_initialization_status

materialization:
  type: view

columns:
  - name: week_start_date
    type: date
    checks:
      - name: not_null

  - name: country
    type: string
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
    checks:
      - name: not_null

  - name: confidence_level
    type: string
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

  - name: feature_version
    type: string

  - name: classification_methodology_version
    type: string

  - name: severity_methodology_version
    type: string

  - name: computed_at
    type: timestamp

  - name: initialized_under_version
    type: string
    description: |
      Passthrough from country_initialization_status. Records which
      regime_methodology_version was active when this country's history
      was initialized. Allows consumers to detect rows computed under
      an older methodology version.

  - name: initialization_mode
    type: string
    description: |
      Passthrough from country_initialization_status.
      HISTORICAL_BACKFILL | REBUILD_AFTER_METHOD_CHANGE | REPAIR_AFTER_FAILURE.
@bruin */

-- ═══════════════════════════════════════════════════════════════════════════
-- READINESS GATE
-- Joins acled_pressure_regimes against country_initialization_status and
-- filters to COMPLETE countries only. All base-table columns are passed
-- through unchanged. Two metadata columns from the status table are added
-- (initialized_under_version, initialization_mode) so consumers can
-- detect potential staleness without querying the status table separately.
--
-- INNER JOIN (not LEFT JOIN) is intentional: any country with no status
-- row is treated as not-ready, same as PENDING. This is the conservative
-- safe default — unknown initialization state = excluded from analysis.
-- ═══════════════════════════════════════════════════════════════════════════
SELECT
    -- ── All base intelligence columns ────────────────────────────────────
    r.week_start_date,
    r.country,
    r.iso2,
    r.data_grain,
    r.primary_regime,
    r.confidence_level,
    r.methodology_caveat_required,
    r.transition_detected,
    r.previous_regime,
    r.regime_duration_weeks,
    r.transition_type,
    r.transition_significance,
    r.transition_confidence,
    r.escalation_entry_pathway,
    r.secondary_regime_characteristics,
    r.pre_transition_flag,
    r.pre_transition_target,
    r.regime_continuation_flag,
    r.regime_held_by_exit_persistence,
    r.protest_band,
    r.violence_band,
    r.suppression_band,
    r.disorder_band,
    r.velocity_band,
    r.conversion_band,
    r.classification_reason,
    r.regime_explanation,
    r.supporting_signal_summary,
    r.thresholds_active_json,
    r.fallback_used,
    r.consecutive_lower_weeks,
    r.consecutive_invalid_weeks,
    r.is_first_observation_week,
    r.weeks_in_current_regime,
    r.regime_methodology_version,
    r.feature_version,
    r.classification_methodology_version,
    r.severity_methodology_version,
    r.computed_at,

    -- ── Readiness metadata from status table ─────────────────────────────
    s.initialized_under_version,
    s.initialization_mode

FROM `{{ var.project_id }}.intelligence.acled_pressure_regimes` r
INNER JOIN `{{ var.project_id }}.intelligence.country_initialization_status` s
    ON  s.country = r.country
    AND s.initialization_status = 'COMPLETE'