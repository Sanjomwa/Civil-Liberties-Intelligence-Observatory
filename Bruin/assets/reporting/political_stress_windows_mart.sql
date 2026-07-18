/* @bruin
tags:
  - reporting

name: reporting.mart_political_stress_windows
type: bq.sql
connection: bigquery-default

description: |
  Detects elevated digital suppression windows in Kenya by combining
  country-level pressure indicators with statistically validated OONI
  protocol interference trends.

  This v4 rebuild corrects protocol feature collinearity by reducing
  corroboration overweighting between protocol stress and elevated
  protocol count.

  ADR-0004 / TD-44 / TD-45 (2026-07-05, v5, historical -- column renamed
  by TD-66 below): the fact table's composite score, then named
  source_composite_pressure_score in this mart, no longer includes a Lumen
  legal-pressure term -- see fact_country_pressure_daily's header.
  legal_pressure_score and legal_pressure_is_synthetic are still passed
  through below for transparency/provenance, but neither feeds this mart's
  own scoring -- that was already derived from the fact table's composite
  score, not from legal_pressure_score directly, so at the time this only
  shifted that upstream value, not this mart's own formula.

  TD-66 (2026-07-18, v6): this mart used to redefine composite_pressure_score
  under the same name as the fact table's own documented, ADR-0004-cited,
  ADR-0006-decomposed score -- two different formulas sharing one column
  name (TD-45's original finding), with no cited derivation for this mart's
  four added OONI terms anywhere in this asset's history (checked: git log
  -p across every commit that touched this formula, back to its introduction
  -- no rationale found). composite_pressure_score below is now a direct,
  undecomposed-formula passthrough of fact_country_pressure_daily's own
  value -- the number CLIO's Pressure Attribution page (ADR-0006) actually
  decomposes is now the same number this mart's consumers read.

  The OONI-fused recomputation (the former composite_pressure_score, and
  its downstream rolling_baseline_pressure/pressure_delta/
  suppression_window_probability/suppression_window_class chain) is
  deleted, not renamed. A recalibration test against the Finance Bill 2024
  window (matching the old formula's historical CRITICAL/HIGH/ELEVATED
  trigger-frequency against the clean composite's own delta distribution)
  found the clean composite alone, once recalibrated, correctly classifies
  the full 2024-06-22-through-06-28 peak week CRITICAL -- including
  2024-06-25, which the OONI-fused version actually misses. The two
  detectors differed only on the 06-20/06-21 pre-storming ramp and a
  handful of isolated July days -- differences with no independent ground
  truth available to adjudicate as real signal vs. noise in the
  daily-varying OONI terms (the same per-event capture gap TD-67 already
  flags for Kenya's ACLED coverage). Given the crisis itself recovers
  cleanly once recalibrated, and the OONI terms' own weights have no cited
  derivation anywhere in this asset's history, the undocumented formula is
  retired outright rather than kept under a relabeled name. TD-45's
  underlying naming collision is closed by the same removal -- there is
  now only one composite_pressure_score formula in this codebase, defined
  once, in fact_country_pressure_daily.sql.

  OONI's protocol/network signals (signal_rate, weighted_blocking,
  max_protocol_anomaly_score, max_protocol_stress_score,
  elevated_protocol_count, avg_sample_quality_score) are unaffected by
  this change and remain below as their own passthrough columns -- they
  were never part of composite_pressure_score's own definition, only of
  the now-deleted recomputation.

depends:
  - reporting.mart_protocol_interference_trends
  - marts.fact_country_pressure_daily
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH network AS (

    SELECT
        date_key AS measurement_date,

        AVG(signal_rate) AS signal_rate,

        AVG(confidence_weighted_interference)
            AS weighted_blocking,

        MAX(anomaly_score)
            AS max_protocol_anomaly_score,

        MAX(protocol_stress_score)
            AS max_protocol_stress_score,

        COUNTIF(trend_state IN (
            'CRITICAL_PROTOCOL_SHIFT',
            'HIGH_PROTOCOL_ANOMALY'
        )) AS elevated_protocol_count,

        AVG(sample_quality_score)
            AS avg_sample_quality_score

    FROM `{{ var.project_id }}.reporting.mart_protocol_interference_trends`

    GROUP BY measurement_date
),

country_pressure AS (

    SELECT
        measurement_date,

        conflict_pressure_score,

        -- ADR-0004 / TD-44 / TD-45: passthrough only, as of 2026-07-05 --
        -- legal_pressure_score is no longer a term in
        -- composite_pressure_score below (see fact_country_pressure_daily
        -- header). Kept here for transparency/provenance, not consumed by
        -- this mart's own arithmetic.
        legal_pressure_score,
        platform_pressure_score,
        legal_pressure_is_synthetic,

        -- TD-66: direct, undecomposed-formula passthrough of the fact
        -- table's own documented composite_pressure_score/pressure_level --
        -- no longer recomputed under this same name below.
        composite_pressure_score,
        pressure_level,

        -- ADR-0002 step (e): additive ACLED path A passthrough.
        -- Not consumed by this mart's own composite-score arithmetic --
        -- surfaced for reporting only.
        regime_primary_regime,
        regime_confidence_level,
        regime_transition_detected,
        regime_transition_type,
        regime_previous_regime,
        regime_protest_band,
        regime_violence_band,
        regime_suppression_band,
        regime_disorder_band

    FROM `{{ var.project_id }}.marts.fact_country_pressure_daily`

    WHERE iso2 = '{{ var.iso2 }}'
)

SELECT
    d.date_key,

    COALESCE(c.conflict_pressure_score, 0)
        AS conflict_pressure,

    COALESCE(c.legal_pressure_score, 0)
        AS legal_pressure,

    -- TD-01: FALSE (not NULL) when this date has no country_pressure
    -- row at all, matching the COALESCE(...,0) treatment above.
    COALESCE(c.legal_pressure_is_synthetic, FALSE)
        AS legal_pressure_is_synthetic,

    COALESCE(c.platform_pressure_score, 0)
        AS platform_pressure,

    COALESCE(c.composite_pressure_score, 0)
        AS composite_pressure_score,

    COALESCE(c.pressure_level, 'LOW')
        AS pressure_level,

    -- ADR-0002 step (e): nullable passthrough, not COALESCEd --
    -- NULL means no regime classification exists for this date
    -- (e.g. outside the backfilled range), which is a different
    -- and more honest signal than a fabricated default.
    c.regime_primary_regime,
    c.regime_confidence_level,
    c.regime_transition_detected,
    c.regime_transition_type,
    c.regime_previous_regime,
    c.regime_protest_band,
    c.regime_violence_band,
    c.regime_suppression_band,
    c.regime_disorder_band,

    COALESCE(n.signal_rate, 0)
        AS signal_rate,

    COALESCE(n.weighted_blocking, 0)
        AS weighted_blocking,

    COALESCE(n.max_protocol_anomaly_score, 0)
        AS max_protocol_anomaly_score,

    COALESCE(n.max_protocol_stress_score, 0)
        AS max_protocol_stress_score,

    COALESCE(n.elevated_protocol_count, 0)
        AS elevated_protocol_count,

    COALESCE(n.avg_sample_quality_score, 0)
        AS avg_sample_quality_score,

    'political_stress_windows_mart_v6'
        AS reporting_version,

    CURRENT_TIMESTAMP()
        AS snapshot_at

FROM `{{ var.project_id }}.marts.dim_dates` d

LEFT JOIN country_pressure c
    ON d.date_key = c.measurement_date

LEFT JOIN network n
    ON d.date_key = n.measurement_date

ORDER BY d.date_key
