"""
Regression lock for TD-55's fix: the probe engine's own bogon verdict
(dns_failure = 'dns_bogon_error') must classify as BLOCKED with its
distinct provenance label ('dns.bogon_probe_reported'), and the features
layer must count BOTH bogon forms into dns_bogon_events.

Two layers of protection, deliberately:

1. Static SQL-text assertions (always run, zero credentials). CI's
   pytest job has no GCP credentials today (TD-39), so a lexical check
   on the two files the fix touched is the only guard that actually
   executes on every push. It catches the accidental-revert case
   directly -- someone removing or rewording the CASE arms.

2. Live-BigQuery behavioral assertions, gated behind RUN_BIGQUERY_TESTS=1
   like tests/test_acled_pressure_regimes_golden.py. These verify the
   materialized int.ooni_experiment_results actually classifies the
   probe-reported bogon rows as BLOCKED at 0.90 confidence and that the
   rows still exist at all (they numbered 9,046 when TD-55 landed).

The static assertions normalize whitespace so formatting-only edits
don't false-fail, but any semantic edit to the locked arms will trip
them -- which is the point: TD-55's investigation (whole-session
bogoning of public DoH/DoT resolvers while app DNS resolved normally)
is the evidence a future editor must re-engage before weakening this.
"""
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_RESULTS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "intermediate" / "int.ooni_experiment_results.sql"
)
PROTOCOL_DAILY_SIGNALS_SQL = (
    REPO_ROOT / "Bruin" / "assets" / "features" / "protocol_daily_signals.sql"
)

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"


def _normalized(path):
    return re.sub(r"\s+", " ", path.read_text())


def test_dns_bogon_error_maps_to_blocked_result_state():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert (
        "WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 'BLOCKED'" in sql
    ), (
        "TD-55 regression: the DNS branch of int.ooni_experiment_results.sql no "
        "longer maps the probe engine's own bogon verdict (dns_failure = "
        "'dns_bogon_error') to BLOCKED. See TD-55 before changing this arm."
    )


def test_dns_bogon_error_keeps_distinct_provenance_detail():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert (
        "WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 'dns.bogon_probe_reported'"
        in sql
    ), (
        "TD-55 regression: blocking_detail no longer carries the distinct "
        "'dns.bogon_probe_reported' provenance label for probe-reported bogons."
    )


def test_dns_bogon_error_keeps_regex_path_confidence():
    sql = _normalized(EXPERIMENT_RESULTS_SQL)
    assert (
        "WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 0.90" in sql
    ), (
        "TD-55 regression: the probe-reported bogon arm no longer scores 0.90 "
        "confidence (parity with the answer-regex bogon path)."
    )


def test_features_layer_counts_both_bogon_forms():
    sql = _normalized(PROTOCOL_DAILY_SIGNALS_SQL)
    assert (
        "COUNTIF(blocking_detail IN ('dns.bogon', 'dns.bogon_probe_reported')) AS dns_bogon_events"
        in sql
    ), (
        "TD-55 regression: features.protocol_daily_signals no longer counts "
        "both bogon forms ('dns.bogon' and 'dns.bogon_probe_reported') into "
        "dns_bogon_events."
    )


@requires_bigquery
def test_live_probe_reported_bogons_classify_blocked():
    from google.cloud import bigquery

    client = bigquery.Client(project=PROJECT_ID)
    query = f"""
        SELECT
            COUNT(*) AS total_rows,
            COUNTIF(result_state = 'BLOCKED') AS blocked_rows,
            COUNTIF(blocking_detail = 'dns.bogon_probe_reported') AS provenance_rows,
            COUNTIF(is_blocking_signal) AS blocking_signal_rows,
            COUNTIF(confidence_score = 0.90) AS full_confidence_rows
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE protocol = 'dns'
          AND LOWER(COALESCE(failure_reason, '')) = 'dns_bogon_error'
    """
    row = next(client.query(query).result())

    assert row.total_rows > 0, (
        "No probe-reported bogon rows exist at all -- either upstream data "
        "changed radically or the staging chain dropped them (TD-47/TD-55)."
    )
    for field in ("blocked_rows", "provenance_rows", "blocking_signal_rows", "full_confidence_rows"):
        assert getattr(row, field) == row.total_rows, (
            f"TD-55 regression (live): {field}={getattr(row, field)} but "
            f"total probe-reported bogon rows={row.total_rows}; every such row "
            "must classify BLOCKED / dns.bogon_probe_reported / 0.90."
        )
