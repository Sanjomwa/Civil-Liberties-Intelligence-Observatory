"""
Golden-file test for TD-71 (this repo's numbering): the `tls` CTE's
confidence_score CASE used to collapse every non-reset/timeout/cert-
exclusion TLS failure mode into a single flat `ELSE 0.45`, discarding the
per-failure-mode evidentiary weight already visible in `tls_failure`
(connection_reset is strong active-interference evidence; a captive-
portal-style timeout is weak; eof_error/connection_aborted are genuinely
ambiguous per OONI's own error-string spec).

Fix: marts.dim_tls_failure_evidence, a small dimension table (tls_failure
-> tier -> standalone_confidence, sourced against ooni/spec's
df-007-errors.md), joined into int.ooni_experiment_results.sql's `tls_source`
CTE and consumed by the confidence_score CASE via
`COALESCE(tls_failure_standalone_confidence, 0.45)` -- the COALESCE is the
default-low allowlist: any tls_failure string absent from the dimension
table (today or in the future) silently keeps the pre-fix floor, never an
elevated tier it was never reviewed for.

result_state (BLOCKED for connection_reset, DOWN for
generic_timeout_error) is unchanged by this fix -- it comes from the
CTE's existing LIKE-pattern arms, not from the dimension table. Only
confidence_score moves, for the failure modes with a real entry in
marts.dim_tls_failure_evidence.

Four fixtures, per this project's golden-file-test discipline (mirrors
tests/test_ooni_tls_handshake_success_fix.py):

  (a) connection_reset (test_name=signal) -- confidence_score must be
      0.60 (up from the pre-fix flat 0.45), result_state still BLOCKED.
  (b) generic_timeout_error (test_name=signal) -- confidence_score must
      be 0.40 (down from 0.45), result_state still DOWN.
  (c) eof_error (test_name=psiphon) -- confidence_score must be 0.50,
      result_state still UNKNOWN (eof_error has no dedicated
      result_state arm, so it still falls through to the same UNKNOWN
      fallback as before this fix -- only its confidence value moves).
  (d) a synthetic, deliberately unmapped tls_failure string -- proves the
      default-low allowlist itself: joining against
      marts.dim_tls_failure_evidence for a string not present in it
      produces NULL, so COALESCE(..., 0.45) must resolve to exactly 0.45,
      never something higher. Live data currently has zero unmapped
      tls_failure strings (verified separately, not by this fixture) --
      this fixture exercises the fallback mechanism directly rather than
      waiting for OONI to introduce a new failure string.
"""
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_RESULTS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_experiment_results.sql"
)
DIM_TLS_FAILURE_EVIDENCE_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "marts" / "dims" / "dim_tls_failure_evidence.sql"
)

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"

# (a) A real signal TLS connection_reset -- already classifying BLOCKED
# before this fix; only its confidence should move.
RESET_FIXTURE_OBSERVATION_ID = "6dd258b77de9764e3c5366533a20ad28"

# (b) A real signal TLS generic_timeout_error -- already classifying DOWN
# before this fix; only its confidence should move.
TIMEOUT_FIXTURE_OBSERVATION_ID = "d911fc1e1e69e18102c49e71e891db61"

# (c) A real psiphon TLS eof_error -- no dedicated result_state arm,
# stays UNKNOWN; only its confidence should move.
EOF_FIXTURE_OBSERVATION_ID = "8590ce1b15397a364da18feead72fdb3"


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def test_dim_table_has_no_duplicate_tls_failure_entries():
    """Static sanity check: the dimension table's join key
    (tls_failure) must be unique, or the LEFT JOIN in tls_source would
    fan out rows -- checked by construction here (the file is a literal
    UNNEST), not just trusted."""
    sql = DIM_TLS_FAILURE_EVIDENCE_SQL.read_text()
    failures = re.findall(r"'([a-z_]+)' AS tls_failure", sql)
    assert len(failures) == len(set(failures)), (
        f"Duplicate tls_failure entries in dim_tls_failure_evidence.sql: {failures}"
    )
    assert len(failures) >= 6, (
        "Expected at least the 6 tls_failure strings confirmed live in "
        "Kenya's TLS data as of 2026-08-01 (connection_reset, "
        "generic_timeout_error, eof_error, connection_aborted, "
        "ssl_invalid_certificate, ssl_unknown_authority)."
    )


def test_sql_defaults_unmapped_failures_low_not_high():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert "COALESCE(tls_failure_standalone_confidence, 0.45)" in sql, (
        "TD-71 regression: the tls CTE's confidence_score CASE must "
        "default an unmapped/unmatched tls_failure to the pre-fix floor "
        "(0.45) via COALESCE -- an unmatched LEFT JOIN must default down, "
        "never up to an elevated tier it was never reviewed for."
    )


@requires_bigquery
def test_live_connection_reset_confidence_raised_state_unchanged():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT result_state, blocking_detail, confidence_score, failure_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE observation_id = '{RESET_FIXTURE_OBSERVATION_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 1
    row = rows[0]
    assert row.failure_reason == "connection_reset"
    assert row.result_state == "BLOCKED", (
        "TD-71 regression (golden fixture a): connection_reset's "
        "result_state must stay BLOCKED -- this fix only touches "
        "confidence_score, not the reset arm's own state routing."
    )
    assert row.blocking_detail == "tls.rst"
    assert row.confidence_score == pytest.approx(0.60), (
        f"TD-71 regression (golden fixture a): connection_reset "
        f"confidence_score is {row.confidence_score}, expected 0.60 "
        f"(up from the pre-fix flat 0.45 -- RST injection is the "
        f"strongest single-failure-mode evidence in this table)."
    )


@requires_bigquery
def test_live_generic_timeout_confidence_lowered_state_unchanged():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT result_state, blocking_detail, confidence_score, failure_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE observation_id = '{TIMEOUT_FIXTURE_OBSERVATION_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 1
    row = rows[0]
    assert row.failure_reason == "generic_timeout_error"
    assert row.result_state == "DOWN", (
        "TD-71 regression (golden fixture b): generic_timeout_error's "
        "result_state must stay DOWN -- this fix only touches "
        "confidence_score, not the timeout arm's own state routing."
    )
    assert row.blocking_detail == "tls.timeout"
    assert row.confidence_score == pytest.approx(0.40), (
        f"TD-71 regression (golden fixture b): generic_timeout_error "
        f"confidence_score is {row.confidence_score}, expected 0.40 "
        f"(down from the pre-fix flat 0.45 -- timeouts are the least "
        f"attributable TLS failure mode, indistinguishable from ordinary "
        f"network unreachability from this vantage point)."
    )


@requires_bigquery
def test_live_eof_error_confidence_set_state_unchanged():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT result_state, blocking_detail, confidence_score, failure_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE observation_id = '{EOF_FIXTURE_OBSERVATION_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 1
    row = rows[0]
    assert row.failure_reason == "eof_error"
    assert row.result_state == "UNKNOWN", (
        "TD-71 regression (golden fixture c): eof_error has no dedicated "
        "result_state arm -- must still fall through to UNKNOWN, "
        "unchanged by this fix."
    )
    assert row.confidence_score == pytest.approx(0.50), (
        f"TD-71 regression (golden fixture c): eof_error confidence_score "
        f"is {row.confidence_score}, expected 0.50 (genuinely ambiguous "
        f"evidence per ooni/spec -- neither strong like connection_reset "
        f"nor weak like a timeout)."
    )


@requires_bigquery
def test_live_unmapped_tls_failure_defaults_to_floor_not_elevated():
    """Fixture (d): exercises the default-low allowlist mechanism
    directly -- joins a synthetic tls_failure string against the real
    marts.dim_tls_failure_evidence table and confirms the join produces
    NULL (no match), so the CASE's COALESCE must resolve to exactly 0.45,
    never a value from any real tier."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COALESCE(dim.standalone_confidence, 0.45) AS resolved_confidence
        FROM (SELECT 'some_future_ooni_failure_string' AS tls_failure) AS synthetic
        LEFT JOIN `{PROJECT_ID}.marts.dim_tls_failure_evidence` AS dim
          ON dim.tls_failure = synthetic.tls_failure
    """
    row = next(client.query(query).result())
    assert row.resolved_confidence == pytest.approx(0.45), (
        "TD-71 regression: an unmapped tls_failure string must resolve "
        "to the 0.45 floor via COALESCE, not inherit any tier's elevated "
        "confidence -- the default-low allowlist is broken."
    )
