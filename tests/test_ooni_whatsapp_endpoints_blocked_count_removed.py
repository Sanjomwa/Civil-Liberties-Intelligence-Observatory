"""
Regression lock for TD-105's build fix: whatsapp's test_anomaly_flag arm
no longer treats whatsapp_endpoints_blocked_count > 0 or
whatsapp_endpoints_dns_inconsistent_count > 0 as ANOMALOUS drivers --
both conditions are REMOVED from the OR-chain, not thresholded.

Two verification sessions (2026-08-21, 2026-08-22) found
whatsapp_endpoints_blocked_count > 0 actively wrong, not just imprecise:
OONI's own live scorer source contains this exact rule, commented out,
with the note "Disabled due to bug in the probe
https://github.com/ooni/probe-engine/issues/341". Restricted to the
population where blocked_count was the ONLY driver (no co-occurring
web-check or registration failure), OONI's real classification agreed
with CLIO's ANOMALOUS call 0/131 times across two independently-drawn
samples, spanning the full blocked_count range (1-15) and every
magnitude bucket. The earlier-observed "high count usually means real
interference" pattern was a confound: high-blocked_count rows are
disproportionately ones where a web or registration failure ALSO
occurred (only 18.4% of the highest bucket is actually isolated from
that), and OONI's own scorer never reaches its endpoint-accessibility
check at all once the web/registration checks have already failed --
confirmed directly via OONI's `scores.analysis` sub-object, present only
when that branch is reached.

whatsapp_endpoints_dns_inconsistent_count > 0 is removed alongside it as
dead weight, not on its own merits: confirmed permanently 0/51,394 rows
live, never populated by the probe.

THIS TEST EXISTS SPECIFICALLY TO STOP A FUTURE REFACTOR FROM SILENTLY
REINTRODUCING EITHER CONDITION, THRESHOLDED OR OTHERWISE. If a future
edit adds any severity-aware logic keyed on whatsapp_endpoints_blocked_
count back into the OR-chain, that is a design decision that needs its
own fresh evidence -- this test's static assertions must fail to force
that conversation, not silently pass.

Two layers of protection, same pattern as
tests/test_ooni_whatsapp_web_accessible_classification.py:

1. Static SQL-text assertions (always run, zero credentials). Checks
   that both conditions are ABSENT from the whatsapp OR-chain, and that
   the three surviving conditions are present, unchanged.

2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1.
   whatsapp has a valid, non-degenerate oracle (OONI's own
   /api/v1/measurements), confirmed by two verification sessions -- used
   as ground truth throughout.

PINNED FIXTURE (tests/fixtures/ooni_whatsapp_endpoints_blocked_count_removed/
pinned_measurements.json): 5 real measurement_ids -- 2 reclassified
(low and highest-observed blocked_count buckets, ANOMALOUS->OK), 2
regression guards proving a second real driver (whatsapp_web_accessible,
registration_server_status) keeps a row ANOMALOUS despite the removal,
and 1 guard for an already-OK row never touched by blocked_count at all.
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
    REPO_ROOT / "tests" / "fixtures" / "ooni_whatsapp_endpoints_blocked_count_removed"
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

def test_whatsapp_endpoints_blocked_count_removed_from_orchain():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert "OR s.whatsapp_endpoints_blocked_count > 0" not in sql, (
        "TD-105 build regression: whatsapp_endpoints_blocked_count > 0 is "
        "back in the whatsapp OR-chain. Two verification sessions found "
        "0/131 agreement with OONI once isolated from the bug (a)/(c) "
        "confound, and OONI's own scorer disables this exact rule in "
        "source. If this needs to come back, it needs fresh evidence, "
        "not a silent revert."
    )


def test_whatsapp_endpoints_dns_inconsistent_count_removed_from_orchain():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert "OR s.whatsapp_endpoints_dns_inconsistent_count > 0" not in sql, (
        "TD-105 build regression: whatsapp_endpoints_dns_inconsistent_count "
        "> 0 is back in the whatsapp OR-chain. This field is permanently "
        "dead (never populated by the probe, confirmed 0/51,394 live "
        "rows) and was removed as dead weight."
    )


def test_whatsapp_orchain_surviving_conditions_unchanged():
    sql = _normalized(VERDICTS_CANDIDATE_SQL)
    assert (
        "WHEN s.whatsapp_endpoints_status = 'blocked' "
        "OR s.whatsapp_web_accessible IS FALSE "
        "OR s.registration_server_status = 'blocked' THEN TRUE"
        in sql
    ), (
        "TD-105 build regression: the whatsapp OR-chain's surviving three "
        "conditions (whatsapp_endpoints_status, whatsapp_web_accessible, "
        "registration_server_status) have drifted from the exact shape "
        "the build session shipped -- none of these three were meant to "
        "change in this fix."
    )


# ---------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------

@requires_bigquery
def test_live_reclassified_population_matches_expected_size():
    """The sole-driver population (blocked_count was the ONLY thing
    keeping the row out of OK) was measured at 514 rows during the build
    session's verification. This is a real population, not a fixed
    constant -- allow drift as new data lands, but the count should stay
    in the same order of magnitude, not collapse to 0 or explode."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.stg.ooni_measurement_summary`
        WHERE test_name = 'whatsapp'
          AND whatsapp_endpoints_blocked_count > 0
          AND whatsapp_endpoints_status = 'ok'
          AND (whatsapp_web_accessible IS NULL OR whatsapp_web_accessible IS TRUE)
          AND registration_server_status = 'ok'
    """
    n = next(client.query(query).result()).n
    assert n > 0, (
        "TD-105 build's reclassified population is empty -- expected "
        "roughly 514 rows (as of 2026-08-22) where blocked_count was the "
        "sole ANOMALOUS driver before this fix."
    )


@requires_bigquery
def test_live_reclassified_population_is_now_ok():
    """Structural, time-invariant guard for the fix's actual effect: any
    row where blocked_count/dns_inconsistent_count were the ONLY signal
    (every other condition clean) must now be OK, not ANOMALOUS."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'whatsapp'
          AND (s.whatsapp_endpoints_blocked_count > 0 OR s.whatsapp_endpoints_dns_inconsistent_count > 0)
          AND s.whatsapp_endpoints_status = 'ok'
          AND (s.whatsapp_web_accessible IS NULL OR s.whatsapp_web_accessible IS TRUE)
          AND s.registration_server_status = 'ok'
          AND v.ooni_verdict != 'OK'
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-105 build regression (live): {n} whatsapp rows where "
        "blocked_count/dns_inconsistent_count were the sole signal are "
        "NOT classified OK -- the removal did not take effect for these "
        "rows."
    )


@requires_bigquery
def test_live_no_row_with_independent_driver_true_is_missing_anomalous():
    """Additive-proof regression guard: any whatsapp row where
    endpoints_status/whatsapp_web_accessible/registration_server_status
    independently indicate blocking must be ANOMALOUS, regardless of
    blocked_count/dns_inconsistent_count."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'whatsapp'
          AND (
            s.whatsapp_endpoints_status = 'blocked'
            OR s.whatsapp_web_accessible IS FALSE
            OR s.registration_server_status = 'blocked'
          )
          AND v.ooni_verdict != 'ANOMALOUS'
    """
    n = next(client.query(query).result()).n
    assert n == 0, (
        f"TD-105 build additive-claim regression (live): {n} whatsapp "
        "rows have a real, independent driver true but are NOT "
        "classified ANOMALOUS."
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
