/* @bruin
tags:
  - staging
  - staging_bq
  - dataset_acled_conflict_events

name: stg.acled_conflict_events
type: bq.sql
connection: bigquery-default

description: |
  ACLED staging layer. Source facts only.

  SCOPE:
  This asset stops at grain metadata, quality metadata, and source
  preservation. It records what ACLED said. It does not infer what
  ACLED means.

  All KCLIO interpretation — sub_event_category, pressure_domain,
  suppression markers — lives in int.acled_event_classification.
  That boundary is the same boundary maintained between
  stg.ooni_tcp_observations and int.ooni_experiment_results.

  GRAIN:
  The source dataset is a weekly aggregated ACLED export.
  Each row represents aggregated events within a geographic unit
  (country + admin1) for one calendar week.

  week_start_date is the Monday anchor of that week.
  It is NOT an individual event date.
  Minimum detectable lag in downstream analysis = 7 days.
  Day-level lead times within the same week are not distinguishable.

  event_date is NULL for all rows from this pipeline.
  It is reserved for future event-level ACLED ingestion where
  one row = one event with a specific date.

  data_grain = 'WEEKLY_AGGREGATE' is hardcoded on every row.
  Future event-level pipeline sets 'DAILY_EVENT'.
  Downstream assets must document which grain was used.

  QUALITY FLAGS:
  Three flags surface data quality issues explicitly.
  None of them silently absorb missing data.

  week_parse_failed:
    TRUE when SAFE.PARSE_DATE returns NULL.
    Rows where TRUE are excluded from this asset's output
    but counted before the filter for monitoring purposes.

  population_exposure_missing:
    TRUE when population_exposure IS NULL.
    Coverage is systematically absent pre-2017.
    Downstream assets must NOT coalesce to 0.
    Confidence must degrade explicitly when this flag is TRUE.

  low_event_density:
    TRUE when events <= 1.
    Threshold is a placeholder pending empirical calibration
    against Kenya data (ACLED-RQ-005).
    Analogous to low_sample_flag in protocol_daily_signals.sql.

  COUNTRY SCOPE:
  Full Africa-wide dataset is materialised here.
  Country filtering is applied at the feature layer.
  This supports multi-country deployment without modifying staging.

  WHAT IS NOT HERE:
  sub_event_category     — lives in int.acled_event_classification
  pressure_domain        — lives in int.acled_event_classification
  suppression markers    — lives in int.acled_event_classification
  Any KCLIO inference    — lives downstream of this asset

owner: civil-liberties-pipeline

depends:
  - load.acled_conflict_events_to_gcs

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week_start_date
    type: date
    description: |
      Monday anchor date of the aggregated week.
      NOT an individual event date.
      Grain is WEEKLY_AGGREGATE.
    checks:
      - name: not_null

  - name: week
    type: string
    description: |
      Original ACLED week string e.g. "23-October-2004".
      Preserved verbatim for audit and source traceability.

  - name: data_grain
    type: string
    description: |
      Hardcoded as WEEKLY_AGGREGATE for this pipeline.
      Future event-level pipeline sets DAILY_EVENT.
    checks:
      - name: not_null
      - name: accepted_values
        value: ["WEEKLY_AGGREGATE", "DAILY_EVENT"]

  - name: event_date
    type: date
    description: |
      NULL for all weekly aggregated rows.
      Reserved for future event-level ACLED ingestion.

  - name: region
    type: string
    description: ACLED region e.g. "Eastern Africa".

  - name: country
    type: string
    description: Country name as provided by ACLED.
    checks:
      - name: not_null

  - name: admin1
    type: string
    description: First administrative division.

  - name: event_type
    type: string
    description: |
      ACLED top-level event classification.
      Preserved verbatim. Not interpreted here.
    checks:
      - name: not_null

  - name: sub_event_type
    type: string
    description: |
      ACLED sub-event classification.
      Preserved verbatim. Not interpreted here.
      Classification into KCLIO pressure domains happens
      in int.acled_event_classification.
    checks:
      - name: not_null

  - name: disorder_type
    type: string
    description: ACLED disorder classification. Preserved verbatim.

  - name: events
    type: integer
    description: |
      Number of aggregated events for this unit and week.
      NULL normalised to 1 (single undocumented event).

  - name: fatalities
    type: integer
    description: |
      Number of fatalities for this unit and week.
      NULL normalised to 0.

  - name: population_exposure
    type: float
    description: |
      ACLED-provided population exposure estimate.
      Preserved as nullable. Not coalesced to 0.
      Use population_exposure_missing to handle absence explicitly.

  - name: population_exposure_missing
    type: boolean
    description: |
      TRUE when population_exposure IS NULL.
      Systematic absence pre-2017 — not random missingness.
      Downstream confidence must degrade when TRUE.
    checks:
      - name: not_null

  - name: week_parse_failed
    type: boolean
    description: |
      TRUE when SAFE.PARSE_DATE returned NULL for the week string.
      Rows where TRUE are excluded from output.
      Counted before exclusion for pipeline monitoring.
    checks:
      - name: not_null

  - name: low_event_density
    type: boolean
    description: |
      TRUE when events <= 1.
      Placeholder threshold pending calibration (ACLED-RQ-005).
      Intelligence layer treats TRUE rows as suppression candidates.
    checks:
      - name: not_null

  - name: id
    type: float
    description: ACLED record identifier. Preserved for source traceability.

  - name: centroid_latitude
    type: float
    description: |
      Latitude of the administrative centroid.
      All current rows carry ADMIN1_CENTROID precision.
      Not event-precise coordinates.

  - name: centroid_longitude
    type: float
    description: |
      Longitude of the administrative centroid.
      All current rows carry ADMIN1_CENTROID precision.
      Not event-precise coordinates.

  - name: spatial_precision
    type: string
    description: |
      KCLIO-labelled spatial precision tier.
      ADMIN1_CENTROID: all rows from this weekly aggregate pipeline.
      EVENT_PRECISE: reserved for future event-level ingestion.
      Spatial Diffusion Score must document this value in outputs.

  - name: extracted_at
    type: timestamp
    description: Pipeline extraction timestamp. Preserved from source.

  - name: year
    type: integer
    description: Calendar year extracted from week_start_date.

  - name: month
    type: integer
    description: Calendar month extracted from week_start_date.

  - name: day
    type: integer
    description: Day of month extracted from week_start_date.

@bruin */

WITH parsed AS (

    SELECT
        week,
        region,
        country,
        admin1,
        event_type,
        sub_event_type,
        disorder_type,
        id,
        centroid_latitude,
        centroid_longitude,
        extracted_at,

        -- Normalise event count: NULL → 1 (single undocumented event)
        COALESCE(events, 1)      AS events,

        -- Normalise fatalities: NULL → 0
        COALESCE(fatalities, 0)  AS fatalities,

        -- population_exposure preserved as nullable.
        -- population_exposure_missing surfaces the gap explicitly.
        population_exposure,

        -- Parse ACLED week string "23-October-2004" → DATE 2004-10-23.
        -- SAFE variant returns NULL on parse failure rather than erroring.
        SAFE.PARSE_DATE(
            '%d-%B-%Y',
            week
        ) AS week_start_date

    FROM `{{ var.project_id }}.{{ var.bq_dataset }}.acled_conflict_events`

),

with_flags AS (

    SELECT
        *,
        (week_start_date IS NULL)       AS week_parse_failed,
        (population_exposure IS NULL)   AS population_exposure_missing,
        (events <= 1)                   AS low_event_density
    FROM parsed

)

SELECT

    -- ── TEMPORAL ────────────────────────────────────────────────────────────
    week_start_date,
    week,

    -- Hardcoded grain marker for this weekly aggregate pipeline.
    'WEEKLY_AGGREGATE'              AS data_grain,

    -- NULL for all weekly rows. Reserved for event-level ingestion.
    CAST(NULL AS DATE)              AS event_date,

    -- ── GEOGRAPHIC ──────────────────────────────────────────────────────────
    region,
    country,
    admin1,
    centroid_latitude,
    centroid_longitude,

    -- All current rows are centroid-assigned, not event-precise.
    'ADMIN1_CENTROID'               AS spatial_precision,

    -- ── ACLED SOURCE FIELDS — VERBATIM ──────────────────────────────────────
    -- These fields record what ACLED said.
    -- No KCLIO interpretation is applied here.
    event_type,
    sub_event_type,
    disorder_type,
    events,
    fatalities,
    population_exposure,

    -- ── QUALITY FLAGS ────────────────────────────────────────────────────────
    week_parse_failed,
    population_exposure_missing,
    low_event_density,

    -- ── SOURCE TRACEABILITY ──────────────────────────────────────────────────
    id,
    extracted_at,

    -- ── DATE PARTS ───────────────────────────────────────────────────────────
    EXTRACT(YEAR  FROM week_start_date) AS year,
    EXTRACT(MONTH FROM week_start_date) AS month,
    EXTRACT(DAY   FROM week_start_date) AS day

FROM with_flags

-- Exclude rows with no valid temporal anchor.
-- week_parse_failed is computed before this filter
-- so pipeline monitoring can count failures upstream.
WHERE week_start_date IS NOT NULL;
