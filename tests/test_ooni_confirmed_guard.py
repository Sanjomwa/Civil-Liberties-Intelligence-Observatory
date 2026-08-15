"""
Static test for TD-87 Phase 2's three-layer CONFIRMED guard, layer 3 of 3
(see int.ooni_measurement_verdicts_candidate.sql's header for layer 1,
the structural CTE isolation, and
int.ooni_measurement_verdicts_confirmed_guard.sql for layer 2, the
DAG-level runtime check).

TD-91 (2026-08-16): repointed from int.ooni_measurement_verdicts.sql to
int.ooni_measurement_verdicts_candidate.sql -- the candidate/publish
split moved all real CONFIRMED-producing logic into the candidate file;
int.ooni_measurement_verdicts.sql is now a trivial
`SELECT * FROM candidate` with no CASE logic of its own to check.

OONI's CONFIRMED verdict is structurally possible only for
test_name = 'web_connectivity' (fingerprint-matched block pages /
censorship-associated DNS answers) -- never for Signal, WhatsApp,
Telegram, Tor, or any other test. This test reads int.ooni_measurement_
verdicts_candidate.sql's own source text (not live BigQuery) and
asserts, by construction:

  1. The literal SQL string 'CONFIRMED' appears exactly once, and only in
     the exact gate `WHEN fingerprint_match_id IS NOT NULL THEN 'CONFIRMED'`
     -- so CONFIRMED can only ever be produced via fingerprint_match_id.
  2. fingerprint_match_id is assigned (`AS fingerprint_match_id`) exactly
     once in the whole file, inside the wc_confirmed CTE.
  3. That CTE's own body filters its source to
     `WHERE test_name = 'web_connectivity'` -- not a bare
     `CASE WHEN test_name = 'web_connectivity'` predicate mixed into a
     shared, unfiltered CTE.
  4. No text before that CTE's definition ever assigns fingerprint_match_id
     -- it cannot be computed anywhere outside the web_connectivity-
     filtered CTE.

fingerprint_match_id is always NULL this phase (real fingerprint matching
against ooni/blocking-fingerprints is Phase 5, out of scope here) -- this
test locks in the *structure* now, so Phase 5 has one safe, pre-isolated
place to add real matching logic later, and any future edit that moves
CONFIRMED-producing logic outside that structure fails this test
immediately, without needing live BigQuery access.

Modeled on the static-half pattern in
tests/test_ooni_tls_failure_evidence_tiering.py (read that file first).
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
VERDICTS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_measurement_verdicts_candidate.sql"
)


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def test_confirmed_literal_appears_only_in_fingerprint_gated_branch():
    sql = _normalized(VERDICTS_SQL)
    assert "WHEN fingerprint_match_id IS NOT NULL THEN 'CONFIRMED'" in sql, (
        "TD-87 Phase 2 guard regression: 'CONFIRMED' must only ever be "
        "produced by the fingerprint_match_id IS NOT NULL branch of the "
        "ooni_verdict CASE."
    )
    occurrences = re.findall(r"'CONFIRMED'", sql)
    assert len(occurrences) == 1, (
        f"TD-87 Phase 2 guard regression: expected exactly one SQL string "
        f"literal 'CONFIRMED' in int.ooni_measurement_verdicts_candidate.sql, found "
        f"{len(occurrences)} -- a second occurrence could produce CONFIRMED "
        f"via a path this guard doesn't check."
    )


def test_fingerprint_match_id_assigned_exactly_once():
    raw = VERDICTS_SQL.read_text()
    assignments = re.findall(r"AS fingerprint_match_id\b", raw)
    assert len(assignments) == 1, (
        f"TD-87 Phase 2 guard regression: expected exactly one "
        f"'AS fingerprint_match_id' assignment in "
        f"int.ooni_measurement_verdicts_candidate.sql, found {len(assignments)} -- "
        f"a second assignment site could populate it outside the "
        f"web_connectivity-filtered CTE."
    )


def test_fingerprint_match_id_only_defined_inside_web_connectivity_filtered_cte():
    raw = VERDICTS_SQL.read_text()

    cte_match = re.search(r"wc_confirmed AS \(\s*(.*?)\n\),?\n", raw, re.DOTALL)
    assert cte_match, (
        "wc_confirmed CTE not found in int.ooni_measurement_verdicts_candidate.sql -- "
        "this test's structural assumptions no longer match the file."
    )
    cte_body = cte_match.group(1)

    assert "AS fingerprint_match_id" in cte_body, (
        "wc_confirmed CTE no longer defines fingerprint_match_id -- "
        "either the guard moved (update this test) or the structural "
        "isolation broke."
    )
    assert re.search(r"WHERE\s+test_name\s*=\s*'web_connectivity'", cte_body), (
        "TD-87 Phase 2 guard regression: wc_confirmed's own source must be "
        "filtered to WHERE test_name = 'web_connectivity' -- a bare "
        "CASE WHEN test_name = 'web_connectivity' predicate mixed into a "
        "shared, unfiltered CTE would not provide the same structural "
        "guarantee."
    )

    # Strip the /* @bruin ... @bruin */ header comment block before
    # checking -- it discusses fingerprint_match_id in prose (documenting
    # this exact guard), which is not a SQL assignment and must not
    # trip this check.
    header_end = raw.find("@bruin */")
    assert header_end != -1, "Could not find end of @bruin header comment"
    sql_before_cte = raw[header_end + len("@bruin */") : cte_match.start()]
    assert "AS fingerprint_match_id" not in sql_before_cte, (
        "TD-87 Phase 2 guard regression: fingerprint_match_id must not be "
        "assigned anywhere before the web_connectivity-filtered "
        "wc_confirmed CTE is defined."
    )
