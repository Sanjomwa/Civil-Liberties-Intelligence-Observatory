/* @bruin
name: intelligence.ooni_acled_lag_correlation
type: bq.sql
connection: bigquery-default

tags:
  - intelligence_bq
  - dataset_ooni
  - ooni_weekly_aggregation

description: |
  Lag-tested correlation between each of features.ooni_weekly_signals' two
  independent weekly OONI series and intelligence.acled_pressure_regimes'
  weekly regime classification, at lags of 0, +-1, +-2 weeks.

  Grain: week_start_date x test_name x series_type x lag_weeks. series_type
  is 'ANOMALOUS' or 'BLOCKED' -- the two series are computed independently
  within their own partition (PARTITION BY series_type, test_name, lag_weeks
  throughout) and never combined into one correlation number. This mirrors
  features.ooni_weekly_signals' own non-merge discipline one layer
  downstream, per this project's Extension A methodology principle and
  ADR-0009's non-merge precedent.

  LAG SIGN CONVENTION (read this before interpreting lag_weeks): a positive
  lag_weeks means the ACLED week used is EARLIER than the OONI week --
  acled_week_start_date = week_start_date - lag_weeks * 7 days. So:
    lag_weeks = 0   : same week.
    lag_weeks = +1/+2 : ACLED pressure LEADS OONI by 1/2 weeks (does last
                        week's conflict pressure predict this week's OONI
                        signal?).
    lag_weeks = -1/-2 : OONI LEADS ACLED by 1/2 weeks (does this week's
                        OONI signal predict next week's conflict pressure?).

  ACLED NUMERIC PROXY: intelligence.acled_pressure_regimes.primary_regime
  is categorical (STABLE/MOBILISATION/CONTESTATION/ESCALATION/CRISIS/
  REPRESSION/CONFLICT), not a continuous score -- CORR() needs a number.
  Reuses that asset's OWN frozen severity-hierarchy ordinal mapping
  (CRISIS=7, ESCALATION=6, CONTESTATION=5, REPRESSION=4, CONFLICT=3,
  MOBILISATION=2, STABLE=1 -- see acled_pressure_regimes.sql's CTE-11/
  CTE-16 comment, "hierarchy ordinal mapping... is unchanged and frozen")
  rather than inventing a new severity scale. Pearson CORR() on an
  equal-interval encoding of an ordinal category is a deliberate
  approximation -- the same kind of approximation this pipeline already
  makes elsewhere (e.g. confidence-level bucketing), not a new one
  introduced here.

  DAMPING: reuses reporting.protocol_repression_correlation_mart's rolling-
  correlation pattern (quality/confidence-damped CORR(), window_obs >= 18
  guardrail, 0.55/0.82 MODERATE/STRONG thresholds, ROWS BETWEEN 30
  PRECEDING correlation window -- a period-count window, so it transfers
  unchanged from daily to weekly grain, unlike features.ooni_weekly_
  signals' baseline window above). ONE deliberate deviation: that mart
  damps by `sample_quality_score * COALESCE(final_confidence_score, 0.25)`
  -- a per-week confidence score sourced from intelligence.protocol_
  relationships. No equivalent per-week confidence layer exists yet for
  either OONI weekly series (building one is out of this build's scope),
  so damping here uses sample_quality_score alone. If a future confidence
  layer for these series is built, this should be revisited.

  HONESTY NOTE (read before trusting any single coefficient here): Kenya's
  ACLED regime history is overwhelmingly STABLE (1,341 of 1,523 weeks,
  all-time), and the OONI overlap window (2023-06-01 to 2025-06-30, 110
  weeks) is no exception -- most 30-week rolling windows will see near-zero
  hierarchy variance and correctly resolve to NULL / ZERO_VARIANCE_WINDOW.
  Any nonzero correlation this asset produces is therefore driven by a
  small number of non-STABLE weeks (effectively the Finance Bill 2024
  cluster and whatever else falls in-window) -- report the effective
  non-STABLE week count alongside any coefficient, not the coefficient
  alone.

depends:
  - features.ooni_weekly_signals
  - intelligence.acled_pressure_regimes

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
  - name: series_type
    type: string
    checks:
      - name: not_null
      - name: accepted_values
        value: [ANOMALOUS, BLOCKED]
  - name: lag_weeks
    type: int64
    checks:
      - name: not_null
      - name: accepted_values
        value: [-2, -1, 0, 1, 2]
@bruin */

WITH lag_config AS (
  SELECT -2 AS lag_weeks UNION ALL
  SELECT -1 UNION ALL
  SELECT 0 UNION ALL
  SELECT 1 UNION ALL
  SELECT 2
),

guardrails AS (
  SELECT
    18 AS min_window_obs,
    30 AS correlation_window_weeks,
    0.55 AS moderate_correlation_threshold,
    0.82 AS strong_correlation_threshold
),

acled AS (
  SELECT
    week_start_date,
    primary_regime,
    CASE primary_regime
      WHEN 'CRISIS' THEN 7
      WHEN 'ESCALATION' THEN 6
      WHEN 'CONTESTATION' THEN 5
      WHEN 'REPRESSION' THEN 4
      WHEN 'CONFLICT' THEN 3
      WHEN 'MOBILISATION' THEN 2
      WHEN 'STABLE' THEN 1
    END AS acled_hierarchy
  FROM `{{ var.project_id }}.intelligence.acled_pressure_regimes`
  WHERE iso2 = '{{ var.iso2 }}'
),

-- Unpivot the two independent series into one long (series_type)-keyed
-- shape. This is a row-labeling operation, not a merge -- ooni_rate and
-- sample_quality_score always come from exactly one series' own columns.
ooni_long AS (
  SELECT week_start_date, test_name, 'ANOMALOUS' AS series_type,
    anomalous_rate AS ooni_rate, anomalous_sample_quality_score AS sample_quality_score
  FROM `{{ var.project_id }}.features.ooni_weekly_signals`
  WHERE anomalous_rate IS NOT NULL
  UNION ALL
  SELECT week_start_date, test_name, 'BLOCKED' AS series_type,
    blocked_rate AS ooni_rate, blocked_sample_quality_score AS sample_quality_score
  FROM `{{ var.project_id }}.features.ooni_weekly_signals`
  WHERE blocked_rate IS NOT NULL
),

paired AS (
  SELECT
    o.week_start_date,
    o.test_name,
    o.series_type,
    lag_config.lag_weeks,
    DATE_SUB(o.week_start_date, INTERVAL lag_config.lag_weeks * 7 DAY) AS acled_week_start_date,
    o.ooni_rate,
    o.sample_quality_score,
    a.primary_regime AS acled_primary_regime,
    a.acled_hierarchy
  FROM ooni_long AS o
  CROSS JOIN lag_config
  INNER JOIN acled AS a
    ON a.week_start_date = DATE_SUB(o.week_start_date, INTERVAL lag_config.lag_weeks * 7 DAY)
),

normalized AS (
  SELECT
    *,
    SAFE_DIVIDE(
      ooni_rate - AVG(ooni_rate) OVER (PARTITION BY series_type, test_name, lag_weeks),
      NULLIF(STDDEV_SAMP(ooni_rate) OVER (PARTITION BY series_type, test_name, lag_weeks), 0)
    ) AS raw_z_ooni,
    SAFE_DIVIDE(
      acled_hierarchy - AVG(acled_hierarchy) OVER (PARTITION BY series_type, test_name, lag_weeks),
      NULLIF(STDDEV_SAMP(acled_hierarchy) OVER (PARTITION BY series_type, test_name, lag_weeks), 0)
    ) AS z_acled
  FROM paired
),

quality_adjusted AS (
  SELECT
    *,
    raw_z_ooni * COALESCE(sample_quality_score, 0.0) AS z_ooni
  FROM normalized
),

correlated AS (
  SELECT
    q.*,
    g.min_window_obs,
    g.moderate_correlation_threshold,
    g.strong_correlation_threshold,
    COUNT(*) OVER win AS window_obs,
    STDDEV_SAMP(z_ooni) OVER win AS ooni_window_stddev,
    STDDEV_SAMP(z_acled) OVER win AS acled_window_stddev,
    CORR(z_ooni, z_acled) OVER win AS raw_corr
  FROM quality_adjusted AS q
  CROSS JOIN guardrails AS g
  WINDOW win AS (
    PARTITION BY series_type, test_name, lag_weeks
    ORDER BY UNIX_DATE(week_start_date)
    ROWS BETWEEN 30 PRECEDING AND CURRENT ROW
  )
),

guarded AS (
  SELECT
    *,
    window_obs < min_window_obs AS insufficient_history_flag,
    (COALESCE(ooni_window_stddev, 0) = 0 OR COALESCE(acled_window_stddev, 0) = 0)
      AS zero_variance_flag,
    CASE
      WHEN window_obs < min_window_obs THEN NULL
      WHEN COALESCE(ooni_window_stddev, 0) = 0 THEN NULL
      WHEN COALESCE(acled_window_stddev, 0) = 0 THEN NULL
      ELSE raw_corr * COALESCE(sample_quality_score, 0.0)
    END AS rolling_pressure_corr
  FROM correlated
)

SELECT
  week_start_date,
  test_name,
  series_type,
  lag_weeks,
  acled_week_start_date,
  ooni_rate,
  sample_quality_score,
  acled_primary_regime,
  acled_hierarchy,
  raw_z_ooni,
  z_ooni,
  z_acled,
  window_obs,
  raw_corr,
  rolling_pressure_corr,
  CASE
    WHEN insufficient_history_flag THEN 'INSUFFICIENT_HISTORY'
    WHEN zero_variance_flag THEN 'ZERO_VARIANCE_WINDOW'
    WHEN ABS(rolling_pressure_corr) >= strong_correlation_threshold THEN 'STRONG_RELATIONSHIP'
    WHEN ABS(rolling_pressure_corr) >= moderate_correlation_threshold THEN 'MODERATE_RELATIONSHIP'
    ELSE 'WEAK_OR_NO_RELATIONSHIP'
  END AS correlation_state,
  insufficient_history_flag,
  zero_variance_flag,
  'ooni_acled_lag_correlation_v1' AS intelligence_version,
  CURRENT_TIMESTAMP() AS computed_at
FROM guarded
ORDER BY series_type, test_name, lag_weeks, week_start_date;
