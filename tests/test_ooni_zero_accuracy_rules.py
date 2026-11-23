"""ADR-0017 (2026-11-22): OONI's current zero-accuracy rules, applied at
both measurement and observation level.

Static layer (always runs): the rules table holds the adopted rules with
conditions copied from ooni/backend fastpath/fastpath/core.py at commit
27f2b28, DNSCheck's unsupported-test branch is recorded but not adopted,
and both levels plus every observation-counting asset read the shared
match table. ADR-0018 (2026-11-23) adds OONI's two date-consistency
rules (GEN-F, GEN-O) for every test, decided in int.ooni_receive_time.

Live layer (RUN_BIGQUERY_TESTS=1): the figures the fix session verified on
2026-11-22. These are data-dependent: they hold for CLIO's historical
OONI backfill and would need re-deriving if that data were re-ingested.
"""
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS = REPO_ROOT / "Bruin" / "assets"
RULES_SQL = ASSETS / "marts" / "dims" / "dim_ooni_zero_accuracy_rules.sql"
MATCHES_SQL = ASSETS / "intermediate" / "int.ooni_zero_accuracy_measurements.sql"
CANDIDATE_SQL = ASSETS / "intermediate" / "int.ooni_measurement_verdicts_candidate.sql"
RESULTS_SQL = ASSETS / "intermediate" / "int.ooni_experiment_results.sql"
FACT_SQL = ASSETS / "marts" / "facts" / "fact_ooni_censorship_signals.sql"
WEEKLY_SQL = ASSETS / "features" / "ooni_weekly_signals.sql"

OONI_COMMIT = "27f2b28cd021c51a42ac6418fba44335d5de4ca8"
PROJECT_ID = "encoded-joy-485413-k5"

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def _body(path):
    """SQL after the @bruin header, whitespace-normalized."""
    return _normalized(path).split("@bruin */", 1)[1]


# ---------------------------------------------------------------------
# Static layer
# ---------------------------------------------------------------------

def test_rules_table_conditions_match_pinned_ooni_code():
    sql = _body(RULES_SQL)
    expected = [
        "'SIG-B2', 1, 'signal', '0.2.4', NULL, NULL, NULL, NULL, FALSE,",
        "'SIG-B3', 2, 'signal', NULL, '0.2.3', NULL, TIMESTAMP('2023-11-07 00:00:00'), NULL, FALSE,",
        "'SIG-B4', 3, 'signal', NULL, NULL, '0.2.2', TIMESTAMP('2022-10-19 00:00:00'), NULL, FALSE,",
        "'SIG-B5', 4, 'signal', NULL, NULL, NULL, TIMESTAMP('2023-05-02 00:00:00'), '3.17.2', FALSE,",
    ]
    for row in expected:
        assert row in sql, f"ADR-0017: rules table row drifted from the pinned OONI code: {row}"
    assert "'TOR-1' AS rule_id" in sql and "TRUE AS requires_no_targets" in sql
    assert sql.count(OONI_COMMIT) == 8, "every rule must cite the pinned ooni/backend commit"


def test_date_rules_adopted_for_every_test():
    """ADR-0018: GEN-F / GEN-O are adopted, cover every test ('*'), carry
    OONI's thresholds, and come after every scorer rule (order 101/102)."""
    sql = _body(RULES_SQL)
    assert "'2026-11-23.1', 'GEN-F', 101, '*'," in sql
    assert "'2026-11-23.1', 'GEN-O', 102, '*'," in sql
    gen_f = sql[sql.index("'GEN-F'"):sql.index("'GEN-O'")]
    gen_o = sql[sql.index("'GEN-O'"):]
    assert "NULL, TRUE, 'recv_time = strptime(msmt_uid[:22]" in gen_f and "delta < -3600" in gen_f
    assert "'DATE', 'GEN_F'" in gen_f
    assert "NULL, TRUE, 'Same function, elif branch: delta > 31536000" in gen_o
    assert "'DATE', 'GEN_O'" in gen_o
    assert "core.py:1634-1652" in gen_f and "core.py:1634-1652" in gen_o
    assert "'2026-11-22.1'" not in sql, "rules_version must be bumped on every row together"


def test_receive_time_applies_ooni_thresholds():
    sql = _body(ASSETS / "intermediate" / "int.ooni_receive_time.sql")
    assert "SAFE.PARSE_TIMESTAMP('%Y%m%d%H%M%E*S_', SUBSTR(measurement_uid, 1, 22))" in sql
    assert "STARTS_WITH(measurement_uid, '20') AND LENGTH(measurement_uid) >= 20" in sql
    assert "WHEN uid_delta_seconds < -3600 THEN 'GEN_F' WHEN uid_delta_seconds > 31536000 THEN 'GEN_O'" in sql
    assert "WHERE match_state = 'MATCHED'" in sql, "only unambiguous API matches may decide a band row"
    assert "ELSE 'UNDETERMINED'" in sql


def test_matches_asset_reads_date_rules_for_every_test():
    sql = _body(MATCHES_SQL)
    assert "ON r.test_name = m.test_name AND r.rule_stage = 'SCORE'" in sql
    assert (
        "FROM `{{ var.project_id }}.int.ooni_receive_time` AS rt JOIN rules AS r "
        "ON r.rule_stage = 'DATE' AND r.test_name = '*' AND r.date_rule_state = rt.date_rule_state"
    ) in sql
    header = _normalized(MATCHES_SQL).split("@bruin */", 1)[0]
    assert "WHERE adopted AND rule_stage = 'SCORE' AND test_name NOT IN ('signal', 'tor')" in header, (
        "the scan-restriction check must still hold scorer rules to signal and tor"
    )


def test_dnscheck_unsupported_branch_recorded_not_adopted():
    sql = _body(RULES_SQL)
    gen_u = sql[sql.index("'GEN-U'"):]
    assert "NULL, FALSE, 'OONI has no dnscheck scorer; not a quality judgement'" in gen_u, (
        "ADR-0017 Decision 4: GEN-U must stay adopted = FALSE. Adopting it would "
        "remove all DNSCheck evidence because OONI has no scorer for that test."
    )


def test_matches_asset_only_uses_adopted_rules():
    sql = _body(MATCHES_SQL)
    assert "FROM `{{ var.project_id }}.marts.dim_ooni_zero_accuracy_rules` WHERE adopted" in sql


def test_measurement_gate_checks_ooni_rules_first():
    sql = _normalized(CANDIDATE_SQL)
    idx_za = sql.index(
        "WHEN za.ooni_zero_accuracy_rule_id IS NOT NULL THEN 'DISCARDED_OONI_ZERO_ACCURACY'"
    )
    idx_dim = sql.index("WHEN dim.is_known_bad_version IS TRUE THEN 'DISCARDED_BAD_PROBE_VERSION'")
    assert idx_za < idx_dim, "OONI's current rules must be checked ahead of CLIO's own discards"
    assert (
        "WHEN probe_accuracy_gate IN ('DISCARDED_BAD_PROBE_VERSION', "
        "'DISCARDED_OONI_ZERO_ACCURACY') THEN NULL" in sql
    ), "a DISCARDED_OONI_ZERO_ACCURACY measurement must get a NULL verdict"


def test_observation_level_flags_without_changing_result_state():
    sql = _body(RESULTS_SQL)
    assert "u.result_state = 'BLOCKED' AND za.ooni_zero_accuracy_rule_id IS NULL AS is_blocking_signal" in sql
    assert "COALESCE( u.exclusion_reason, CONCAT('OONI_ZERO_ACCURACY:', za.ooni_zero_accuracy_rule_id) )" in sql, (
        "an existing exclusion_reason (KNOWN_SIGNAL_ROOT_CA) must win over the new one"
    )
    assert "LEFT JOIN `{{ var.project_id }}.int.ooni_zero_accuracy_measurements` AS za" in sql


def test_every_observation_counter_filters_flagged_rows():
    assert _body(FACT_SQL).rstrip().endswith("WHERE ooni_zero_accuracy_rule_id IS NULL;")
    weekly = _body(WEEKLY_SQL)
    blocked = weekly[weekly.index("blocked_weekly AS ("):weekly.index("combined AS (")]
    assert "AND ooni_zero_accuracy_rule_id IS NULL" in blocked


def test_no_other_asset_counts_int_experiment_results_directly():
    """Any new direct reader of int.ooni_experiment_results must apply the
    ADR-0017 filter itself, or read marts.fact_ooni_censorship_signals."""
    allowed = {
        "fact_ooni_censorship_signals.sql",  # the shared filter point
        "ooni_weekly_signals.sql",  # filters itself (tested above)
        "dim_country.sql",  # reads the country column only, counts nothing
        "int.ooni_experiment_results.sql",  # the table itself
    }
    readers = {
        p.name
        for p in ASSETS.rglob("*.sql")
        if re.search(r"(FROM|JOIN)\s+`[^`]*int\.ooni_experiment_results`", p.read_text())
        or "FROM `int.ooni_experiment_results`" in p.read_text()
    }
    assert readers <= allowed, f"unreviewed direct readers: {sorted(readers - allowed)}"


# ---------------------------------------------------------------------
# Live layer
# ---------------------------------------------------------------------

def _scalar(sql):
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    return next(iter(client.query(sql).result()))[0]


@requires_bigquery
def test_live_measurement_counts():
    n = _scalar(f"""
        SELECT COUNT(*) FROM `{PROJECT_ID}.int.ooni_measurement_verdicts`
        WHERE probe_accuracy_gate = 'DISCARDED_OONI_ZERO_ACCURACY'""")
    # ADR-0017: signal 15,302 + tor 2. ADR-0018 (2026-11-23): + 640 measurements
    # excluded by the date rules only (643 meet GEN-F/GEN-O; 3 signal ones were
    # already excluded by a scorer rule).
    assert n == 15302 + 2 + 640


@requires_bigquery
def test_live_date_rule_states():
    """ADR-0018 figures on 2026-11-23: 527 decided by archive hour, 116 GEN-F
    decided by measurement_uid, none left UNDETERMINED."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    rows = {
        (r.date_rule_state, r.receive_time_source): r.n
        for r in client.query(f"""
            SELECT date_rule_state, receive_time_source, COUNT(*) n
            FROM `{PROJECT_ID}.int.ooni_receive_time`
            WHERE date_rule_state != 'NEITHER' GROUP BY 1, 2""").result()
    }
    assert rows == {
        ("GEN_F", "ARCHIVE_HOUR"): 480,
        ("GEN_O", "ARCHIVE_HOUR"): 47,
        ("GEN_F", "MEASUREMENT_UID"): 116,
    }


@requires_bigquery
def test_live_whatsapp_future_case_excluded():
    n = _scalar(f"""
        SELECT COUNT(*) FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.int.ooni_receive_time` rt USING (measurement_id)
        WHERE rt.measurement_uid = '20241011071247.739797_KE_whatsapp_f56040603deb14ed'
          AND v.probe_accuracy_gate = 'DISCARDED_OONI_ZERO_ACCURACY'
          AND v.ooni_zero_accuracy_rule_id = 'GEN-F'""")
    assert n == 1


@requires_bigquery
def test_live_signal_0_2_4_has_no_verdict():
    n = _scalar(f"""
        SELECT COUNT(*) FROM `{PROJECT_ID}.int.ooni_measurement_verdicts` v
        JOIN `{PROJECT_ID}.stg.ooni_measurement_summary` s USING (measurement_id)
        WHERE s.test_name = 'signal' AND s.test_version = '0.2.4' AND v.ooni_verdict IS NOT NULL""")
    assert n == 0


@requires_bigquery
def test_live_tls_blocked_counted():
    n = _scalar(f"""
        SELECT COUNT(*) FROM `{PROJECT_ID}.marts.fact_ooni_censorship_signals`
        WHERE protocol = 'tls' AND result_state = 'BLOCKED'""")
    assert n == 271


@requires_bigquery
def test_live_flagged_observations_never_counted():
    n = _scalar(f"""
        SELECT COUNT(*) FROM `{PROJECT_ID}.marts.fact_ooni_censorship_signals` f
        JOIN `{PROJECT_ID}.int.ooni_zero_accuracy_measurements` z USING (measurement_id)""")
    assert n == 0
