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

EXTENDED (weekly OONI aggregation relay session, 2026-08-15): the fixture
file was restructured from one flat week->test_name mapping into two
top-level keys, `result_state_weekly` (the original content, unchanged
values, renamed only) and `ooni_verdict_weekly` (new -- the ANOMALOUS/
ooni_verdict side, from int.ooni_measurement_verdicts, same window, same
Saturday anchor, same skip-gate pattern). Extending in place rather than
adding a sibling file was chosen because both sides describe the exact
same window and the same underlying grain-compatibility finding (test_name
is native to both source tables) -- one file, one drift check, two
independently-verified column groups, matching features.ooni_weekly_
signals' own choice to carry both series side by side in one row rather
than as two separate tables. ooni_verdict_weekly's total_scored_
measurements excludes NULL ooni_verdict rows (NOT_IMPLEMENTED tor +
DISCARDED_BAD_PROBE_VERSION signal rows), per this build's own Task B
denominator -- see reports.md's 2026-08-15 entry for the 17.9%-vs-15.1%
denominator correction this produced for signal specifically.

RE-FROZEN (TD-93, 2026-08-15, same day): `ooni_verdict_weekly`'s `signal`
values changed after TD-93's fix (int.ooni_measurement_verdicts_candidate.sql
now routes signal's NXDOMAIN failures against two out-of-spec legacy
hostnames to FAILED instead of ANOMALOUS -- see that asset's header).
`total_scored_measurements` is unchanged for every week/test_name (the
fix only moves rows between ANOMALOUS and FAILED, not into or out of the
scored population). Only `signal`'s `anomalous_count` moved -- every
other test_name's numbers in this fixture are byte-for-byte unchanged,
confirmed via a full before/after diff before re-freezing, not assumed.
Real deltas, Finance Bill window (signal anomalous_count, before -> after):
2024-05-11: 85->13, 05-18: 110->7, 05-25: 109->4, 06-01: 87->1,
06-08: 65->1, 06-15: 78->4, 06-22: 90->31, 06-29: 9->6, 07-06: 20->10,
07-13: 1->1 (unchanged that week). Window total: 1,844 -> 1,268 (-576,
-31.2%). See reports.md's 2026-08-15 TD-93 entry for the full
methodology and the external-validation matched-pair check this fix is
based on.

RE-FROZEN (TD-101 Phase 3, 2026-08-20): `ooni_verdict_weekly`'s `dnscheck`
values changed after int.ooni_measurement_verdicts_candidate.sql's
narrow bogon carve-out (dns_bogon_error keeps ANOMALOUS; every other
non-NULL dnscheck_bootstrap_failure value newly routes to FAILED instead
-- see that asset's header for the full TD-55/TD-101 reasoning, and
tests/test_ooni_dnscheck_bootstrap_failed_classification.py for this
fix's own static+live regression lock). `total_scored_measurements` is
unchanged for every week (same TD-93 precedent: this fix only moves rows
between ANOMALOUS and FAILED, both non-NULL, never into or out of the
scored population). Only `dnscheck`'s `anomalous_count` moved -- every
other test_name's numbers in this fixture are unchanged, confirmed via a
live requery before re-freezing, not assumed. Real deltas, Finance Bill
window (dnscheck anomalous_count, before -> after): 2024-05-11: 89->0,
05-18: 68->0, 05-25: 1->0, 06-01: 3->0, 06-08: 2->0, 06-15: 36->0,
06-22: 34->0, 06-29: 24->0, 07-06: 226->0, 07-13: 10->0. Window total:
493 -> 0 (-493, -100%). Worth stating plainly, not just as a number: the
entire flagship Finance Bill 2024 window contained ZERO real
dns_bogon_error detections for dnscheck -- every one of the 493
previously-ANOMALOUS dnscheck rows in this window was one of the other
five bootstrap-failure values, all investigated this session and found
probe/test-infrastructure-artifact-shaped, not manipulation-shaped (see
int.ooni_measurement_verdicts_candidate.sql's header and reports.md for
the full investigation, including the permanently-dead/typo'd DoH/DoT
target hostnames -- e.g. doh.appliedprivacy.ne -- that dominate
dns_nxdomain_error, this window's largest single non-bogon contributor
at 07-06's 226). This is not a retraction of any prior flagship finding
-- no deliverable document or incident report ever cited a dnscheck
ANOMALOUS figure for this window (confirmed by grep across streamlit/
before this fix, see reports.md) -- it corrects a structural
misclassification (probe/test-infrastructure noise counted as
"interference-consistent") that predates this session and was never
part of the flagship narrative to begin with.

RE-FROZEN (TD-105 build, 2026-08-22): `ooni_verdict_weekly`'s `whatsapp`
values changed after int.ooni_measurement_verdicts_candidate.sql removed
whatsapp_endpoints_blocked_count > 0 and whatsapp_endpoints_dns_
inconsistent_count > 0 from the whatsapp OR-chain entirely (not
thresholded) -- see that asset's header and
tests/test_ooni_whatsapp_endpoints_blocked_count_removed.py for this
fix's own static+live regression lock. `total_scored_measurements` is
unchanged for every week (same TD-93/TD-101 precedent: this fix only
moves rows out of ANOMALOUS into OK, never into or out of the scored
population). Only `whatsapp`'s `anomalous_count` moved -- every other
test_name's numbers in this fixture are unchanged, confirmed via a live
requery before re-freezing, not assumed. Real deltas, Finance Bill
window (whatsapp anomalous_count, before -> after): 2024-05-11: 25->24,
05-18: 17->15, 05-25: 2->2 (unchanged), 06-01: 5->5 (unchanged), 06-08:
5->5 (unchanged), 06-15: 12->10, 06-22: 65->48, 06-29: 29->20, 07-06:
11->7, 07-13: 2->2 (unchanged). Window total: 173 -> 138 (-35, -20.2%).
The flagship 06-22 "Parliament stormed" week keeps a clear, real spike
after re-freezing (48 anomalous out of 1,217 scored, still far above
every other week's baseline of 2-24) -- this fix removes noise, it does
not erase the flagship signal. See reports.md's 2026-08-21 and
2026-08-22 TD-105 session entries for the full methodology and the two
matched-pair verification sessions this fix is based on.

RE-FROZEN (TD-102 build, 2026-08-22): `ooni_verdict_weekly`'s `signal`
values changed after TWO SEPARATE fixes landed for signal probe
versions 0.2.2 (version-wide, marts.dim_ooni_probe_version_accuracy)
and 0.2.3-post-2023-11-06T16:00:00 (date-gated, inline in
int.ooni_measurement_verdicts_candidate.sql's probe_accuracy_gate) --
see tests/test_ooni_signal_probe_version_discard.py for both fixes'
own static+live regression lock. UNLIKE every prior re-freeze in this
fixture's history (TD-93, TD-101, TD-105), `total_scored_measurements`
is NOT held constant this time -- both TD-102 fixes DISCARD rows
(route them to NULL, excluded from the scored population entirely),
they do not just move rows between ANOMALOUS/FAILED/OK within it. Real
deltas, Finance Bill window (signal total_scored_measurements /
anomalous_count, before -> after): 2024-05-11: 279/13 -> 197/3, 05-18:
298/7 -> 189/1, 05-25: 321/4 -> 214/2, 06-01: 292/1 -> 205/0, 06-08:
340/1 -> 275/0, 06-15: 497/4 -> 423/4 (anomalous_count unchanged this
week, denominator still shrank), 06-22: 1058/31 -> 998/30, 06-29:
784/6 -> 779/4, 07-06: 698/10 -> 688/10 (anomalous_count unchanged,
denominator still shrank), 07-13: 85/1 -> 85/1 (fully unchanged --
zero 0.2.2/0.2.3 rows in this specific week). Window totals:
scored 4,652 -> 4,053 (-599, -12.9%), anomalous 78 -> 55 (-23, -29.5%)
-- the -23 anomalous delta matches TD-102's own verification session's
independently-computed window-impact estimate exactly. Every other
test_name's numbers in this fixture are unchanged, confirmed via a
live requery before re-freezing, not assumed. See reports.md's
2026-08-22 TD-102 session entries (characterization, verification,
build) for the full methodology.

RESCOPED (TD-102 rescoping build, 2026-08-22, same day): the paragraph
above's description of the 0.2.2 mechanism as "version-wide" is now
STALE -- a later session that same day found the version-wide premise
did not hold against the real population (only 415/2,200, 18.9%, of
0.2.2 rows are actually signal_backend_status='blocked'; the other
1,785 are genuine, OONI-agreed 'ok' rows) and narrowed 0.2.2's fix to
an inline signal_backend_status='blocked' predicate in
int.ooni_measurement_verdicts_candidate.sql (marts.
dim_ooni_probe_version_accuracy's 0.2.2 row is back to
is_known_bad_version=FALSE). THE NUMBERS ABOVE REMAIN CORRECT AND WERE
NOT RE-FROZEN -- verified live, not assumed: every one of the Finance
Bill window's 71 0.2.2 rows happens to be signal_backend_status=
'blocked', so the rescoped, narrower predicate discards the exact same
rows the version-wide predicate did, within this specific window. The
1,785-row restoration the rescoping actually accomplishes is real but
lands entirely outside this window, elsewhere in 0.2.2's broader date
range -- do not read the unchanged numbers above as evidence the
rescoping had no effect. See reports.md's 2026-08-22 TD-102 rescoping
session entry for the full account.
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
RESULT_STATE_FIELDS = ["total_experiment_results", "blocked_results", "down_results", "unknown_results", "blocking_signal_count"]
OONI_VERDICT_FIELDS = ["total_scored_measurements", "anomalous_count"]


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
            f: getattr(row, f) for f in RESULT_STATE_FIELDS
        }
    return actual


def _fetch_actual_ooni_verdict(client, country, start, end):
    from google.cloud import bigquery

    query = f"""
        SELECT
          CAST(DATE_TRUNC(measurement_date, WEEK(SATURDAY)) AS STRING) AS week_start_date,
          test_name,
          COUNT(*) AS total_scored_measurements,
          COUNTIF(ooni_verdict = 'ANOMALOUS') AS anomalous_count
        FROM `{PROJECT_ID}.int.ooni_measurement_verdicts`
        WHERE country = @country
          AND ooni_verdict IS NOT NULL
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
            f: getattr(row, f) for f in OONI_VERDICT_FIELDS
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

    golden = _load_golden("finance_bill_2024.json")["result_state_weekly"]
    client = bigquery.Client(project=PROJECT_ID)
    actual = _fetch_actual(client, "KE", "2024-05-11", "2024-07-13")
    _assert_matches_golden(actual, golden)


@requires_bigquery
def test_finance_bill_2024_weekly_golden_ooni_verdict():
    from google.cloud import bigquery

    golden = _load_golden("finance_bill_2024.json")["ooni_verdict_weekly"]
    client = bigquery.Client(project=PROJECT_ID)
    actual = _fetch_actual_ooni_verdict(client, "KE", "2024-05-11", "2024-07-13")
    _assert_matches_golden(actual, golden)
