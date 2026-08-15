/* @bruin
name: features.ooni_weekly_signals
type: bq.sql
connection: bigquery-default

tags:
  - features_bq
  - dataset_ooni
  - ooni_weekly_aggregation

description: |
  Weekly OONI signal table, Saturday-anchored (DATE_TRUNC(measurement_date,
  WEEK(SATURDAY)) -- the same anchor intelligence.acled_pressure_regimes
  uses, verified live against that table before this was written, so any
  future join lines up without a translation step).

  Grain: week_start_date x test_name.

  TWO INDEPENDENT SERIES, NEVER MERGED. This table carries two column
  groups -- anomalous_* (from int.ooni_measurement_verdicts, OONI's own
  per-measurement OK/CONFIRMED/ANOMALOUS/FAILED vocabulary) and blocked_*
  (from int.ooni_experiment_results, the per-observation result_state
  BLOCKED/OK/DOWN/UNKNOWN classification) -- placed side by side in one
  wide row per (week_start_date, test_name) for query convenience only.
  They are NOT commensurable and must never be averaged, blended, or
  combined into a single score: ANOMALOUS is a broader per-measurement
  signal (interference-consistent, not necessarily a confirmed block) and
  BLOCKED is a narrower per-observation, connection-level positive
  detection. This project's own methodology principle (Extension A,
  docs/07-governance/methodology-internal.md:52) requires disagreeing
  independent inference layers to be disclosed side by side, never
  silently merged -- the same non-merge discipline ADR-0009 already
  established for the LLM extraction layer.

  Verified before building (planning-stage assumptions checked, not
  trusted): (1) int.ooni_experiment_results carries a real test_name
  column (not just protocol) -- confirmed via INFORMATION_SCHEMA.COLUMNS,
  so blocked_* aggregates at test_name grain natively, no translation
  needed. This also matches the grain the existing Phase 0 golden fixture
  (tests/fixtures/ooni_weekly_golden/finance_bill_2024.json) already used.
  (2) tor drops out of both series with no explicit filter needed: it is
  always ooni_verdict IS NULL (NOT_IMPLEMENTED, per int.ooni_measurement_
  verdicts_candidate's header) and has zero live rows in int.ooni_
  experiment_results (structural -- see the Phase 0 fixture's own note).
  (3) A live re-derivation of Signal's ANOMALOUS rate over the FULL
  scored-only denominator (ooni_verdict IS NOT NULL) gives 17.9%
  (7,601/42,376), not the 15.1% figure (7,601/50,454, denominator
  including the 8,078 DISCARDED_BAD_PROBE_VERSION rows) carried into this
  session's own briefing -- the briefing's number was itself computed over
  the wrong denominator. This asset's anomalous_total_scored deliberately
  excludes NULL/NOT_IMPLEMENTED/DISCARDED rows, per this build's own Task
  B spec, so it reproduces 17.9%, not 15.1%.

  BASELINE METHODOLOGY: reuses features.protocol_daily_signals' pattern
  (unweighted trailing mean/stddev, sparse-data gating, effective-stddev
  floor) but NOT its literal window-size constant. Window size (12
  preceding weeks) is taken from features.acled_pressure_signals' own
  weekly-grain baseline (protest_baseline_12w / violence_baseline_12w /
  suppression_baseline_12w, w12 window) instead of reinterpreting
  protocol_daily_signals' "30" as 30 preceding weeks -- 30 weekly periods
  would span ~7 months, a materially different lookback character than
  protocol_daily_signals' ~1-month daily window, whereas 12 weeks (~1
  quarter) is this pipeline's own established weekly-grain precedent.
  min_baseline_weeks_12w = 7 keeps protocol_daily_signals' sample-count
  gate (a dimensionless "how many prior values before trusting mean/
  stddev" bar that transfers regardless of grain) rather than acled_
  pressure_signals' min_active_baseline_weeks = 4, because that 4
  specifically gates weeks with NONZERO activity (a sparse-activity
  concept), which does not apply here -- OONI's weekly volume in this
  window is never legitimately zero (min observed: 35 scored signal
  measurements in a week, out of 110 weeks total). min_measurements_
  per_week = 5 is also kept from protocol_daily_signals for the same
  dimensionless reason, but is expected to never fire live at this grain
  (no ASN partition here, so weekly volumes are always in the hundreds to
  hundreds of thousands) -- kept for structural consistency with the
  house pattern, not because it is expected to bind.

  SAMPLE QUALITY: a coverage-only score (volume relative to a fixed
  target, LEAST-capped at 1.0), not a full replica of protocol_daily_
  signals' 3-term sample_quality_score -- that formula's third term
  (1 - unknown_rate) has no analogue for the anomalous_* series (OONI's
  OK/CONFIRMED/ANOMALOUS/FAILED vocabulary has no UNKNOWN state), so
  applying it only to blocked_* would make the two series' quality scores
  inconsistent in what they measure. Both series use coverage only.
  Targets (200 scored measurements/week, 500 observations/week) are set
  well below the observed medians (342-8,774 and correspondingly higher)
  so the score saturates at 1.0 for the large majority of real weeks and
  only discounts genuinely thin ones (e.g. signal's 35-measurement week).

depends:
  - int.ooni_measurement_verdicts
  - int.ooni_experiment_results

materialization:
  type: table
  strategy: create+replace

columns:
  - name: week_start_date
    type: date
    checks:
      - name: not_null
  - name: test_name
    type: string
    checks:
      - name: not_null
  - name: country
    type: string
    checks:
      - name: not_null
@bruin */

WITH thresholds AS (
  SELECT
    12 AS baseline_window_weeks,
    7 AS min_baseline_weeks,
    5 AS min_measurements_per_week,
    0.0005 AS baseline_stddev_floor,
    200.0 AS target_scored_measurements_per_week,
    500.0 AS target_observations_per_week
),

anomalous_weekly AS (
  SELECT
    DATE_TRUNC(measurement_date, WEEK(SATURDAY)) AS week_start_date,
    test_name,
    COUNT(*) AS anomalous_total_scored,
    COUNTIF(ooni_verdict = 'ANOMALOUS') AS anomalous_count
  FROM `{{ var.project_id }}.int.ooni_measurement_verdicts`
  WHERE country = '{{ var.iso2 }}'
    -- Excludes NULL (NOT_IMPLEMENTED tor + DISCARDED_BAD_PROBE_VERSION
    -- signal rows) -- see header for the 17.9% vs 15.1% denominator note.
    AND ooni_verdict IS NOT NULL
  GROUP BY week_start_date, test_name
),

blocked_weekly AS (
  SELECT
    DATE_TRUNC(measurement_date, WEEK(SATURDAY)) AS week_start_date,
    test_name,
    COUNT(*) AS blocked_total_observations,
    COUNTIF(result_state = 'BLOCKED') AS blocked_count
  FROM `{{ var.project_id }}.int.ooni_experiment_results`
  WHERE country = '{{ var.iso2 }}'
  GROUP BY week_start_date, test_name
),

-- FULL OUTER JOIN: a (week, test_name) missing from one series is a real,
-- honest NULL below (no data that week for that series), not a fabricated
-- zero -- matching this project's established regime_* passthrough
-- discipline (fact_country_pressure_daily.sql).
combined AS (
  SELECT
    COALESCE(a.week_start_date, b.week_start_date) AS week_start_date,
    COALESCE(a.test_name, b.test_name) AS test_name,
    a.anomalous_total_scored,
    a.anomalous_count,
    SAFE_DIVIDE(a.anomalous_count, a.anomalous_total_scored) AS anomalous_rate,
    b.blocked_total_observations,
    b.blocked_count,
    SAFE_DIVIDE(b.blocked_count, b.blocked_total_observations) AS blocked_rate
  FROM anomalous_weekly AS a
  FULL OUTER JOIN blocked_weekly AS b
    USING (week_start_date, test_name)
),

with_baselines AS (
  SELECT
    c.*,
    AVG(anomalous_rate) OVER anomalous_12w AS anomalous_baseline_rate_12w,
    STDDEV_SAMP(anomalous_rate) OVER anomalous_12w AS anomalous_baseline_stddev_12w,
    COUNT(anomalous_rate) OVER anomalous_12w AS anomalous_baseline_weeks_12w,
    AVG(blocked_rate) OVER blocked_12w AS blocked_baseline_rate_12w,
    STDDEV_SAMP(blocked_rate) OVER blocked_12w AS blocked_baseline_stddev_12w,
    COUNT(blocked_rate) OVER blocked_12w AS blocked_baseline_weeks_12w
  FROM combined AS c
  WINDOW
    anomalous_12w AS (
      PARTITION BY test_name
      ORDER BY UNIX_DATE(week_start_date)
      ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING
    ),
    blocked_12w AS (
      PARTITION BY test_name
      ORDER BY UNIX_DATE(week_start_date)
      ROWS BETWEEN 12 PRECEDING AND 1 PRECEDING
    )
),

with_effective_variance AS (
  SELECT
    b.*,
    GREATEST(COALESCE(NULLIF(b.anomalous_baseline_stddev_12w, 0), 0), t.baseline_stddev_floor)
      AS anomalous_baseline_stddev_effective,
    GREATEST(COALESCE(NULLIF(b.blocked_baseline_stddev_12w, 0), 0), t.baseline_stddev_floor)
      AS blocked_baseline_stddev_effective
  FROM with_baselines AS b
  CROSS JOIN thresholds AS t
)

SELECT
  TO_HEX(MD5(CONCAT(CAST(week_start_date AS STRING), '|', test_name))) AS feature_id,
  week_start_date,
  '{{ var.iso2 }}' AS country,
  test_name,
  'week_start_date_test_name' AS feature_grain,

  anomalous_total_scored,
  anomalous_count,
  anomalous_rate,
  anomalous_baseline_rate_12w,
  anomalous_baseline_stddev_12w,
  anomalous_baseline_weeks_12w,
  anomalous_baseline_stddev_effective,
  SAFE_DIVIDE(anomalous_rate - anomalous_baseline_rate_12w, anomalous_baseline_stddev_effective)
    AS anomalous_zscore_12w,
  LEAST(1.0, SAFE_DIVIDE(anomalous_total_scored, target_scored_measurements_per_week))
    AS anomalous_sample_quality_score,
  COALESCE(anomalous_baseline_weeks_12w, 0) < min_baseline_weeks AS anomalous_sparse_baseline_flag,
  COALESCE(anomalous_total_scored, 0) < min_measurements_per_week AS anomalous_low_sample_flag,

  blocked_total_observations,
  blocked_count,
  blocked_rate,
  blocked_baseline_rate_12w,
  blocked_baseline_stddev_12w,
  blocked_baseline_weeks_12w,
  blocked_baseline_stddev_effective,
  SAFE_DIVIDE(blocked_rate - blocked_baseline_rate_12w, blocked_baseline_stddev_effective)
    AS blocked_zscore_12w,
  LEAST(1.0, SAFE_DIVIDE(blocked_total_observations, target_observations_per_week))
    AS blocked_sample_quality_score,
  COALESCE(blocked_baseline_weeks_12w, 0) < min_baseline_weeks AS blocked_sparse_baseline_flag,
  COALESCE(blocked_total_observations, 0) < min_measurements_per_week AS blocked_low_sample_flag,

  TO_JSON_STRING(STRUCT(
    baseline_window_weeks,
    min_baseline_weeks,
    min_measurements_per_week,
    baseline_stddev_floor,
    target_scored_measurements_per_week,
    target_observations_per_week
  )) AS guardrail_config_json,
  'ooni_weekly_signals_v1' AS feature_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM with_effective_variance
CROSS JOIN thresholds;
