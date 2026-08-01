"""
Golden-file test for TD-72 (this repo's numbering; "TD-73" in the Cowork
planning environment's numbering -- same finding, coincidental collision
with an unrelated, different TD-72 over there): stg.ooni_tls_observations.sql's
`handshake_success` was read from `$.status.success`, a field shape that
belongs to OONI's TCP-connect data format (present in these same four
tests' own tcp_connect[] arrays), never to a TLS handshake object. It was
NULL for 100% of this table's 422,487 rows, always -- a copy-paste of the
TCP extractor onto the wrong shape, not a real signal. Consequence:
int.ooni_experiment_results.sql's `tls` CTE's `handshake_success IS TRUE`
arm never fired, so every genuinely successful handshake (tls_failure IS
NULL) fell through to `ELSE 'UNKNOWN'` instead of 'OK' -- 386,617 of
422,487 rows (91.5%) across all four ingested test types.

Fix: `handshake_success` now derives from `tls_failure IS NULL` (no
failure string present = success), the same shape OONI's own canonical
TLS model uses (probe-cli's ArchivalTLSOrQUICHandshakeResult has no
boolean success field at all, only `failure`). Certificate trust stays a
separate, orthogonal concept (peer_certificate_sha256s /
presents_known_signal_root_ca, TD-69's own machinery) -- this fix does not
touch or duplicate that.

Two fixtures, per this project's golden-file-test discipline (mirrors
tests/test_ooni_tls_root_ca_exclusion.py and
tests/test_ooni_dns_canary_classification.py):

  (a) a real, genuinely successful TLS handshake (tls_failure IS NULL) --
      must now classify OK, not UNKNOWN.
  (b) a real, genuinely failed TLS handshake that was already classifying
      correctly before this fix (tls.rst / connection_reset -> BLOCKED) --
      must classify identically after this fix, proving the fix is
      provably narrow and does not touch failure-mode classification at
      all. This also guards against the specific trap this fix had to
      avoid: the CTE's pre-existing (but permanently dead, until this fix)
      `WHEN handshake_success IS FALSE THEN 'BLOCKED'` arm, which would
      have silently reclassified every non-reset/timeout/cert-exclusion
      failure mode from UNKNOWN to BLOCKED had it been left in place once
      handshake_success started working -- that arm was deliberately
      removed rather than resurrected (see int.ooni_experiment_results.sql
      comments), so this fixture also confirms no such reclassification
      happened for a case that could plausibly have been affected.
"""
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TLS_OBSERVATIONS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "staging" / "stg.ooni_tls_observations.sql"
)
EXPERIMENT_RESULTS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_experiment_results.sql"
)

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"

# (a) A real, successful whatsapp TLS handshake -- tls_failure IS NULL,
# not touched by the Signal-only cert-rotation exclusion (TD-69).
SUCCESS_FIXTURE_MEASUREMENT_ID = (
    "7ff13556c61d9752f411b480d1e2882c365dafaef9524bb627dfc4a06ac715f2"
)
SUCCESS_FIXTURE_OBSERVATION_ID = "d3c72205ece485913a2eb054537fb380"

# (b) A real, genuinely blocked telegram TLS handshake -- tls.rst /
# connection_reset, already classifying BLOCKED before this fix.
BLOCKED_FIXTURE_MEASUREMENT_ID = (
    "ecea775bee33057226ddadddf6c9f7c2af47770d588fc0eed7640f976d3b9fcd"
)
BLOCKED_FIXTURE_OBSERVATION_ID = "e5a738392c2fad5d26afd52674e6dc1d"


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def _code_only(path):
    """Strip `--`-style line comments before normalizing whitespace, so
    assertions about what the SQL actually *does* aren't fooled by prose
    comments (this file's own comments quote the removed CASE arm verbatim,
    inside backticks, to explain why it was removed)."""
    lines = (
        line for line in path.read_text().splitlines()
        if not line.strip().startswith("--")
    )
    return re.sub(r"\s+", " ", "\n".join(lines))


def test_staging_no_longer_reads_status_success_for_handshake_success():
    sql = _normalized(TLS_OBSERVATIONS_SQL)
    assert "JSON_VALUE(tls_json, '$.status.success')" not in sql, (
        "TD-72 regression: stg.ooni_tls_observations.sql still reads "
        "handshake_success from the wrong ($.status.success) JSONPath -- "
        "this field belongs to OONI's TCP-connect format, not TLS."
    )
    assert "IS NULL AS handshake_success" in sql, (
        "TD-72 regression: handshake_success should derive from the "
        "tls_failure COALESCE expression being NULL (no failure string "
        "present = success), matching OONI's own canonical TLS model."
    )


def test_sql_does_not_resurrect_the_dead_blocked_arm():
    sql = _code_only(EXPERIMENT_RESULTS_SQL)
    assert "handshake_success IS FALSE THEN 'BLOCKED'" not in sql, (
        "TD-72 regression: the tls CTE's result_state CASE must not gate "
        "on `handshake_success IS FALSE` -- now that handshake_success "
        "is real (not always NULL), that arm would fire for every "
        "non-reset/timeout/cert-exclusion TLS failure mode and silently "
        "reclassify it from UNKNOWN to BLOCKED, which is TD-71's separate, "
        "still-open per-failure-mode question, not this fix's scope."
    )
    assert "handshake_success IS FALSE THEN 0.75" not in sql, (
        "TD-72 regression: confidence_score must not gate on "
        "`handshake_success IS FALSE` either, for the same reason -- "
        "failure-row confidence should stay at its pre-fix value."
    )
    assert (
        "[BLOCKED, OK, DOWN, UNKNOWN]" in sql
    ), (
        "TD-72 regression: result_state's accepted_values enum should not "
        "have gained a new value from this fix."
    )


@requires_bigquery
def test_live_genuine_success_now_classifies_ok():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT result_state, failure_reason, exclusion_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE measurement_id = '{SUCCESS_FIXTURE_MEASUREMENT_ID}'
          AND observation_id = '{SUCCESS_FIXTURE_OBSERVATION_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 1, (
        f"Expected exactly 1 TLS handshake row for the success fixture, "
        f"found {len(rows)}."
    )
    row = rows[0]
    assert row.result_state == "OK", (
        f"TD-72 regression (golden fixture a): a genuinely successful "
        f"handshake (failure_reason={row.failure_reason!r}) still "
        f"classifies {row.result_state}, expected OK."
    )
    assert row.failure_reason is None
    assert row.exclusion_reason is None, (
        "A plain successful handshake should not carry an exclusion_reason "
        "-- that column is reserved for the Signal root-CA carve-out."
    )


@requires_bigquery
def test_live_genuine_block_still_classifies_blocked():
    """Fixture (b): proves the fix is provably narrow -- a real TLS reset,
    already classifying BLOCKED before this fix, classifies identically
    after it. This is the specific case that would have silently flipped
    to a *different* verdict had the dead `handshake_success IS FALSE`
    arm been left in place instead of removed."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT result_state, blocking_detail, failure_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE measurement_id = '{BLOCKED_FIXTURE_MEASUREMENT_ID}'
          AND observation_id = '{BLOCKED_FIXTURE_OBSERVATION_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 1, (
        f"Expected exactly 1 TLS handshake row for the blocked fixture, "
        f"found {len(rows)}."
    )
    row = rows[0]
    assert row.result_state == "BLOCKED", (
        f"TD-72 regression (golden fixture b): a genuine tls.rst block "
        f"now classifies {row.result_state}, expected BLOCKED unchanged."
    )
    assert row.blocking_detail == "tls.rst"


@requires_bigquery
def test_live_no_row_has_null_handshake_success():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS null_count
        FROM `{PROJECT_ID}.stg.ooni_tls_observations`
        WHERE handshake_success IS NULL
    """
    row = next(client.query(query).result())
    assert row.null_count == 0, (
        "TD-72 regression: handshake_success should never be NULL post-fix "
        "-- it is a deterministic function of tls_failure IS NULL, which "
        "is itself never NULL-valued in a way that would propagate here."
    )
