"""
Golden-file regression tests for intelligence.acled_pressure_regimes (TD-08,
ADR-0002 step (d), testing-strategy.md Priority 1).

These assert the already-backfill-confirmed output for two known incident
windows (Finance Bill 2024, Jan-Feb 2008 post-election violence) against a
recorded golden snapshot. This is a drift check against materialized
BigQuery output, not a rerun of the SQL logic against a frozen input
snapshot -- see the design note in the PR/commit for why, and what a true
rerun-based regression test would additionally require.

Skipped unless RUN_BIGQUERY_TESTS=1 is set, since running requires live
GCP credentials that aren't wired into CI yet.
"""
import json
import os
from pathlib import Path

import pytest

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "acled_regimes_golden"
FIELDS = ["primary_regime", "confidence_level", "transition_detected", "transition_type", "previous_regime"]


def _load_golden(name):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def _fetch_actual(client, country, start, end):
    from google.cloud import bigquery

    query = f"""
        SELECT week_start_date, {", ".join(FIELDS)}
        FROM `{PROJECT_ID}.intelligence.acled_pressure_regimes`
        WHERE country = @country
          AND week_start_date BETWEEN @start AND @end
        ORDER BY week_start_date
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("start", "DATE", start),
        bigquery.ScalarQueryParameter("end", "DATE", end),
    ])
    rows = client.query(query, job_config=job_config).result()
    return {row.week_start_date.isoformat(): {f: getattr(row, f) for f in FIELDS} for row in rows}


def _assert_matches_golden(actual, golden):
    for week, expected in golden.items():
        assert week in actual, f"missing week {week} in live output"
        for field, expected_value in expected.items():
            assert actual[week][field] == expected_value, (
                f"{week}.{field}: expected {expected_value!r}, got {actual[week][field]!r}"
            )


@requires_bigquery
def test_finance_bill_2024_golden_window():
    from google.cloud import bigquery

    golden = _load_golden("finance_bill_2024.json")
    client = bigquery.Client(project=PROJECT_ID)
    actual = _fetch_actual(client, "Kenya", "2024-05-04", "2024-07-20")
    _assert_matches_golden(actual, golden)


@requires_bigquery
def test_post_election_2008_golden_window():
    from google.cloud import bigquery

    golden = _load_golden("post_election_2008.json")
    client = bigquery.Client(project=PROJECT_ID)
    actual = _fetch_actual(client, "Kenya", "2008-01-05", "2008-03-01")
    _assert_matches_golden(actual, golden)
