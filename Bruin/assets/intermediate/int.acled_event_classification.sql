/* @bruin
tags:
  - intermediate
  - dataset_acled_conflict_events

name: int.acled_event_classification
type: bq.sql
connection: bigquery-default

description: |
  KCLIO interpretation layer for ACLED event vocabulary.
  Version: 4.0 — Production-ready for KCLIO Phase 1.

  ──────────────────────────────────────────────────────────────────────
  SCOPE
  ──────────────────────────────────────────────────────────────────────
  This asset translates ACLED source vocabulary into KCLIO analytical
  vocabulary. It records what KCLIO inferred from what ACLED said.
  It does not modify what ACLED said.

  Staging owns:     what ACLED said.
  This asset owns:  what KCLIO inferred.

  DEPENDENCY CHAIN:
    stg.acled_conflict_events       → ACLED source facts
    int.acled_event_classification  → KCLIO inference    ← this asset
    feat.acled_pressure_signals     → signal engineering
    int.acled_pressure_regimes      → regime classification

  ──────────────────────────────────────────────────────────────────────
  DESIGN PRINCIPLES
  ──────────────────────────────────────────────────────────────────────

  Principle 1 — Interpret only what the dataset can support.
    The aggregated ACLED export does not contain actor1, actor2,
    associated_actor, or interaction code fields. Without actor-level
    data, state actor identity cannot be established.
    No field in this asset attempts to infer state involvement.
    State attribution is future work pending event-level ACLED data.
    Observable outputs only: is_suppression_marker and is_civic_response
    derive from ACLED vocabulary, not actor inference.

  Principle 2 — pressure_domain from event_type only.
    ACLED event_type is stable across methodology versions.
    sub_event_type taxonomy changes by country and time period.
    (ACLED-RQ-004). Deriving primary domain from event_type only
    maximises historical comparability and reduces maintenance burden.

  Principle 3 — dual contribution via independent boolean flags.
    A single event contributes to multiple KCLIO pressure dimensions.
    Example:
      event_type:            Protests
      sub_event_type:        Excessive force against protesters
      pressure_domain:       PROTEST
      is_suppression_marker: TRUE
      is_civic_response:     TRUE
    This row contributes to Protest Pressure Index AND to
    Suppression Intensity Index simultaneously.

  Principle 4 — suppression is strictly defined.
    Suppression requires observable civic activity + directed response.
    General political violence is not suppression.
    Expand only when evidence from data review supports it.

  Principle 5 — classification uncertainty and methodology risk
    are separate concepts and must be separated in the schema.
    classification_confidence: how certain is KCLIO's inference
      for this specific event.
    methodology_risk_level: how likely is cross-country methodology
      variation to affect interpretation of this event_type.
    Example: Strategic developments Arrests → confidence HIGH
    (the classification is clear) but methodology_risk HIGH
    (ACLED applies this category differently by country).

  Principle 6 — uncertainty is first-class metadata.
    classification_confidence, is_ambiguous_event,
    methodology_risk_level, classification_methodology_version,
    and severity_methodology_version are mandatory outputs.
    Uncertainty must be visible, not hidden.
    This mirrors the OONI platform's high_unknown_flag and
    guardrail_config_json philosophy.

  ──────────────────────────────────────────────────────────────────────
  OUTPUTS
  ──────────────────────────────────────────────────────────────────────

  pressure_domain               — primary KCLIO pressure category
  is_suppression_marker         — civic activity + directed response
  is_civic_response             — act directed at protests/assembly
  severity_tier                 — fatality-based severity (V1)
  is_high_severity              — derived from severity_tier
  classification_confidence     — HIGH / MEDIUM / LOW
  is_ambiguous_event            — derived from confidence = LOW
  methodology_risk_level        — LOW / MEDIUM / HIGH (ACLED-RQ-004)
  classification_note           — plain-language explanation
  classification_methodology_version — framework version tag
  severity_methodology_version  — severity model version tag

  ──────────────────────────────────────────────────────────────────────
  KNOWN LIMITATIONS
  ──────────────────────────────────────────────────────────────────────

  ACLED-RQ-004 (Country methodology variation):
    ACLED applies country-specific methodology that alters sub_event_type
    meaning across political contexts. methodology_risk_level operationalises
    this risk at the row level. Resolution depends on the Country
    Configuration Framework.

  Actor data absence:
    Aggregated ACLED exports do not contain actor fields.
    State actor attribution has been intentionally excluded from v4.
    Future upgrade to event-level ACLED data will enable actor-based
    classification.

  Severity model:
    V1 uses fatality count only. Future impact_score will incorporate
    event_count, population_exposure, and event_type weighting.
    severity_methodology_version enables schema-stable upgrade.

owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week_start_date
    type: date
    description: Week anchor date. Passed through from staging.
    checks:
      - name: not_null

  - name: data_grain
    type: string
    description: WEEKLY_AGGREGATE for all current rows.
    checks:
      - name: not_null

  - name: event_date
    type: date
    description: NULL for weekly aggregate rows. Reserved for event-level data.

  - name: region
    type: string
    description: ACLED region. Passed through verbatim.

  - name: country
    type: string
    description: Country name. Passed through verbatim.
    checks:
      - name: not_null

  - name: admin1
    type: string
    description: First administrative division. Passed through verbatim.

  - name: spatial_precision
    type: string
    description: Spatial precision tier. Passed through from staging.

  - name: centroid_latitude
    type: float
    description: Admin1 centroid latitude. Passed through verbatim.

  - name: centroid_longitude
    type: float
    description: Admin1 centroid longitude. Passed through verbatim.

  - name: event_type
    type: string
    description: ACLED top-level event classification. Preserved verbatim.
    checks:
      - name: not_null

  - name: sub_event_type
    type: string
    description: ACLED sub-event classification. Preserved verbatim.
    checks:
      - name: not_null

  - name: disorder_type
    type: string
    description: ACLED disorder classification. Preserved verbatim.

  - name: events
    type: integer
    description: Normalised event count from staging.

  - name: fatalities
    type: integer
    description: Normalised fatality count from staging.

  - name: population_exposure
    type: float
    description: Population exposure. Nullable. Not coalesced to zero.

  - name: pressure_domain
    type: string
    description: |
      KCLIO primary pressure domain. Derived from event_type only.
      Values: PROTEST, DISORDER, VIOLENCE, STRATEGIC, UNCLASSIFIED.
      This is KCLIO classification. Not ACLED classification.
    checks:
      - name: not_null
      - name: accepted_values
        value: ["PROTEST", "DISORDER", "VIOLENCE", "STRATEGIC", "UNCLASSIFIED"]

  - name: is_suppression_marker
    type: boolean
    description: |
      TRUE when observable civic activity + directed response is
      present in the ACLED vocabulary. Strictly defined.
      Does not require actor identification.
      Observable from sub_event_type vocabulary alone.
      Drives Suppression Intensity Index independently of pressure_domain.
    checks:
      - name: not_null

  - name: is_civic_response
    type: boolean
    description: |
      TRUE when the sub_event_type indicates a direct response to
      protest or civic assembly activity.
      Requires event_type = Protests as the civic activity anchor.
      Observable from ACLED vocabulary. Not actor-inferred.
    checks:
      - name: not_null

  - name: severity_tier
    type: string
    description: |
      KCLIO severity classification.
      severity_methodology_version = FATALITY_ONLY_V1.
        NONE:    0 fatalities
        LOW:     1–2 fatalities
        MEDIUM:  3–9 fatalities
        HIGH:    10–49 fatalities
        EXTREME: 50+ fatalities
      Future severity_methodology_version = IMPACT_SCORE_V2 will
      incorporate fatalities + event_count + population_exposure
      + event_type weighting. Schema will remain stable.
    checks:
      - name: not_null
      - name: accepted_values
        value: ["NONE", "LOW", "MEDIUM", "HIGH", "EXTREME"]

  - name: is_high_severity
    type: boolean
    description: |
      TRUE when severity_tier IN (HIGH, EXTREME).
      Derived from severity_tier.
    checks:
      - name: not_null

  - name: classification_confidence
    type: string
    description: |
      KCLIO certainty in this specific classification.
      Distinct from methodology_risk_level.
      HIGH:   unambiguous inference from stable ACLED vocabulary.
      MEDIUM: clear event_type, sub_event_type has some variability.
      LOW:    sub_event_type = Other, or vocabulary is inherently
              ambiguous for this row.
      Mirrors the HIGH/MEDIUM/LOW tiers in marts.dim_censorship_confidence,
      OONI's own confidence-bucketing scheme (unified there under ADR-0001).
      Computed independently -- this is not a functional dependency.
    checks:
      - name: not_null
      - name: accepted_values
        value: ["HIGH", "MEDIUM", "LOW"]

  - name: is_ambiguous_event
    type: boolean
    description: |
      TRUE when classification_confidence = LOW.
      Convenience field for downstream filtering.
      Mirrors high_unknown_flag pattern in OONI pipeline.
      Downstream assets should suppress or degrade signals
      where is_ambiguous_event = TRUE.
    checks:
      - name: not_null

  - name: methodology_risk_level
    type: string
    description: |
      Likelihood that cross-country ACLED methodology variation
      affects interpretation of this event_type.
      Operationalises ACLED-RQ-004 at the row level.
      Distinct from classification_confidence.
      HIGH:   Strategic developments, UNCLASSIFIED.
              ACLED methodology varies most for these categories.
      LOW:    Protests, Riots, Battles, Violence against civilians,
              Explosions/Remote violence.
              Top-level classification is stable across contexts.
      AI report generation must caveat HIGH risk rows explicitly.
    checks:
      - name: not_null
      - name: accepted_values
        value: ["LOW", "HIGH"]

  - name: classification_note
    type: string
    description: |
      Plain-language explanation of the classification decision.
      Explains what happened in this specific row.
      Covers dual contributions, ambiguities, and edge cases.
      NULL for unambiguous, single-contribution rows.

  - name: classification_methodology_version
    type: string
    description: |
      Version of the ACLED Intelligence Framework that produced
      this row's classification. Enables retrospective audit.
      Equivalent to guardrail_config_json in OONI pipeline.
      Current value: ACLED_INTELLIGENCE_FRAMEWORK_V1.
    checks:
      - name: not_null

  - name: severity_methodology_version
    type: string
    description: |
      Version of the severity model applied to this row.
      FATALITY_ONLY_V1: current model using fatality count.
      IMPACT_SCORE_V2: future composite model.
      Enables schema-stable upgrade without breaking downstream.
    checks:
      - name: not_null

  - name: population_exposure_missing
    type: boolean
    description: Quality flag passed through from staging.
    checks:
      - name: not_null

  - name: week_parse_failed
    type: boolean
    description: Quality flag passed through from staging.
    checks:
      - name: not_null

  - name: low_event_density
    type: boolean
    description: Quality flag passed through from staging.
    checks:
      - name: not_null

  - name: id
    type: float
    description: ACLED source identifier. Preserved for traceability.

  - name: extracted_at
    type: timestamp
    description: Pipeline extraction timestamp. Passed through.

  - name: year
    type: integer
    description: Passed through from staging.

  - name: month
    type: integer
    description: Passed through from staging.

  - name: day
    type: integer
    description: Passed through from staging.

@bruin */

WITH source AS (

    SELECT *
    FROM `{{ var.project_id }}.stg.acled_conflict_events`
    WHERE week_parse_failed = FALSE

),

classified AS (

    SELECT
        *,

        -- ────────────────────────────────────────────────────────────────────
        -- PRESSURE DOMAIN
        -- event_type only. See Principle 2.
        -- ────────────────────────────────────────────────────────────────────
        CASE event_type
            WHEN 'Protests'                   THEN 'PROTEST'
            WHEN 'Riots'                      THEN 'DISORDER'
            WHEN 'Battles'                    THEN 'VIOLENCE'
            WHEN 'Explosions/Remote violence' THEN 'VIOLENCE'
            WHEN 'Violence against civilians' THEN 'VIOLENCE'
            WHEN 'Strategic developments'     THEN 'STRATEGIC'
            ELSE                                   'UNCLASSIFIED'
        END AS pressure_domain,

        -- ────────────────────────────────────────────────────────────────────
        -- SUPPRESSION MARKER
        -- Observable from vocabulary. No actor inference required.
        -- Strictly: civic activity + directed response.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN LOWER(sub_event_type) IN (
                'excessive force against protesters',
                'protest with intervention'
            )                                   THEN TRUE
            WHEN LOWER(sub_event_type) LIKE '%arrest%'
              OR LOWER(sub_event_type) LIKE '%detain%'
              OR LOWER(sub_event_type) LIKE '%crackdown%'
                                                THEN TRUE
            ELSE                                     FALSE
        END AS is_suppression_marker,

        -- ────────────────────────────────────────────────────────────────────
        -- CIVIC RESPONSE
        -- Physical response to protest or assembly. Observable from
        -- vocabulary. Requires event_type = Protests as anchor.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN event_type = 'Protests'
              AND LOWER(sub_event_type) IN (
                  'excessive force against protesters',
                  'protest with intervention'
              )
            THEN TRUE
            ELSE FALSE
        END AS is_civic_response,

        -- ────────────────────────────────────────────────────────────────────
        -- SEVERITY TIER
        -- FATALITY_ONLY_V1. See severity_methodology_version.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN fatalities >= 50 THEN 'EXTREME'
            WHEN fatalities >= 10 THEN 'HIGH'
            WHEN fatalities >= 3  THEN 'MEDIUM'
            WHEN fatalities >= 1  THEN 'LOW'
            ELSE                       'NONE'
        END AS severity_tier,

        -- ────────────────────────────────────────────────────────────────────
        -- CLASSIFICATION CONFIDENCE
        -- Certainty of THIS inference. Not cross-country risk.
        -- Separated from methodology_risk_level. See Principle 5.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN LOWER(sub_event_type) = 'other'
                THEN 'LOW'
            WHEN event_type = 'Strategic developments'
                THEN 'MEDIUM'
            ELSE
                'HIGH'
        END AS classification_confidence,

        -- ────────────────────────────────────────────────────────────────────
        -- CLASSIFICATION NOTE
        -- Explains what happened in this specific classification.
        -- NULL for unambiguous single-contribution rows.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN LOWER(sub_event_type) = 'other'
                THEN 'sub_event_type is Other — inherently ambiguous across ACLED methodology versions and countries.'

            WHEN event_type = 'Protests'
              AND LOWER(sub_event_type) IN (
                  'excessive force against protesters',
                  'protest with intervention'
              )
                THEN 'Dual contribution: pressure_domain PROTEST + is_suppression_marker TRUE + is_civic_response TRUE. Contributes to Protest Pressure Index and Suppression Intensity Index simultaneously.'

            WHEN event_type = 'Protests'
              AND (
                  LOWER(sub_event_type) LIKE '%arrest%'
               OR LOWER(sub_event_type) LIKE '%detain%'
              )
                THEN 'Dual contribution: pressure_domain PROTEST + is_suppression_marker TRUE. Contributes to Protest Pressure Index and Suppression Intensity Index.'

            WHEN event_type = 'Strategic developments'
                THEN 'Strategic developments: methodology_risk_level HIGH. Sub-event meaning varies by country (ACLED-RQ-004). AI reports must caveat governance-related claims as inferred from vocabulary, not confirmed from actor data.'

            ELSE NULL
        END AS classification_note

    FROM source

),

-- Derive methodology_risk_level and is_ambiguous_event after classified CTE
-- so that methodology_risk_level can correctly reference pressure_domain.
-- Fix: WHEN pressure_domain = 'UNCLASSIFIED' (not event_type = 'UNCLASSIFIED',
-- which could never match — UNCLASSIFIED is a KCLIO value, not an ACLED value).
with_risk AS (

    SELECT
        *,

        -- ────────────────────────────────────────────────────────────────────
        -- METHODOLOGY RISK LEVEL
        -- Cross-country ACLED methodology variation risk.
        -- Operationalises ACLED-RQ-004 at row level.
        -- Separated from classification_confidence. See Principle 5.
        -- Computed here (not in classified CTE) so it can reference
        -- pressure_domain, which is derived in classified.
        -- ────────────────────────────────────────────────────────────────────
        CASE
            WHEN event_type     = 'Strategic developments' THEN 'HIGH'
            WHEN pressure_domain = 'UNCLASSIFIED'          THEN 'HIGH'
            ELSE                                                'LOW'
        END AS methodology_risk_level,

        -- Derived after classification_confidence is available.
        -- Mirrors high_unknown_flag pattern in OONI pipeline.
        (classification_confidence = 'LOW')                AS is_ambiguous_event

    FROM classified

)

SELECT

    -- ── TEMPORAL ────────────────────────────────────────────────────────────
    week_start_date,
    data_grain,
    event_date,

    -- ── GEOGRAPHIC ──────────────────────────────────────────────────────────
    region,
    country,
    admin1,
    spatial_precision,
    centroid_latitude,
    centroid_longitude,

    -- ── ACLED SOURCE FIELDS — VERBATIM ──────────────────────────────────────
    event_type,
    sub_event_type,
    disorder_type,
    events,
    fatalities,
    population_exposure,

    -- ── KCLIO CLASSIFICATION ─────────────────────────────────────────────────
    pressure_domain,
    is_suppression_marker,
    is_civic_response,

    -- Severity
    severity_tier,
    severity_tier IN ('HIGH', 'EXTREME')      AS is_high_severity,

    -- Confidence and ambiguity
    classification_confidence,
    is_ambiguous_event,

    -- Methodology risk (ACLED-RQ-004 operationalised)
    methodology_risk_level,

    -- Explanatory field
    classification_note,

    -- Version tags for retrospective audit
    'ACLED_INTELLIGENCE_FRAMEWORK_V1'         AS classification_methodology_version,
    'FATALITY_ONLY_V1'                        AS severity_methodology_version,

    -- ── QUALITY FLAGS — PASSED THROUGH ───────────────────────────────────────
    population_exposure_missing,
    week_parse_failed,
    low_event_density,

    -- ── SOURCE TRACEABILITY ──────────────────────────────────────────────────
    id,
    extracted_at,

    -- ── DATE PARTS ───────────────────────────────────────────────────────────
    year,
    month,
    day

FROM with_risk;