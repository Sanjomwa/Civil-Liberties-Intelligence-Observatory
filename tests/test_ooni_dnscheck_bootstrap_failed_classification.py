"""
Regression lock for TD-101 Phase 3's fix: dnscheck's FAILED tier is now
reachable, via a NARROW carve-out -- not a blanket rule.

dns_bogon_error (dnscheck_bootstrap_failure) keeps its ANOMALOUS
classification, unchanged: TD-55 already established it as a real,
sampling-validated manipulation signal (whole-session bogoning of
DoH/DoT resolver hostnames while messaging-app DNS resolved normally on
the same network-day), already classified BLOCKED @ 0.90 confidence in
int.ooni_experiment_results.sql, and already regression-locked by
tests/test_ooni_dns_bogon_classification.py. Every OTHER non-NULL
dnscheck_bootstrap_failure value (dns_nxdomain_error,
generic_timeout_error, android_dns_cache_no_data, dns_temporary_failure,
dns_server_misbehaving) newly routes to FAILED instead of ANOMALOUS.

THIS TEST EXISTS SPECIFICALLY TO STOP A FUTURE REFACTOR FROM SILENTLY
REVERTING TD-55 THE WAY AN EARLIER DESIGN DRAFT ALMOST DID. An earlier
design pass for TD-101 considered routing ALL non-NULL
dnscheck_bootstrap_failure values to FAILED -- a blanket rule -- which
would have silently and partially reverted TD-55 (dns_bogon_error would
have stopped being ANOMALOUS) and produced a live contradiction between
result_state (BLOCKED, from int.ooni_experiment_results.sql, untouched
by this fix) and ooni_verdict (FAILED) for the same underlying rows. An
advisory review caught this before any code was written, by reading the
live codebase directly. If a future edit to
int.ooni_measurement_verdicts_candidate.sql's dnscheck arm removes the
dns_bogon_error exception from either the test_anomaly_flag CASE or the
ooni_verdict FAILED-tier predicate, this file's static assertions must
fail.

Two layers of protection, same pattern as
tests/test_ooni_dns_bogon_classification.py:

1. Static SQL-text assertions (always run, zero credentials). Checks
   that the ANOMALOUS branch (test_anomaly_flag's dnscheck arm) matches
   dns_bogon_error ONLY, and that the FAILED branch's own predicate
   explicitly EXCLUDES dns_bogon_error rather than relying on branch
   ordering (FAILED already outranks ANOMALOUS in this file's CASE
   precedence -- a predicate that only tested "IS NOT NULL" would
   silently swallow the bogon rows too).

2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1
   like tests/test_acled_pressure_regimes_golden.py and
   tests/test_ooni_dns_bogon_classification.py's own live layer.

PINNED FIXTURE (tests/fixtures/ooni_dnscheck_bootstrap_classification/
pinned_measurements.json): 7 real measurement_ids spanning all six live
dnscheck_bootstrap_failure values (2 bogon, 5 distinct non-bogon).
Ground truth is TD-55's own sampled evidence and this session's live
investigation of the five non-bogon values -- explicitly NOT OONI's own
/api/v1/measurements API, which is confirmed degenerate for dnscheck
(TD-103) and must not be treated as validation here.
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
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "ooni_dnscheck_bootstrap_classification"
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

def test_dnscheck_anomaly_flag_matches_bogon_only():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN LOWER(COALESCE(s.dnscheck_bootstrap_failure, '')) = 'dns_bogon_error' THEN TRUE"
        in sql
    ), (
        "TD-101 Phase 3 regression: dnscheck's test_anomaly_flag arm no longer "
        "matches dns_bogon_error specifically -- it may have reverted to 'any "
        "non-NULL bootstrap failure', which is the blanket rule this fix "
        "deliberately rejected (it would silently revert TD-55)."
    )


def test_dnscheck_failed_branch_excludes_bogon_explicitly():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN dnscheck_bootstrap_failure IS NOT NULL AND "
        "LOWER(COALESCE(dnscheck_bootstrap_failure, '')) != 'dns_bogon_error' "
        "THEN 'FAILED'"
        in sql
    ), (
        "TD-101 Phase 3 regression: the FAILED tier's dnscheck predicate no "
        "longer excludes dns_bogon_error explicitly. Because FAILED outranks "
        "ANOMALOUS in this file's CASE precedence, a bare "
        "'dnscheck_bootstrap_failure IS NOT NULL THEN FAILED' predicate would "
        "silently route dns_bogon_error rows to FAILED too -- a partial "
        "revert of TD-55 and a live contradiction with result_state=BLOCKED "
        "for the same rows."
    )


def test_dnscheck_bootstrap_failure_is_carried_through_verdicts_cte():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert "s.dnscheck_bootstrap_failure," in sql, (
        "TD-101 Phase 3 regression: dnscheck_bootstrap_failure is no longer "
        "carried through the verdicts CTE's select list -- the FAILED-tier "
        "predicate above has nothing to read."
    )


# ---------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------

@requires_bigquery
def test_live_bogon_rows_are_anomalous_not_failed():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT v.ooni_verdict, COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'dnscheck'
          AND LOWER(COALESCE(s.dnscheck_bootstrap_failure, '')) = 'dns_bogon_error'
        GROUP BY 1
    """
    rows = {row.ooni_verdict: row.n for row in client.query(query).result()}
    assert rows.get("FAILED", 0) == 0, (
        f"TD-101 Phase 3 / TD-55 regression (live): {rows.get('FAILED')} "
        "dns_bogon_error rows classify FAILED -- they must stay ANOMALOUS."
    )
    assert rows.get("ANOMALOUS", 0) > 0, (
        "No dns_bogon_error rows classify ANOMALOUS at all -- either the "
        "carve-out broke, or TD-55's underlying bogon rows disappeared "
        "upstream (check stg.ooni_measurement_summary)."
    )


@requires_bigquery
def test_live_non_bogon_bootstrap_failures_are_failed_not_anomalous():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT v.ooni_verdict, COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'dnscheck'
          AND s.dnscheck_bootstrap_failure IS NOT NULL
          AND LOWER(COALESCE(s.dnscheck_bootstrap_failure, '')) != 'dns_bogon_error'
        GROUP BY 1
    """
    rows = {row.ooni_verdict: row.n for row in client.query(query).result()}
    assert rows.get("ANOMALOUS", 0) == 0, (
        f"TD-101 Phase 3 regression (live): {rows.get('ANOMALOUS')} non-bogon "
        "dnscheck bootstrap-failure rows still classify ANOMALOUS -- the "
        "narrow carve-out may have widened back into a blanket rule, or a "
        "new bootstrap-failure value appeared that this fix's predicate "
        "doesn't route correctly."
    )
    assert rows.get("FAILED", 0) > 0, (
        "TD-101's own structural gap (FAILED unreachable for dnscheck) is "
        "not closed -- expected a nonzero FAILED count for non-bogon "
        "bootstrap failures."
    )


@requires_bigquery
def test_live_dnscheck_failed_is_reachable():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts`
        WHERE test_name = 'dnscheck' AND ooni_verdict = 'FAILED'
    """
    n = next(client.query(query).result()).n
    assert n > 0, (
        "TD-101's structural gap is not closed: dnscheck FAILED count is "
        "still 0."
    )


@requires_bigquery
def test_live_dnscheck_anomalous_equals_bogon_row_count_exactly():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        WITH anomalous AS (
          SELECT COUNT(*) AS n
          FROM `{PROJECT_ID}.int.ooni_measurement_verdicts`
          WHERE test_name = 'dnscheck' AND ooni_verdict = 'ANOMALOUS'
        ),
        bogon AS (
          SELECT COUNT(*) AS n
          FROM `{PROJECT_ID}.stg.ooni_measurement_summary`
          WHERE test_name = 'dnscheck'
            AND LOWER(COALESCE(dnscheck_bootstrap_failure, '')) = 'dns_bogon_error'
        )
        SELECT (SELECT n FROM anomalous) AS anomalous_n, (SELECT n FROM bogon) AS bogon_n
    """
    row = next(client.query(query).result())
    assert row.anomalous_n == row.bogon_n, (
        f"dnscheck ANOMALOUS count ({row.anomalous_n}) no longer equals the "
        f"live dns_bogon_error row count ({row.bogon_n}) exactly -- some "
        "other value may be leaking into ANOMALOUS, or a bogon row is "
        "leaking out (e.g. via probe_accuracy_gate or a new dnscheck-only "
        "discard rule)."
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
            f"{mid} ({entry['dnscheck_bootstrap_failure']}, {entry['note']}): "
            f"expected {entry['expected_ooni_verdict']!r}, got {actual[mid]!r}"
        )
