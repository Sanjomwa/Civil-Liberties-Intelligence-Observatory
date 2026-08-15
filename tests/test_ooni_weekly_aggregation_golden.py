"""
Golden-file regression test for int.ooni_experiment_results, aggregated to
weekly grain per test_name (TD-87 Phase 0).

Freezes a known-good weekly snapshot of the Finance Bill 2024 window
(2024-05-11 to 2024-07-13), taken AFTER TD-80 (TCP `timed_out`
misclassification) and TD-82 (dead `error_results` COUNTIF renamed to
`unknown_results`) were both fixed and materialized -- so this fixture
reflects corrected classification data, not the pre-fix state. It is meant
to be the baseline any future OONI classification change gets diffed
against.

Week boundary matches ACLED's own Saturday-anchored week
(DATE_TRUNC(measurement_date, WEEK(SATURDAY))), the same anchor established
for the regime_* join in fact_country_pressure_daily.sql.

Same pattern as test_acled_pressure_regimes_golden.py: a drift check against
materialized BigQuery output, not a rerun of the classification SQL against
a frozen input snapshot. Skipped unless RUN_BIGQUERY_TESTS=1 is set.

NOTE (TD-91, 2026-08-16): the fixture has only 5 test_names (dnscheck,
psiphon, signal, telegram, whatsapp), not CLIO's full live set of 6 --
`tor` is absent. This is NOT a Finance-Bill-window-specific gap; verified
live that `tor` has ZERO rows in int.ooni_experiment_results across its
ENTIRE history, and zero rows in every one of its four underlying
protocol-observation staging tables (stg.ooni_{dns,tcp,tls,http}_
observations). Structural, not incidental: tor's own test_keys nests its
tcp_connect/tls_handshakes/queries/requests arrays one level deeper,
inside `targets` (a dict keyed by opaque "ip:port" identifiers), not at
the top level the way DNS/TCP/TLS/HTTP's exploding UNNEST(JSON_QUERY_
ARRAY(raw_test_keys, '$.tcp_connect')) (etc.) pattern expects -- the same
`targets`-is-dict-keyed blocker already flagged for TD-87 Phase 1's own
stg.ooni_measurement_summary (tor's verdict extraction there is also
deliberately not implemented, for the same underlying reason). This is
not an oversight in this fixture -- it is a faithful reflection of a real
CLIO-wide gap, not a bug this test masks.
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
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "ooni_weekly_golden"
FIELDS = ["total_experiment_results", "blocked_results", "down_results", "unknown_results", "blocking_signal_count"]


def _load_golden(name):
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def _fetch_actual(client, country, start, end):
    from google.cloud import bigquery

    query = f"""
        SELECT
          CAST(DATE_TRUNC(measurement_date, WEEK(SATURDAY)) AS STRING) AS week_start_date,
          test_name,
          COUNT(*) AS total_experiment_results,
          COUNTIF(result_state = 'BLOCKED') AS blocked_results,
          COUNTIF(result_state = 'DOWN') AS down_results,
          COUNTIF(result_state = 'UNKNOWN') AS unknown_results,
          COUNTIF(is_blocking_signal) AS blocking_signal_count
        FROM `{PROJECT_ID}.int.ooni_experiment_results`
        WHERE country = @country
          AND measurement_date BETWEEN @start AND @end
        GROUP BY week_start_date, test_name
    """
    job_config = bigquery.QueryJobConfig(query_parameters=[
        bigquery.ScalarQueryParameter("country", "STRING", country),
        bigquery.ScalarQueryParameter("start", "DATE", start),
        bigquery.ScalarQueryParameter("end", "DATE", end),
    ])
    rows = client.query(query, job_config=job_config).result()
    actual = {}
    for row in rows:
        actual.setdefault(row.week_start_date, {})[row.test_name] = {
            f: getattr(row, f) for f in FIELDS
        }
    return actual


def _assert_matches_golden(actual, golden):
    for week, tests in golden.items():
        assert week in actual, f"missing week {week} in live output"
        for test_name, expected in tests.items():
            assert test_name in actual[week], f"missing test_name {test_name} in week {week}"
            for field, expected_value in expected.items():
                assert actual[week][test_name][field] == expected_value, (
                    f"{week}.{test_name}.{field}: expected {expected_value!r}, "
                    f"got {actual[week][test_name][field]!r}"
                )


@requires_bigquery
def test_finance_bill_2024_weekly_golden():
    from google.cloud import bigquery

    golden = _load_golden("finance_bill_2024.json")
    client = bigquery.Client(project=PROJECT_ID)
    actual = _fetch_actual(client, "KE", "2024-05-11", "2024-07-13")
    _assert_matches_golden(actual, golden)
