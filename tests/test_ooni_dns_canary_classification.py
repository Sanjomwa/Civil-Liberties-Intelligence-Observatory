"""
Regression lock for TD-68: int.ooni_experiment_results.sql's DNS bogon
regex must not fire on Signal's own client-side canary hostname
(uptime.signal.org, designed to always resolve to loopback as a benign
health check) or on any non-A/AAAA record shape.

Before this fix, CLIO's flagship "177 same-day DNS-layer interference
signals on June 25 2024, concentrated on Signal" claim was 100%
uptime.signal.org resolving to 127.0.0.1 -- confirmed live, retracted
2026-07-29, and independently confirmed benign by OONI's own Signal-test
author (hellais) on 2026-07-30.

This is deliberately a separate file from test_ooni_dns_bogon_classification.py
(TD-55's regression lock): TD-55 locks the *different*, unrelated
`dns_failure = 'dns_bogon_error'` probe-reported path, which this fix does
not touch and must keep passing unchanged.

Two layers, same pattern as TD-55's test:

1. Static SQL-text assertions (always run, zero credentials).
2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1.
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


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def test_bogon_regex_requires_a_or_aaaa_answer_type():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert "answer_type IN ('A', 'AAAA')" in sql, (
        "TD-68 regression: the DNS bogon classification no longer guards on "
        "answer_type, which would let a CNAME target starting with fc/fd/fe80 "
        "false-positive as a bogon."
    )


def test_bogon_regex_excludes_signal_canary_hostname():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert "test_name = 'signal' AND hostname = 'uptime.signal.org'" in sql, (
        "TD-68 regression: the DNS bogon classification no longer excludes "
        "Signal's uptime.signal.org canary hostname -- this hostname always "
        "resolves to loopback by design and is not interference."
    )


@requires_bigquery
def test_live_signal_canary_hostname_never_classifies_bogon():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE protocol = 'dns'
          AND test_name = 'signal'
          AND observation_target = 'uptime.signal.org'
          AND blocking_detail = 'dns.bogon'
    """
    row = next(client.query(query).result())
    assert row.n == 0, (
        f"TD-68 regression (live): {row.n} uptime.signal.org rows still "
        "classify as dns.bogon; expected 0."
    )


@requires_bigquery
def test_live_finance_bill_june_25_2024_dns_count_is_zero():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE protocol = 'dns'
          AND test_name = 'signal'
          AND country = 'KE'
          AND measurement_date = '2024-06-25'
          AND blocking_detail = 'dns.bogon'
    """
    row = next(client.query(query).result())
    assert row.n == 0, (
        f"TD-68 regression (live): the retracted '177 same-day DNS signals' "
        f"claim should reproduce as 0 post-fix; got {row.n}."
    )


@requires_bigquery
def test_live_dns_bogon_error_path_still_fires_unaffected():
    """TD-55's probe-reported bogon path is a different signal; TD-68 must
    not have touched it. Cross-check with a live query rather than trust
    the static assertion alone."""
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT COUNT(*) AS n
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE protocol = 'dns'
          AND blocking_detail = 'dns.bogon_probe_reported'
          AND result_state = 'BLOCKED'
    """
    row = next(client.query(query).result())
    assert row.n > 0, (
        "TD-68 regression (live): TD-55's probe-reported bogon rows "
        "(dns.bogon_probe_reported) disappeared or stopped classifying "
        "BLOCKED -- TD-68 should not have touched this path at all."
    )
