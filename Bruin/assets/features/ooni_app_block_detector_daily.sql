/* @bruin
name: features.ooni_app_block_detector_daily
type: bq.sql
connection: bigquery-default

tags:
  - features_bq
  - dataset_ooni
  - app_block_detector

description: |
  Daily app-block detector (ADR-0016). One row per measurement_date x
  test_name for telegram, whatsapp and signal, from CLIO's own verdicts
  (int.ooni_measurement_verdicts, scored rows only: ooni_verdict IS NOT
  NULL). No OONI labels, findings or reports are used.

  RULE (detector v1.0, fixed in advance; change it only by a new ADR):
  rate r = ANOMALOUS / scored. Baseline = median r over days d-35 to d-8
  with >= 20 scored measurements (the 7-day gap keeps a block's first week
  out of its own baseline). A day is flagged when n_scored >= 20, at
  least 14 baseline days, z >= 4 with z = (r - base) / sqrt(p(1-p)/n) and
  p = max(base, 0.02), and r - base >= 0.10.

  app_specific_flag: flagged, and neither of the other two apps is flagged
  on the same day, the day before or the day after. This separates an
  app-level block from a general connectivity failure, in which all apps
  move together; it only partly separates them (a connectivity failure
  can still hit one app's measurements first).

  r_anomalous_or_failed is reported alongside and is not used by the rule.

  LIMITS: built for multi-day blocks of an app; a one-day or partial block
  may not cross the thresholds. A flag is a candidate event, not a
  confirmed block, and never a statement about cause.

depends:
  - int.ooni_measurement_verdicts

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_date
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

WITH daily AS (
  SELECT
    measurement_date AS d,
    test_name,
    COUNT(*) AS n_scored,
    COUNTIF(ooni_verdict = 'ANOMALOUS') AS n_anomalous,
    COUNTIF(ooni_verdict IN ('ANOMALOUS', 'FAILED')) AS n_anomalous_or_failed
  FROM `{{ var.project_id }}.int.ooni_measurement_verdicts`
  WHERE country = '{{ var.iso2 }}'
    AND test_name IN ('telegram', 'whatsapp', 'signal')
    AND ooni_verdict IS NOT NULL
  GROUP BY d, test_name
),

rates AS (
  SELECT
    *,
    SAFE_DIVIDE(n_anomalous, n_scored) AS r,
    SAFE_DIVIDE(n_anomalous_or_failed, n_scored) AS r_notok
  FROM daily
),

base AS (
  SELECT
    a.d,
    a.test_name,
    APPROX_QUANTILES(b.r, 2)[OFFSET(1)] AS base_r,
    COUNT(*) AS base_days
  FROM rates AS a
  JOIN rates AS b
    ON b.test_name = a.test_name
   AND b.d BETWEEN DATE_SUB(a.d, INTERVAL 35 DAY) AND DATE_SUB(a.d, INTERVAL 8 DAY)
   AND b.n_scored >= 20
  GROUP BY a.d, a.test_name
),

det AS (
  SELECT
    r.d, r.test_name, r.n_scored, r.n_anomalous, r.n_anomalous_or_failed,
    r.r, r.r_notok, b.base_r, b.base_days,
    SAFE_DIVIDE(
      r.r - b.base_r,
      SQRT(GREATEST(b.base_r, 0.02) * (1 - GREATEST(b.base_r, 0.02)) / r.n_scored)
    ) AS z,
    (r.n_scored >= 20 AND b.base_days >= 14
     AND SAFE_DIVIDE(
           r.r - b.base_r,
           SQRT(GREATEST(b.base_r, 0.02) * (1 - GREATEST(b.base_r, 0.02)) / r.n_scored)
         ) >= 4
     AND r.r - b.base_r >= 0.10) AS flag
  FROM rates AS r
  JOIN base AS b USING (d, test_name)
),

near AS (
  SELECT nd, ARRAY_AGG(DISTINCT test_name) AS flagged_tests
  FROM det,
  UNNEST(GENERATE_DATE_ARRAY(DATE_SUB(det.d, INTERVAL 1 DAY),
                             DATE_ADD(det.d, INTERVAL 1 DAY))) AS nd
  WHERE det.flag
  GROUP BY nd
)

SELECT
  det.d AS measurement_date,
  '{{ var.iso2 }}' AS country,
  det.test_name,
  det.n_scored,
  det.n_anomalous,
  det.n_anomalous_or_failed,
  ROUND(det.r, 4) AS r_anomalous,
  ROUND(det.r_notok, 4) AS r_anomalous_or_failed,
  ROUND(det.base_r, 4) AS baseline_r,
  det.base_days AS baseline_days,
  ROUND(det.z, 2) AS z,
  IFNULL(det.flag, FALSE) AS flag,
  (IFNULL(det.flag, FALSE)
   AND (SELECT COUNTIF(t != det.test_name)
        FROM UNNEST(IFNULL(n.flagged_tests, ARRAY<STRING>[])) AS t) = 0) AS app_specific_flag,
  'v1.0' AS detector_version
FROM det
LEFT JOIN near AS n ON n.nd = det.d
