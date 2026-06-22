/* @bruin
name: intelligence.country_initialization_status
type: bq.sql
connection: bigquery-default
tags:
  - intelligence
  - intelligence_bq
  - orchestration_metadata

description: |
  Orchestration metadata table for the historical initialization platform.
  Tracks per-country backfill state for intelligence assets that use a
  stateful self-referential merge architecture.

  PURPOSE:
  This table is the authoritative source of truth for whether a country's
  history has been sequentially initialized via backfill_acled_pressure_regimes.py
  (or equivalent future initializers). It serves three functions:

    1. LOCK: prevents concurrent initialization runs for the same country.
    2. CHECKPOINT: records the last confirmed-committed week so a crashed
       or interrupted run can resume without reprocessing completed weeks.
    3. STATUS GATE: allows orchestration to determine whether a country
       should receive a steady-state weekly run (COMPLETE) or a
       historical backfill run (PENDING / FAILED / no row).

  STRICT SEPARATION:
  This table is NEVER read by intelligence.acled_pressure_regimes or any
  other classification asset. It is orchestration metadata only. The
  intelligence asset's single responsibility is computing this week's
  regime state from features.acled_pressure_signals and the prior week's
  intelligence output. Country initialization state is not part of that
  responsibility and must not become so.

  GRAIN: one row per country.
  OWNER: backfill_acled_pressure_regimes.py (writes all fields).
  CONSUMERS: orchestration layer only (never intelligence SQL assets).

  INITIALIZATION STATUS VALUES:
    PENDING              — country registered, backfill not yet started.
    IN_PROGRESS          — backfill driver is actively running; row acts as
                           a distributed lock (see locking notes below).
    COMPLETE             — full sequential backfill finished successfully.
                           Country is eligible for steady-state weekly runs.
    FAILED               — backfill driver exited with an error. error_message
                           field contains the failure reason. Run can be
                           resumed; set to IN_PROGRESS again on retry.

  INITIALIZATION MODE VALUES:
    HISTORICAL_BACKFILL         — first-ever initialization for a country.
    REBUILD_AFTER_METHOD_CHANGE — doctrine/methodology version upgrade
                                  requires recomputing all history.
    REPAIR_AFTER_FAILURE        — resuming a previously FAILED run.

  LOCKING PROTOCOL:
  The IN_PROGRESS status acts as a soft distributed lock. Drivers MUST:
    1. Check status before acquiring. Refuse if IN_PROGRESS and
       last_updated_at is recent (within staleness threshold, e.g. 2h).
    2. Acquire lock via conditional UPDATE WHERE status != 'IN_PROGRESS'
       and check affected_rows == 1 to detect race conditions.
    3. On crash without clean exit: status remains IN_PROGRESS. A new
       driver invocation detects stale last_updated_at, logs a recovery
       event, and re-acquires the lock safely.

  METHODOLOGY VERSION:
  initialized_under_version records the regime_methodology_version
  constant (from CTE-01 of intelligence.acled_pressure_regimes) that was
  active at the time of backfill. When the methodology version increments,
  COMPLETE rows with an older initialized_under_version are detectable as
  potentially stale and candidates for REBUILD_AFTER_METHOD_CHANGE.
  Detection is the system's responsibility; triggering a rebuild is always
  a deliberate, manually-reviewed decision — not an automatic action.

  CLUSTERING:
  Clustered on (initialization_status, country) to support the two primary
  access patterns:
    - "give me all PENDING/FAILED countries that need initialization"
    - "what is the status of country X"
  No partitioning: the table will never exceed a few hundred rows (one per
  country). Partitioning would add overhead with zero benefit at this scale.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: country
    type: string
    primary_key: true
    checks:
      - name: not_null

  - name: iso2
    type: string
    checks:
      - name: not_null

  - name: initialization_status
    type: string
    description: PENDING | IN_PROGRESS | COMPLETE | FAILED
    checks:
      - name: not_null

  - name: earliest_week_available
    type: date

  - name: latest_week_backfilled
    type: date
    description: |
      Last week for which a MERGE was confirmed committed by the
      initialization driver. This is the authoritative resume checkpoint.
      Updated after every successful per-week iteration, not just at
      completion. NULL until at least one week has been committed.

  - name: total_weeks_expected
    type: integer
    description: Total distinct weeks in features.acled_pressure_signals for this country.

  - name: weeks_completed
    type: integer
    description: Number of weeks successfully merged. Updated per iteration.

  - name: started_at
    type: timestamp
    description: When the current (or most recent) initialization run began.

  - name: initialized_at
    type: timestamp
    description: When initialization reached COMPLETE status. NULL until then.

  - name: last_updated_at
    type: timestamp
    description: |
      Updated after every status change and after every per-week checkpoint.
      Used for stale-lock detection: if IN_PROGRESS and last_updated_at is
      older than the staleness threshold (2 hours), the lock is considered
      stale and may be recovered by a new driver invocation.

  - name: initialized_under_version
    type: string
    description: |
      The value of regime_methodology_version (from CTE-01) that was active
      when this country's backfill was completed. Populated only on COMPLETE.
      Used to detect whether a rebuild is required after a methodology upgrade.

  - name: initialization_mode
    type: string
    description: HISTORICAL_BACKFILL | REBUILD_AFTER_METHOD_CHANGE | REPAIR_AFTER_FAILURE

  - name: initialization_run_id
    type: string
    description: |
      UUID generated by the driver at lock-acquisition time. Unique per run
      attempt (not per country). Useful for correlating driver logs with
      status table entries when diagnosing failures.

  - name: error_message
    type: string
    description: |
      Populated when initialization_status = FAILED. Contains the exception
      message or diagnostic string from the driver's error handler. NULL
      when status is PENDING, IN_PROGRESS, or COMPLETE.
@bruin */

-- ═══════════════════════════════════════════════════════════════════════════
-- BOOTSTRAP SELECT
-- This asset uses create+replace materialization. It produces an empty
-- table with the correct schema and clustering on first deployment.
-- All subsequent writes are performed exclusively by the initialization
-- driver (backfill_acled_pressure_regimes.py) via direct BigQuery DML —
-- NOT by re-running this Bruin asset (which would truncate all state).
--
-- WARNING: Re-running this asset in Bruin after initial deployment will
-- DROP and RECREATE the table, erasing all initialization state. This
-- asset should only be run once (initial bootstrap) or deliberately
-- during a full platform reset. It is tagged 'orchestration_metadata'
-- to allow exclusion from routine pipeline runs via --exclude-tag.
--
-- CLUSTERING NOTE:
-- BigQuery DDL-level clustering is set via the OPTIONS clause below.
-- The two clustered columns match the two primary query patterns:
--   1. WHERE initialization_status IN ('PENDING', 'FAILED')
--   2. WHERE country = @country
-- ═══════════════════════════════════════════════════════════════════════════
SELECT
    CAST(NULL AS STRING)    AS country,
    CAST(NULL AS STRING)    AS iso2,
    CAST(NULL AS STRING)    AS initialization_status,
    CAST(NULL AS DATE)      AS earliest_week_available,
    CAST(NULL AS DATE)      AS latest_week_backfilled,
    CAST(NULL AS INT64)     AS total_weeks_expected,
    CAST(NULL AS INT64)     AS weeks_completed,
    CAST(NULL AS TIMESTAMP) AS started_at,
    CAST(NULL AS TIMESTAMP) AS initialized_at,
    CAST(NULL AS TIMESTAMP) AS last_updated_at,
    CAST(NULL AS STRING)    AS initialized_under_version,
    CAST(NULL AS STRING)    AS initialization_mode,
    CAST(NULL AS STRING)    AS initialization_run_id,
    CAST(NULL AS STRING)    AS error_message
FROM (SELECT 1)
WHERE FALSE