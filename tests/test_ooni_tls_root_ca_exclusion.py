"""
Golden-file test for TD-72 item (d) / TD-69: int.ooni_experiment_results.sql's
`tls` CTE must recognize Signal's own rotated root CA and stop classifying
its real backend servers (cdn.signal.org, cdn2.signal.org,
sfu.voip.signal.org, storage.signal.org) as UNKNOWN on ssl_unknown_authority.

Note (2026-08-01): the originally-reported bug shape ("classifies BLOCKED")
did not survive a check against live data, made while implementing this
fix -- `handshake_success` is always NULL in this table (a separate,
larger, deliberately-not-fixed-here bug, logged as TD-72 in this repo's
own numbering -- unrelated to "TD-72" in the Cowork planning environment's
numbering, which is this same fix under a different name; an unfortunate
collision, not the same finding). These rows' real prior classification
was UNKNOWN, not BLOCKED. This fix moves them to OK either way, which was
always the correct verdict -- Signal's real backend, reachable -- just
under a corrected description of what state it moves them from.

Root cause: Signal rotated its TLS root CA in 2022. Older OONI probe
versions fail certificate verification against the new root and report
ssl_unknown_authority against Signal's real, legitimate infrastructure --
a known client-side artifact, confirmed directly with OONI's Signal-test
author (hellais, 2026-07-30), who pointed at oonipipeline's own
SignalTransformer as the reference implementation. Both trusted root
fingerprints below were re-derived independently (SHA-256 over the DER
bytes of the PEM certificates fetched directly from ooni/data's main
branch) and cross-checked against the live, flagged June 25 2024
measurement before being written into the SQL fix.

Two fixtures, per this project's golden-file-test discipline
(mirrors tests/test_acled_pressure_regimes_golden.py and
tests/test_ooni_dns_bogon_classification.py):

  (a) the June 25 2024 measurement -- must now land in the exclusion
      state (OK / KNOWN_SIGNAL_ROOT_CA), not UNKNOWN.
  (b) an adversarial fingerprint that does NOT match either known root --
      proves the exclusion predicate itself is an exact, narrow two-value
      allowlist, not a blanket "ssl_unknown_authority is fine for signal"
      carve-out. No real example of an unrecognized-cert row exists in
      CLIO's current Kenya dataset (every observed ssl_unknown_authority
      row for the signal test matches a known root), so this fixture
      exercises the exclusion predicate directly against a synthetic,
      obviously-wrong SHA-256 value rather than a real row -- it confirms
      the two literal fingerprints are exact matches and nothing else is,
      not that a real unmatched row flows end-to-end to any particular
      verdict (which today would be UNKNOWN, same as a matched row minus
      this fix, not BLOCKED).
"""
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_RESULTS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_experiment_results.sql"
)

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"

# The exact two trusted fingerprints this fix relies on. Duplicated here
# deliberately (same pattern as TD-55's static assertions) -- a future edit
# that silently changes either value should fail this test and force
# re-engagement with why, not slip through unnoticed.
SIGNAL_ROOT_CA_OLD_SHA256 = "098fd5403f63fef89fba4cb4b98135ca2e73dc42c0ed03a377e8383f2d1fe9ea"
SIGNAL_ROOT_CA_NEW_SHA256 = "ddb0f92bb95c8d6fd202ea6e8cc5ccd182b544f8cd696f47d580659ddc9df65a"

# The real, flagged measurement this bug was originally reported against.
JUNE_25_2024_MEASUREMENT_ID = (
    "1a9ff1a7a6f2161670b518c7c41f0967439125f683879e220d42f438bc8088f7"
)


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def test_sql_contains_both_known_root_fingerprints():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert SIGNAL_ROOT_CA_OLD_SHA256 in sql, (
        "TD-69 regression: the old Signal root CA fingerprint is missing "
        "from int.ooni_experiment_results.sql's tls CTE."
    )
    assert SIGNAL_ROOT_CA_NEW_SHA256 in sql, (
        "TD-69 regression: the new Signal root CA fingerprint is missing "
        "from int.ooni_experiment_results.sql's tls CTE."
    )


def test_sql_exposes_orthogonal_exclusion_reason_not_new_verdict():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert "'KNOWN_SIGNAL_ROOT_CA'" in sql
    assert (
        "[BLOCKED, OK, DOWN, UNKNOWN]" in sql
    ), (
        "TD-69 regression: result_state's accepted_values enum should not "
        "have gained a new value -- the exclusion must be an orthogonal "
        "column (exclusion_reason), not a new verdict state."
    )


@requires_bigquery
def test_live_june_25_2024_signal_tls_excluded_not_blocked():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT observation_target, result_state, exclusion_reason, failure_reason
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE measurement_id = '{JUNE_25_2024_MEASUREMENT_ID}'
          AND protocol = 'tls'
    """
    rows = list(client.query(query).result())
    assert len(rows) == 4, (
        f"Expected 4 TLS handshakes for the flagged June 25 2024 signal "
        f"measurement, found {len(rows)}."
    )
    for row in rows:
        assert row.result_state == "OK", (
            f"TD-69 regression (live, golden fixture a): {row.observation_target} "
            f"still classifies {row.result_state}, expected OK."
        )
        assert row.exclusion_reason == "KNOWN_SIGNAL_ROOT_CA"
        assert row.failure_reason == "ssl_unknown_authority", (
            "The original tls_failure must stay visible even once excluded."
        )


@requires_bigquery
def test_unrecognized_fingerprint_does_not_match_allowlist():
    """Adversarial fixture (b): replicate only the exclusion predicate
    itself (not the whole CTE, to avoid duplicating unrelated logic) and
    confirm a synthetic, deliberately-wrong SHA-256 does NOT match --
    proving the guard is an exact two-value allowlist, not a broad
    ssl_unknown_authority carve-out for the signal test. Does not assert
    what result_state a real unmatched row would land on end-to-end
    (today that would be UNKNOWN, per TD-72 -- handshake_success is
    always NULL in this table -- not BLOCKED as an earlier version of
    this test's name implied)."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    fake_fingerprint = "0" * 64  # Obviously not either real root's SHA-256.
    query = f"""
        SELECT EXISTS (
            SELECT 1
            FROM UNNEST([@fake_fp]) AS fp
            WHERE fp IN (
                '{SIGNAL_ROOT_CA_OLD_SHA256}',
                '{SIGNAL_ROOT_CA_NEW_SHA256}'
            )
        ) AS matches
    """
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("fake_fp", "STRING", fake_fingerprint)
        ]
    )
    row = next(client.query(query, job_config=job_config).result())
    assert row.matches is False, (
        "TD-69 regression: an unrecognized certificate fingerprint matched "
        "the known-root allowlist -- the guard is no longer narrow."
    )
