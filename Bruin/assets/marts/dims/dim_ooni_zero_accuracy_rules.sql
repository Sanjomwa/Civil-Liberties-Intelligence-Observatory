/* @bruin
tags:
  - marts_bq
  - canonical_dimensions
  - ooni_verdict_phase_2

name: marts.dim_ooni_zero_accuracy_rules
type: bq.sql
connection: bigquery-default

description: |
  ADR-0017 (2026-11-22). The rules table that decides which OONI
  measurements CLIO sets aside because OONI's own current scoring code
  gives them zero accuracy. One row per rule. It drives both levels:
  int.ooni_zero_accuracy_measurements evaluates the adopted rows against
  each measurement, and both int.ooni_measurement_verdicts_candidate
  (measurement level) and int.ooni_experiment_results (observation level)
  read that result.

  Reference: ooni/backend, fastpath/fastpath/core.py, pinned at commit
  27f2b28cd021c51a42ac6418fba44335d5de4ca8. Every condition below is
  copied from that file at the line given in ooni_file_line; it is not
  reconstructed from OONI's stored per-measurement scores, which are used
  only as a check (ADR-0017, Decision 1). When OONI changes its scoring
  code, review the new commit and publish a new rules_version; do not edit
  a condition in place under the old version string.

  How a row is evaluated (all non-NULL conditions must hold):
  - test_version_equals: test_version equals this string exactly.
  - test_version_max: test_version <= this version (inclusive).
  - test_version_below: test_version < this version (exclusive). Kept
    separate from test_version_max because OONI writes both forms
    (`<= 0.2.3`, `< 0.2.2`) and the two are not interchangeable once
    pre-release suffixes exist.
  - start_time_from: measurement_start_time >= this instant (UTC; OONI
    compares a naive datetime parsed from the same string).
  - engine_version_below: annotations.engine_version < this version.
  - requires_no_targets: test_keys.targets is missing or empty.
  Version comparison follows packaging.Version for the forms present in
  CLIO (N.N.N with an optional -alpha / -beta[.N] suffix, pre-releases
  ordered before the release). As in OONI's code, a missing test_version
  or engine_version counts as "0.0.0".

  adopted = FALSE rows are recorded, not applied. GEN-U (OONI's
  unsupported-test branch) gives every dnscheck measurement zero accuracy
  only because OONI has no dnscheck scorer; CLIO does not treat that as a
  data-quality judgement (ADR-0017, Decision 4).

  Not in this table, and why (from the 2026-11-22 read-only sweep):
  - Other zero-accuracy sites in score_signal / score_tor (SIG-A, SIG-B1,
    SIG-B6, SIG-B7, TOR-2..TOR-4) meet no row in CLIO's corpus today. They
    are not adopted; a future row meeting one of them is not excluded by
    this table.
  - OONI's two date-consistency checks (flag_measurements_with_wrong_date)
    need measurement_uid, which CLIO does not store. Recorded as a limit.
  - CLIO's own 15 Signal discards with no matching OONI rule (0.2.2: 9,
    0.2.3: 6) stay in int.ooni_measurement_verdicts_candidate's
    probe_accuracy_gate CASE as DISCARDED_BAD_PROBE_VERSION.

  This table supersedes marts.dim_ooni_probe_version_accuracy as the
  statement of which versions OONI discards. That table is kept only to
  tell SCORED from UNKNOWN_VERSION.

materialization:
  type: table
  strategy: create+replace

columns:
  - name: rule_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: test_name
    type: string
    checks:
      - name: not_null
  - name: adopted
    type: boolean
    checks:
      - name: not_null
@bruin */

SELECT * FROM UNNEST([
  STRUCT(
    '2026-11-22.1' AS rules_version,
    'TOR-1' AS rule_id,
    1 AS rule_order,
    'tor' AS test_name,
    CAST(NULL AS STRING) AS test_version_equals,
    CAST(NULL AS STRING) AS test_version_max,
    CAST(NULL AS STRING) AS test_version_below,
    CAST(NULL AS TIMESTAMP) AS start_time_from,
    CAST(NULL AS STRING) AS engine_version_below,
    TRUE AS requires_no_targets,
    'ooni/backend' AS ooni_repo,
    '27f2b28cd021c51a42ac6418fba44335d5de4ca8' AS ooni_commit,
    'fastpath/fastpath/core.py:1273-1276 (score_tor)' AS ooni_file_line,
    CAST(NULL AS STRING) AS issue_url,
    TRUE AS adopted,
    'targets = tk.get("targets", {}); if not targets: accuracy 0.0. No issue linked in the code (logbug "missing Tor targets"). 2 measurements in CLIO; tor has no observation rows.' AS note
  ),
  STRUCT(
    '2026-11-22.1', 'SIG-B2', 1, 'signal',
    '0.2.4', NULL, NULL, NULL, NULL, FALSE,
    'ooni/backend', '27f2b28cd021c51a42ac6418fba44335d5de4ca8',
    'fastpath/fastpath/core.py:1395-1399 (score_signal)',
    'https://github.com/ooni/probe/issues/2636', TRUE,
    'if tv == "0.2.4": accuracy 0.0 ("the breakage here is affecting just v0.2.4 of the test"; also cites ooni/probe-cli#1421). 1,146 measurements in CLIO.'
  ),
  STRUCT(
    '2026-11-22.1', 'SIG-B3', 2, 'signal',
    NULL, '0.2.3', NULL, TIMESTAMP('2023-11-07 00:00:00'), NULL, FALSE,
    'ooni/backend', '27f2b28cd021c51a42ac6418fba44335d5de4ca8',
    'fastpath/fastpath/core.py:1402-1406 (score_signal)',
    'https://github.com/ooni/probe/issues/2627', TRUE,
    'Version(tv) <= Version("0.2.3") and start_time >= datetime(2023, 11, 7): accuracy 0.0.'
  ),
  STRUCT(
    '2026-11-22.1', 'SIG-B4', 3, 'signal',
    NULL, NULL, '0.2.2', TIMESTAMP('2022-10-19 00:00:00'), NULL, FALSE,
    'ooni/backend', '27f2b28cd021c51a42ac6418fba44335d5de4ca8',
    'fastpath/fastpath/core.py:1409-1412 (score_signal)',
    'https://github.com/ooni/probe/issues/2344', TRUE,
    'Version(tv) < Version("0.2.2") and start_time >= datetime(2022, 10, 19): accuracy 0.0. The rule itself carries no issue link; ooni/probe#2344 is cited at line 1386 for the enclosing block. Same rule as the 0.2.0 row of marts.dim_ooni_probe_version_accuracy.'
  ),
  STRUCT(
    '2026-11-22.1', 'SIG-B5', 4, 'signal',
    NULL, NULL, NULL, TIMESTAMP('2023-05-02 00:00:00'), '3.17.2', FALSE,
    'ooni/backend', '27f2b28cd021c51a42ac6418fba44335d5de4ca8',
    'fastpath/fastpath/core.py:1415-1422 (score_signal)',
    'https://github.com/ooni/backend/issues/679', TRUE,
    'ev = g_or(annot, "engine_version", "0.0.0"); Version(ev) < Version("3.17.2") and start_time >= datetime(2023, 5, 2): accuracy 0.0.'
  ),
  STRUCT(
    '2026-11-22.1', 'GEN-U', 1, 'dnscheck',
    NULL, NULL, NULL, NULL, NULL, FALSE,
    'ooni/backend', '27f2b28cd021c51a42ac6418fba44335d5de4ca8',
    'fastpath/fastpath/core.py:1576-1578 (score_measurement, unsupported test name)',
    NULL, FALSE,
    'OONI has no dnscheck scorer; not a quality judgement'
  )
])
