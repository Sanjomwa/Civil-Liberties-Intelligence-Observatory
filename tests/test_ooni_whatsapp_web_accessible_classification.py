"""
Regression lock for TD-105's fix: whatsapp's test_anomaly_flag arm now
recomputes web-check accessibility from raw $.requests[] instead of
trusting the probe-submitted whatsapp_web_status field, which an
eight-check verification session (2026-08-21) found unreliable
specifically at probe test_version=0.9.0 -- that probe version's own
plain-HTTP check against http://web.whatsapp.com/ marks the whole web
check "failed" whenever the response isn't exactly HTTP 302, regardless
of whether the HTTPS leg of the same URL succeeded, and OONI's own
backend scorer never reads this field at all. Probe 0.11.0 removes the
flawed check entirely.

THIS TEST EXISTS SPECIFICALLY TO STOP A FUTURE REFACTOR FROM SILENTLY
WIDENING THIS FIX INTO BUG (b)/(c)'S TERRITORY. The same verification
session investigated two other conditions in whatsapp's OR-chain --
whatsapp_endpoints_blocked_count > 0 (real, but heterogeneous: a small
oracle check split roughly 50/50 against OONI's own judgment) and
registration_server_status = 'blocked' (89% genuinely correct across
both probe versions) -- and found neither shares bug (a)'s shape.
Folding either into this fix, or "cleaning up" the OR-chain while in
this file, was explicitly out of scope. If a future edit changes any of
the OTHER four OR-chain conditions, or the NULL-check branch, this
file's static assertions must fail.

UPDATE (TD-105 build, 2026-08-22): bug (b) (whatsapp_endpoints_blocked_
count > 0 and the always-dead whatsapp_endpoints_dns_inconsistent_count
> 0) received its own dedicated investigation and was found actively
wrong (OONI's own scorer disables this exact rule in source, and two
independent samples found 0/131 agreement once isolated from bug (a)/(c)
as a confound) -- see tests/test_ooni_whatsapp_endpoints_blocked_count_
removed.py for that fix's own regression lock. This file's static
assertion below is updated accordingly: it now asserts the whatsapp
OR-chain has exactly THREE conditions (whatsapp_endpoints_status,
whatsapp_web_accessible, registration_server_status), not five --
bug (b)'s two conditions are asserted ABSENT, not present. Bug (c)
(registration_server_status) remains untouched and is still guarded
here.

Two layers of protection, same pattern as
tests/test_ooni_dnscheck_bootstrap_failed_classification.py:

1. Static SQL-text assertions (always run, zero credentials). Checks
   that the whatsapp OR-chain's web-check condition now reads
   whatsapp_web_accessible IS FALSE (not whatsapp_web_status = 'blocked'),
   that the other four conditions and the NULL-check branch are
   byte-for-byte unchanged, and that whatsapp_web_accessible's extraction
   exists in staging.

2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1.
   Unlike dnscheck (TD-103: confirmed-degenerate oracle), whatsapp has a
   valid, non-degenerate oracle -- OONI's own /api/v1/measurements is used
   as ground truth for the pinned fixture's bug-(a)-related rows and the
   registration-server regression guard. ONE fixture row (the bug-(b)
   guard) deliberately uses CLIO's own OR-chain logic as ground truth
   instead, per that row's own note in the fixture file -- see
   tests/fixtures/ooni_whatsapp_web_accessible_classification/
   pinned_measurements.json's top-level _comment for why.

PINNED FIXTURE (tests/fixtures/ooni_whatsapp_web_accessible_classification/
pinned_measurements.json): 8 real measurement_ids -- 2 reclassified
(test_version=0.9.0, ANOMALOUS->OK), 2 regression guards proving a
second real driver keeps a 0.9.0 row ANOMALOUS despite the web-check fix,
2 regression guards at test_version=0.11.0 (already correct, provably
unchanged), and one guard each for bug (c) and bug (b) proving those
conditions are untouched.
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
STG_SUMMARY_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "staging" / "stg.ooni_measurement_summary.sql"
)
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "ooni_whatsapp_web_accessible_classification"
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

def test_whatsapp_web_check_uses_accessible_not_status():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert "OR s.whatsapp_web_accessible IS FALSE" in sql, (
        "TD-105 regression: whatsapp's test_anomaly_flag arm no longer routes "
        "the web-check condition through whatsapp_web_accessible -- it may "
        "have reverted to the unreliable whatsapp_web_status = 'blocked' "
        "field, which is confirmed wrong for 100% of test_version=0.9.0's "
        "http_unexpected_status_code rows."
    )
    assert "OR s.whatsapp_web_status = 'blocked'" not in sql, (
        "TD-105 regression: the old, unreliable whatsapp_web_status = "
        "'blocked' condition is back in the OR-chain."
    )


def test_whatsapp_other_orchain_conditions_untouched():
    """Bug (c) (registration_server_status) must stay byte-for-byte
    unchanged. Bug (b)'s two conditions (whatsapp_endpoints_blocked_count,
    whatsapp_endpoints_dns_inconsistent_count) are asserted ABSENT, not
    present -- TD-105's build session (2026-08-22) removed them; see
    test_ooni_whatsapp_endpoints_blocked_count_removed.py for that fix's
    own regression lock."""
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN s.whatsapp_endpoints_status = 'blocked' "
        "OR s.whatsapp_web_accessible IS FALSE "
        "OR s.registration_server_status = 'blocked' THEN TRUE"
        in sql
    ), (
        "TD-105 regression: the whatsapp OR-chain's full text has drifted "
        "from the exact shape the TD-105 build session shipped -- bug (c) "
        "(registration_server_status) must stay byte-for-byte unchanged, "
        "and bug (b)'s two conditions must stay removed. This fix touches "
        "ONLY the web-check condition. If this assertion fails, check "
        "whether an unrelated edit reordered or changed one of the other "
        "two conditions, or reintroduced bug (b)."
    )
    assert "OR s.whatsapp_endpoints_blocked_count > 0" not in sql, (
        "TD-105 build regression: whatsapp_endpoints_blocked_count > 0 is "
        "back in the OR-chain -- this condition was deliberately removed "
        "(not thresholded) after two verification sessions found 0/131 "
        "agreement with OONI once isolated from the bug (a)/(c) confound."
    )
    assert "OR s.whatsapp_endpoints_dns_inconsistent_count > 0" not in sql, (
        "TD-105 build regression: whatsapp_endpoints_dns_inconsistent_count "
        "> 0 is back in the OR-chain -- this field is permanently dead "
        "(never populated by the probe, confirmed 0/51,394 live rows) and "
        "was deliberately removed as dead weight."
    )


def test_whatsapp_null_check_branch_untouched():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN s.whatsapp_endpoints_status IS NULL "
        "AND s.whatsapp_web_status IS NULL "
        "AND s.registration_server_status IS NULL THEN NULL"
        in sql
    ), (
        "TD-105 regression: the whatsapp NULL-check branch (deciding when "
        "the whole row is unscored) has changed -- TD-105 deliberately left "
        "this on whatsapp_web_status, not whatsapp_web_accessible, since "
        "whatsapp_web_status is never NULL in live data and this branch was "
        "explicitly out of this fix's scope."
    )


def test_whatsapp_web_accessible_extraction_exists_in_staging():
    sql = _normalized(STG_SUMMARY_SQL)
    assert "AS whatsapp_web_accessible" in sql, (
        "TD-105 regression: whatsapp_web_accessible is no longer extracted "
        "in stg.ooni_measurement_summary.sql -- the verdicts candidate "
        "asset's whatsapp arm has nothing to read."
    )
    assert "https://web.whatsapp.com/" in sql, (
        "TD-105 regression: the whatsapp_web_accessible extraction no "
        "longer matches on the expected fixed URL -- confirm it wasn't "
        "changed to a pattern match or a different target."
    )


# ---------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------

@requires_bigquery
def test_live_whatsapp_web_accessible_matches_status_at_fixed_probe_version():
    """The load-bearing invariant this fix's additive claim rests on:
    test_version=0.11.0 has no plain-HTTP-leg bug, so whatsapp_web_status
    should always equal what whatsapp_web_accessible computes, for every
    row, forever (not just the 40-row sample TD-105's Task 0.3 checked).
    A violation here means either a future OONI probe update changed
    0.11.0's behavior, or the extraction itself broke."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
          COUNTIF(whatsapp_web_status = 'blocked' AND whatsapp_web_accessible IS NOT FALSE) AS blocked_but_not_flagged,
          COUNTIF(whatsapp_web_status = 'ok' AND whatsapp_web_accessible IS NOT TRUE) AS ok_but_not_accessible
        FROM `{PROJECT_ID}.stg.ooni_measurement_summary`
        WHERE test_name = 'whatsapp' AND test_version = '0.11.0'
    """
    row = next(client.query(query).result())
    assert row.blocked_but_not_flagged == 0, (
        f"TD-105 regression (live): {row.blocked_but_not_flagged} "
        "test_version=0.11.0 rows have whatsapp_web_status='blocked' but "
        "whatsapp_web_accessible is not FALSE -- the two fields have "
        "diverged at the one probe version where they're expected to "
        "always agree."
    )
    assert row.ok_but_not_accessible == 0, (
        f"TD-105 regression (live): {row.ok_but_not_accessible} "
        "test_version=0.11.0 rows have whatsapp_web_status='ok' but "
        "whatsapp_web_accessible is not TRUE -- same divergence, opposite "
        "direction."
    )


@requires_bigquery
def test_live_whatsapp_reclassified_population_is_nonempty():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.stg.ooni_measurement_summary`
        WHERE test_name = 'whatsapp'
          AND test_version = '0.9.0'
          AND whatsapp_web_status = 'blocked'
          AND whatsapp_web_accessible IS TRUE
    """
    n = next(client.query(query).result()).n
    assert n > 0, (
        "TD-105's fix appears to have no effect: expected a nonzero "
        "population of test_version=0.9.0 rows where the old field said "
        "'blocked' but the new field says accessible."
    )


@requires_bigquery
def test_live_no_row_with_other_driver_true_is_missing_anomalous():
    """Structural, time-invariant regression guard for the additive claim:
    any whatsapp row where endpoints_status/registration_server_status
    independently indicate blocking must be ANOMALOUS, regardless of what
    the web-check condition says. Updated by the TD-105 build session
    (2026-08-22): whatsapp_endpoints_blocked_count/dns_inconsistent_count
    are deliberately EXCLUDED from this list now -- they no longer drive
    ooni_verdict at all, so a row with blocked_count>0 alone is expected
    to be OK, not a violation. See
    test_ooni_whatsapp_endpoints_blocked_count_removed.py for that fix's
    own regression guard covering the removed conditions."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'whatsapp'
          AND (
            s.whatsapp_endpoints_status = 'blocked'
            OR s.registration_server_status = 'blocked'
          )
          AND v.ooni_verdict != 'ANOMALOUS'
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-105 additive-claim regression (live): {n} whatsapp rows have "
        "a real driver (bug (c)'s condition or whatsapp_endpoints_status, "
        "both untouched by this fix) true but are NOT classified "
        "ANOMALOUS."
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
