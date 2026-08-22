"""
Regression lock for TD-102's build: three SEPARATE fixes for signal
measurements CLIO classifies ANOMALOUS when OONI's own live classification
disagrees, for three genuinely different, independently-confirmed reasons.
Do not conflate them -- they have separate mechanisms, separate evidence,
and separate implementation shapes, even though all three resolve to the
same outcome (discard via DISCARDED_BAD_PROBE_VERSION -> NULL).

test_version=0.2.0 -- pre-existing, unrelated, genuinely version-wide
(OONI's own published rule, OONI-confirmed to apply to the whole
version). Untouched by any TD-102 work; included here only as a
regression guard.

test_version=0.2.2 -- a real, but NARROWER than first thought,
dead-endpoint defect. RESCOPING HISTORY, load-bearing for this file's
assertions: a first TD-102 build session (2026-08-22) fixed this as a
version-wide discard (marts.dim_ooni_probe_version_accuracy's
signal/0.2.2 row flipped FALSE -> TRUE), reasoning that 0.2.2's dead
https://api.directory.signal.org/ backend target (removed in 0.2.3)
poisons the WHOLE measurement whenever tested, since Signal's client
code marks the whole measurement blocked if any tested target fails.
That session's OWN post-fix validation then found this premise did not
hold against the real population: only 415/2,200 (18.9%) of 0.2.2 rows
actually show signal_backend_status='blocked'; the other 1,785 (81.1%)
are genuine, OONI-agreed 'ok' rows that the version-wide rule was
incorrectly discarding. A second, RESCOPING build session (same day)
reverted dim_ooni_probe_version_accuracy's signal/0.2.2 row back to
FALSE and replaced it with an inline
`s.test_name = 'signal' AND s.test_version = '0.2.2' AND
s.signal_backend_status = 'blocked'` predicate in
probe_accuracy_gate's own CASE in
int.ooni_measurement_verdicts_candidate.sql -- the same location and
shape already established for 0.2.3's own predicate below. This file's
assertions reflect the RESCOPED (current, correct) state: 0.2.2's dim
table row is FALSE, and an inline blocked-only predicate exists.

test_version=0.2.3, measurement_start_time > '2023-11-06T16:00:00' -- a
one-time, date-gated OONI data-quality patch, UNCHANGED by the
rescoping session (do not touch; this fix was correct from the first
build). OONI's own devops team ran a one-time manual ClickHouse
mutation in November 2023 (citing ooni/probe#2627), retroactively
marking a batch of Signal measurements failed/unscoreable because
Signal decommissioned textsecure-service.whispersystems.org on
2023-11-07 and probe versions before 0.2.4 kept testing the dead host.
Genuinely date-gated: 0.2.3's entire pre-cutoff population (12 rows,
checked exhaustively) shows 0% disagreement with OONI's live
classification; a 76-row post-cutoff sample showed 100%. Fixed via an
inline predicate in probe_accuracy_gate's own CASE, not a
dim_ooni_probe_version_accuracy row -- that table has no date grain.

A REAL, EXPECTED, CORRECT INTERACTION WITH TD-93, NOT A REGRESSION
(unchanged by the rescoping -- only 0.2.2's own mechanism moved):
because probe_accuracy_gate is checked ahead of every FAILED condition
in the ooni_verdict CASE, a subset of 0.2.3's post-cutoff population
that TD-93's own legacy-endpoint-NXDOMAIN carve-out previously
classified FAILED now reclassifies FAILED -> NULL instead, because the
0.2.3 discard check intercepts it first. TD-93's own rule and its own
tests are completely unchanged. See
tests/fixtures/ooni_signal_probe_version_discard/pinned_measurements.json's
0.2.3 entries for live examples.

THIS TEST EXISTS TO STOP A FUTURE REFACTOR FROM SILENTLY MERGING THESE
THREE MECHANISMS, WIDENING 0.2.2 BACK TO VERSION-WIDE, OR
NARROWING/WIDENING 0.2.3's DATE GATE. If a future edit changes the
0.2.2 dimension-table entry's boolean back to TRUE, removes the 0.2.2
inline predicate, or changes the 0.2.3 inline predicate's
version/date condition, this file's static assertions must fail.

Two layers of protection, same pattern as
tests/test_ooni_whatsapp_endpoints_blocked_count_removed.py:

1. Static SQL-text assertions (always run, zero credentials).
2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1.
   signal has a valid, non-degenerate oracle (OONI's own
   /api/v1/measurements), used as ground truth throughout.

PINNED FIXTURE (tests/fixtures/ooni_signal_probe_version_discard/
pinned_measurements.json): 11 real measurement_ids -- 1 discarded via
the rescoped 0.2.2 blocked-only predicate, 2 correctly RESTORED to OK
under the rescoped predicate (previously, incorrectly, discarded under
the first build session's version-wide rule -- these are the entries
that most directly guard against the rescoping being silently
reverted), 2 discarded via the 0.2.3 date-gated fix (both demonstrating
the real TD-93 interaction above), 2 regression guards proving 0.2.3's
pre-cutoff population is untouched, 2 regression guards proving
0.2.4/0.2.5 are unaffected, and 1 guard proving the pre-existing 0.2.0
rule is undisturbed.
"""
import json
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
VERDICTS_CANDIDATE_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_measurement_verdicts_candidate.sql"
)
DIM_PROBE_VERSION_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "marts" / "dims" / "dim_ooni_probe_version_accuracy.sql"
)
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "ooni_signal_probe_version_discard"
    / "pinned_measurements.json"
)

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def _load_fixture():
    with open(FIXTURE_PATH) as f:
        return json.load(f)["entries"]


# ---------------------------------------------------------------------
# Static layer
# ---------------------------------------------------------------------

def test_signal_0_2_2_dim_table_row_is_false_not_version_wide():
    """RESCOPED (2026-08-22, second build session): 0.2.2's dim-table row
    must read FALSE. The version-wide discard (TRUE) was the first build
    session's over-broad fix, reverted once that session's own
    validation found it discarded ~1,785 genuine OONI-agreed OK rows.
    The correctly-scoped rule now lives as an inline predicate -- see
    test_signal_0_2_2_blocked_only_predicate_present below."""
    sql = _normalized(DIM_PROBE_VERSION_SQL)
    assert "STRUCT('signal', '0.2.2', FALSE," in sql, (
        "TD-102 regression: signal/0.2.2's entry in "
        "dim_ooni_probe_version_accuracy is not FALSE -- either the "
        "over-broad version-wide discard has been reinstated, or the "
        "row's shape has drifted unexpectedly."
    )
    assert "STRUCT('signal', '0.2.2', TRUE," not in sql, (
        "TD-102 regression: signal/0.2.2 is back to TRUE (version-wide "
        "discard) in dim_ooni_probe_version_accuracy -- this is the "
        "exact over-broad state the rescoping session fixed. If this is "
        "intentional, the 1,785-row OK-restoration finding needs to be "
        "re-litigated first, not silently reverted."
    )


def test_signal_0_2_2_blocked_only_predicate_present():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN s.test_name = 'signal' AND s.test_version = '0.2.2' "
        "AND s.signal_backend_status = 'blocked' "
        "THEN 'DISCARDED_BAD_PROBE_VERSION'"
        in sql
    ), (
        "TD-102 regression: the rescoped, blocked-only 0.2.2 discard "
        "predicate in probe_accuracy_gate's CASE (int.ooni_measurement_"
        "verdicts_candidate.sql) has drifted from the exact shape this "
        "fix shipped, or has been removed/widened."
    )


def test_signal_0_2_0_rule_unchanged():
    sql = _normalized(DIM_PROBE_VERSION_SQL)
    assert (
        "STRUCT('signal' AS test_name, '0.2.0' AS test_version, TRUE AS is_known_bad_version,"
        in sql
    ), (
        "TD-102 regression: signal/0.2.0's pre-existing, unrelated "
        "discard rule has changed -- this fix must not touch it."
    )


def test_signal_0_2_3_date_gated_predicate_present():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN s.test_name = 'signal' AND s.test_version = '0.2.3' "
        "AND s.measurement_start_time > TIMESTAMP('2023-11-06T16:00:00') "
        "THEN 'DISCARDED_BAD_PROBE_VERSION'"
        in sql
    ), (
        "TD-102 regression: the date-gated 0.2.3 discard predicate in "
        "probe_accuracy_gate's CASE (int.ooni_measurement_verdicts_"
        "candidate.sql) has drifted from the exact shape this fix "
        "shipped, or has been removed."
    )


def test_signal_predicates_ranked_ahead_of_dim_lookup_fallback():
    """Both inline predicates (0.2.3 date-gated, 0.2.2 blocked-only) must
    sit between the dim.is_known_bad_version IS TRUE branch and the
    dim.is_known_bad_version IS FALSE branch -- i.e. they participate in
    the SAME probe_accuracy_gate CASE, at the SAME precedence tier as
    DISCARDED_BAD_PROBE_VERSION, not bolted onto the outer ooni_verdict
    CASE as separate, differently-ranked checks."""
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN dim.is_known_bad_version IS TRUE THEN 'DISCARDED_BAD_PROBE_VERSION' "
        in sql
    )
    idx_true = sql.index("WHEN dim.is_known_bad_version IS TRUE THEN 'DISCARDED_BAD_PROBE_VERSION'")
    idx_0_2_3 = sql.index("WHEN s.test_name = 'signal' AND s.test_version = '0.2.3'")
    idx_0_2_2 = sql.index("WHEN s.test_name = 'signal' AND s.test_version = '0.2.2'")
    idx_false = sql.index("WHEN dim.is_known_bad_version IS FALSE THEN 'SCORED'")
    assert idx_true < idx_0_2_3 < idx_false, (
        "TD-102 regression: the 0.2.3 date-gated predicate has moved "
        "out of its expected position inside probe_accuracy_gate's own "
        "CASE, which would change this fix's interaction with TD-93/"
        "CONFIRMED/other FAILED checks."
    )
    assert idx_true < idx_0_2_2 < idx_false, (
        "TD-102 regression: the rescoped 0.2.2 blocked-only predicate "
        "has moved out of its expected position inside "
        "probe_accuracy_gate's own CASE."
    )


def test_signal_0_2_4_and_0_2_5_untouched_in_dim_table():
    sql = _normalized(DIM_PROBE_VERSION_SQL)
    assert "STRUCT('signal', '0.2.4', FALSE, 'Above the 0.2.2 cutoff -- not discarded by the sourced rule. 1,146 live rows.')," in sql
    assert "STRUCT('signal', '0.2.5', FALSE, 'Above the 0.2.2 cutoff -- not discarded by the sourced rule. 32,186 live rows.')," in sql


# ---------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------

@requires_bigquery
def test_live_signal_0_2_2_blocked_status_fully_discarded():
    """Structural, time-invariant regression guard: every signal/0.2.2
    row with signal_backend_status='blocked' must be discarded (NULL) --
    the rescoped, narrower predicate."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'signal' AND s.test_version = '0.2.2'
          AND s.signal_backend_status = 'blocked'
          AND v.ooni_verdict IS NOT NULL
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-102 regression (live): {n} signal/0.2.2 blocked-status rows "
        "have a non-NULL ooni_verdict -- the rescoped, blocked-only "
        "discard is not fully applied."
    )


@requires_bigquery
def test_live_signal_0_2_2_ok_status_restored_not_discarded():
    """The rescoping's own central claim: signal/0.2.2 rows with
    signal_backend_status='ok' must NOT be discarded -- this is the
    ~1,785-row population the first build session's version-wide rule
    incorrectly threw away. This test is the direct regression guard
    against silently widening 0.2.2 back to version-wide."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'signal' AND s.test_version = '0.2.2'
          AND s.signal_backend_status = 'ok'
          AND v.ooni_verdict IS NULL
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-102 regression (live): {n} signal/0.2.2 ok-status rows are "
        "discarded (NULL) -- the version-wide over-discard has "
        "regressed; these rows should be scored, not thrown away."
    )


@requires_bigquery
def test_live_signal_0_2_3_post_cutoff_fully_discarded():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'signal' AND s.test_version = '0.2.3'
          AND s.measurement_start_time > TIMESTAMP('2023-11-06T16:00:00')
          AND v.ooni_verdict IS NOT NULL
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-102 regression (live): {n} signal/0.2.3 post-cutoff rows "
        "have a non-NULL ooni_verdict -- the date-gated discard is not "
        "fully applied."
    )


@requires_bigquery
def test_live_signal_0_2_3_pre_cutoff_untouched():
    """Regression guard for the additive claim on the OTHER side of the
    date gate: 0.2.3's pre-cutoff population must still resolve to a
    real verdict (not NULL) -- this fix must not over-discard."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'signal' AND s.test_version = '0.2.3'
          AND s.measurement_start_time <= TIMESTAMP('2023-11-06T16:00:00')
          AND v.ooni_verdict IS NULL
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-102 regression (live): {n} signal/0.2.3 pre-cutoff rows "
        "were discarded -- the date gate is over-firing and swallowing "
        "genuine pre-cutoff detections."
    )


@requires_bigquery
def test_pinned_measurements_classify_as_expected():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    entries = _load_fixture()
    ids = [e["measurement_id"] for e in entries]
    query = f"""
        SELECT measurement_id, ooni_verdict
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts`
        WHERE measurement_id IN UNNEST(@ids)
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ArrayQueryParameter("ids", "STRING", ids),
    ])
    actual = {row.measurement_id: row.ooni_verdict for row in client.query(query, job_config=job_config).result()}

    for entry in entries:
        mid = entry["measurement_id"]
        assert mid in actual, f"pinned measurement_id {mid} not found live -- data may have moved/been re-ingested."
        assert actual[mid] == entry["expected_ooni_verdict"], (
            f"{mid} (test_version={entry['test_version']}, {entry['note']}): "
            f"expected {entry['expected_ooni_verdict']!r}, got {actual[mid]!r}"
        )
