/* @bruin
name: int.ooni_zero_accuracy_measurements
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  ADR-0017 (2026-11-22). One row per OONI measurement that meets at least
  one ADOPTED rule in marts.dim_ooni_zero_accuracy_rules, i.e. one that
  OONI's own current scoring code gives zero accuracy. Measurements that
  meet no adopted rule have no row here.

  Read by both levels, so the two can no longer disagree:
  - int.ooni_measurement_verdicts_candidate sets probe_accuracy_gate =
    'DISCARDED_OONI_ZERO_ACCURACY' and ooni_verdict = NULL;
  - int.ooni_experiment_results flags every observation row of the
    measurement (ooni_zero_accuracy_rule_id), and the observation-counting
    assets leave those rows out.

  ooni_zero_accuracy_rule_id is the first matching rule in OONI's own code
  order (rule_order), i.e. the site that would actually set accuracy to 0
  in OONI's score function. ooni_zero_accuracy_rules_met lists every
  matching adopted rule, for traceability. Under the rules adopted today
  "first in code order" and "any condition true" select the same set of
  measurements: the earlier-returning sites that are not adopted (SIG-B1,
  SIG-B6) meet no row in CLIO's corpus (2026-11-22 sweep).

  Two kinds of rule (marts.dim_ooni_zero_accuracy_rules.rule_stage):
  - SCORE rules are evaluated here from stg.ooni_measurements'
    raw_measurement (needed for annotations.engine_version and
    test_keys.targets, neither of which any typed column carries). That
    scan is restricted to the test names that have adopted scorer rules,
    so the table's test_name clustering prunes it: ~246 MB billed per
    rebuild on 2026-11-22, against ~33 GB for the whole raw_measurement
    column. The first custom check below fails if an adopted scorer rule
    is ever added for a test name outside that restriction, rather than
    letting the new rule silently match nothing.
  - DATE rules (ADR-0018, GEN-F and GEN-O, test_name '*' = every test)
    are read from int.ooni_receive_time.date_rule_state, for all test
    names. A measurement whose state is UNDETERMINED meets neither and has
    no row here unless a scorer rule matches it.
  OONI applies the date flag after scoring, so the DATE rules carry
  rule_order 101/102 and come after every scorer rule in
  ooni_zero_accuracy_rule_id; ooni_zero_accuracy_rules_met lists both.

  Expected on 2026-11-22 (ADR-0017, before ADR-0018): signal 15,302
  (SIG-B2 1,146; SIG-B3 11,304; SIG-B4 2,700; SIG-B5 152 by first rule),
  tor 2 (TOR-1). ADR-0018 figures: see the TD entry for ADR-0018.

depends:
  - stg.ooni_measurements
  - marts.dim_ooni_zero_accuracy_rules
  - int.ooni_receive_time

materialization:
  type: table
  strategy: create+replace

custom_checks:
  - name: adopted_rules_within_scanned_test_names
    description: |
      The scorer scan below reads only test_name IN ('signal', 'tor'). An
      adopted SCORE rule for any other test would match nothing. Must stay
      0; if it fails, widen the scan's test_name list in the same change.
      Adopted DATE rules (ADR-0018) apply to every test and are exempt.
    query: |
      SELECT COUNT(*)
      FROM `{{ var.project_id }}.marts.dim_ooni_zero_accuracy_rules`
      WHERE adopted AND rule_stage = 'SCORE' AND test_name NOT IN ('signal', 'tor')
    value: 0
  - name: date_rules_cover_every_test
    description: |
      ADR-0018. Every DATE rule must carry test_name '*' and a
      date_rule_state, so it is matched for every test. Must stay 0.
    query: |
      SELECT COUNT(*)
      FROM `{{ var.project_id }}.marts.dim_ooni_zero_accuracy_rules`
      WHERE rule_stage = 'DATE'
        AND (test_name != '*' OR date_rule_state IS NULL)
    value: 0

columns:
  - name: measurement_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: ooni_zero_accuracy_rule_id
    type: string
    checks:
      - name: not_null
@bruin */

WITH rules AS (
  SELECT *
  FROM `{{ var.project_id }}.marts.dim_ooni_zero_accuracy_rules`
  WHERE adopted
),

-- Same defaults as OONI's code: g_or(msm, "test_version", "0.0.0") and
-- g_or(annot, "engine_version", "0.0.0"). measurement_start_time is the
-- typed column; it equals the raw "%Y-%m-%d %H:%M:%S" string on every
-- signal and tor row (checked 2026-11-22).
measurements AS (
  SELECT
    measurement_id,
    test_name,
    COALESCE(test_version, '0.0.0') AS test_version,
    measurement_start_time,
    COALESCE(JSON_VALUE(raw_measurement, '$.annotations.engine_version'), '0.0.0') AS engine_version,
    JSON_QUERY(raw_measurement, '$.test_keys.targets') AS targets_json
  FROM `{{ var.project_id }}.stg.ooni_measurements`
  WHERE test_name IN ('signal', 'tor')
),

-- A sortable key per version string (packaging.Version order for
-- N.N.N[-alpha|-beta[.N]]): major, minor, patch, then pre-release rank
-- (alpha 0, beta 1, release 9) and pre-release number. A string outside
-- that form gets a NULL key, so no version condition can match it.
version_strings AS (
  SELECT test_version AS v FROM measurements
  UNION DISTINCT
  SELECT engine_version FROM measurements
  UNION DISTINCT
  SELECT x
  FROM rules, UNNEST([test_version_max, test_version_below, engine_version_below]) AS x
  WHERE x IS NOT NULL
),

version_keys AS (
  SELECT
    v,
    IF(
      REGEXP_CONTAINS(v, r'^\d+\.\d+\.\d+(-(alpha|beta)(\.\d+)?)?$'),
      FORMAT(
        '%09d%09d%09d%d%09d',
        CAST(REGEXP_EXTRACT(v, r'^(\d+)\.') AS INT64),
        CAST(REGEXP_EXTRACT(v, r'^\d+\.(\d+)\.') AS INT64),
        CAST(REGEXP_EXTRACT(v, r'^\d+\.\d+\.(\d+)') AS INT64),
        CASE REGEXP_EXTRACT(v, r'-(alpha|beta)') WHEN 'alpha' THEN 0 WHEN 'beta' THEN 1 ELSE 9 END,
        COALESCE(CAST(REGEXP_EXTRACT(v, r'-(?:alpha|beta)\.(\d+)$') AS INT64), 0)
      ),
      NULL
    ) AS k
  FROM version_strings
),

measurements_keyed AS (
  SELECT
    m.*,
    tv.k AS test_version_key,
    ev.k AS engine_version_key,
    -- OONI: targets = tk.get("targets", {}); if not targets. Missing,
    -- JSON null, or an empty/falsy value all count as "no targets".
    (m.targets_json IS NULL
      OR m.targets_json IN ('null', '{}', '[]', '""', 'false', '0')) AS targets_empty
  FROM measurements AS m
  LEFT JOIN version_keys AS tv ON tv.v = m.test_version
  LEFT JOIN version_keys AS ev ON ev.v = m.engine_version
),

rules_keyed AS (
  SELECT
    r.*,
    mx.k AS test_version_max_key,
    bl.k AS test_version_below_key,
    eb.k AS engine_version_below_key
  FROM rules AS r
  LEFT JOIN version_keys AS mx ON mx.v = r.test_version_max
  LEFT JOIN version_keys AS bl ON bl.v = r.test_version_below
  LEFT JOIN version_keys AS eb ON eb.v = r.engine_version_below
),

matches AS (
  SELECT
    m.measurement_id,
    m.test_name,
    m.test_version,
    r.rule_id,
    r.rule_order,
    r.rules_version,
    r.ooni_commit
  FROM measurements_keyed AS m
  JOIN rules_keyed AS r
    ON r.test_name = m.test_name
    AND r.rule_stage = 'SCORE'
  WHERE (r.test_version_equals IS NULL OR m.test_version = r.test_version_equals)
    AND (r.test_version_max IS NULL OR m.test_version_key <= r.test_version_max_key)
    AND (r.test_version_below IS NULL OR m.test_version_key < r.test_version_below_key)
    AND (r.start_time_from IS NULL OR m.measurement_start_time >= r.start_time_from)
    AND (r.engine_version_below IS NULL OR m.engine_version_key < r.engine_version_below_key)
    AND (NOT r.requires_no_targets OR m.targets_empty)

  UNION ALL

  -- ADR-0018: OONI's date-consistency rules, every test. The state is
  -- decided in int.ooni_receive_time (archive hour, or measurement_uid
  -- where the hour cannot decide). UNDETERMINED matches no rule.
  SELECT
    rt.measurement_id,
    rt.test_name,
    COALESCE(rt.test_version, '0.0.0') AS test_version,
    r.rule_id,
    r.rule_order,
    r.rules_version,
    r.ooni_commit
  FROM `{{ var.project_id }}.int.ooni_receive_time` AS rt
  JOIN rules AS r
    ON r.rule_stage = 'DATE'
    AND r.test_name = '*'
    AND r.date_rule_state = rt.date_rule_state
)

SELECT
  measurement_id,
  test_name,
  test_version,
  ARRAY_AGG(rule_id ORDER BY rule_order LIMIT 1)[OFFSET(0)] AS ooni_zero_accuracy_rule_id,
  STRING_AGG(rule_id, ',' ORDER BY rule_order) AS ooni_zero_accuracy_rules_met,
  ANY_VALUE(rules_version) AS rules_version,
  ANY_VALUE(ooni_commit) AS ooni_commit,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM matches
GROUP BY measurement_id, test_name, test_version
