"""
TD-136 Option E acceptance tests for the shadow columns in
features.acled_pressure_signals (shadow_global_conditions_valid,
shadow_protest_pressure_z, shadow_violence_pressure_z, shadow_suppression_z).

These are observation-only columns: a header-spec-correct, global-flags-only
validity gate run alongside the existing (unchanged, still-buggy)
signal_valid gate, for comparison during an observation period before any
TD-136 Option A cutover decision. Not consumed by intelligence.
acled_pressure_regimes or any downstream mart.

Skipped unless RUN_BIGQUERY_TESTS=1 is set, matching
tests/test_acled_pressure_regimes_golden.py's opt-in pattern.
"""
import os

import pytest

requires_bigquery = pytest.mark.skipif(
    os.environ.get("RUN_BIGQUERY_TESTS") != "1",
    reason="Set RUN_BIGQUERY_TESTS=1 to run tests against live BigQuery data",
)

PROJECT_ID = "encoded-joy-485413-k5"

# Established 2026-09-21 against live materialized data. A change to either
# number is a drift signal on the observation baseline this build sets, not
# necessarily a bug -- but it must be understood before proceeding.
KENYA_TOTAL_ROWS = 1523
KENYA_FLIPPED_ROWS = 564

# 2007-11-24 through 2008-01-12: the 8-week run immediately preceding the
# Jan-Feb 2008 post-election violence window, all signal_valid = FALSE under
# the current (buggy) flat gate. Confirmed live (2026-09-21): all three live
# z-scores are NULL for all 8 weeks. On the shadow side, NOT all three are
# uniformly un-suppressed -- shadow_suppression_z stays NULL throughout
# (still correctly gated by its own sparse_suppression_baseline_flag, a
# per-family flag TD-136's fix does not touch), and shadow_protest_pressure_z
# is NULL for the first week only (2007-11-24, same per-family reason).
# Only shadow_violence_pressure_z is non-NULL across the full 8 weeks.
PRE_WINDOW_START = "2007-11-24"
PRE_WINDOW_END = "2008-01-12"
PRE_WINDOW_WEEK_COUNT = 8
PROTEST_STILL_NULL_WEEKS = {"2007-11-24"}


def _client():
    from google.cloud import bigquery

    return bigquery.Client(project=PROJECT_ID)


@requires_bigquery
def test_superset_invariant_holds_for_every_country():
    query = f"""
        SELECT
          country,
          COUNT(*) AS total_rows,
          COUNTIF(signal_valid = FALSE AND shadow_global_conditions_valid = TRUE) AS flipped_rows,
          COUNTIF(
            (protest_pressure_z IS NOT NULL AND (shadow_protest_pressure_z IS NULL OR shadow_protest_pressure_z != protest_pressure_z))
            OR (violence_pressure_z IS NOT NULL AND (shadow_violence_pressure_z IS NULL OR shadow_violence_pressure_z != violence_pressure_z))
            OR (suppression_z IS NOT NULL AND (shadow_suppression_z IS NULL OR shadow_suppression_z != suppression_z))
          ) AS superset_invariant_violations
        FROM `{PROJECT_ID}.features.acled_pressure_signals`
        GROUP BY country
        ORDER BY country
    """
    rows = list(_client().query(query).result())
    assert rows, "expected at least one country in features.acled_pressure_signals"
    for row in rows:
        assert row.superset_invariant_violations == 0, (
            f"{row.country}: {row.superset_invariant_violations} superset-invariant "
            f"violation(s) -- a shadow z-score is NULL or differs where the live "
            f"column is non-NULL"
        )


@requires_bigquery
def test_shadow_global_conditions_valid_never_true_when_a_global_flag_fires():
    query = f"""
        SELECT COUNT(*) AS violations
        FROM `{PROJECT_ID}.features.acled_pressure_signals`
        WHERE shadow_global_conditions_valid = TRUE
          AND (low_event_density_flag OR high_methodology_risk_flag)
    """
    rows = list(_client().query(query).result())
    assert rows[0].violations == 0, (
        "shadow_global_conditions_valid is TRUE in at least one row where a "
        "global validity flag fires -- guard against a careless rewrite of "
        "the shadow gate"
    )


@requires_bigquery
def test_pre_window_null_pattern_matches_observed_shape():
    query = f"""
        SELECT
          week_start_date,
          protest_pressure_z, violence_pressure_z, suppression_z,
          shadow_protest_pressure_z, shadow_violence_pressure_z, shadow_suppression_z
        FROM `{PROJECT_ID}.features.acled_pressure_signals`
        WHERE country = "Kenya"
          AND week_start_date BETWEEN "{PRE_WINDOW_START}" AND "{PRE_WINDOW_END}"
        ORDER BY week_start_date
    """
    rows = list(_client().query(query).result())
    assert len(rows) == PRE_WINDOW_WEEK_COUNT, (
        f"expected {PRE_WINDOW_WEEK_COUNT} weeks in {PRE_WINDOW_START}..{PRE_WINDOW_END}, "
        f"got {len(rows)}"
    )
    for row in rows:
        week = row.week_start_date.isoformat()

        # Live side: all three z-scores are NULL for every week in this range
        # (signal_valid = FALSE throughout, under the current flat gate).
        assert row.protest_pressure_z is None, f"{week}: protest_pressure_z expected NULL live-side"
        assert row.violence_pressure_z is None, f"{week}: violence_pressure_z expected NULL live-side"
        assert row.suppression_z is None, f"{week}: suppression_z expected NULL live-side"

        # Shadow side: violence is fully un-suppressed across the range.
        assert row.shadow_violence_pressure_z is not None, (
            f"{week}: shadow_violence_pressure_z expected non-NULL"
        )

        # Shadow side: suppression stays NULL throughout -- gated by its own
        # sparse_suppression_baseline_flag, untouched by this fix.
        assert row.shadow_suppression_z is None, (
            f"{week}: shadow_suppression_z expected NULL (per-family gate, not "
            f"a TD-136-affected week for this family)"
        )

        # Shadow side: protest is un-suppressed everywhere except the first
        # week, which is still gated by its own sparse_protest_baseline_flag.
        if week in PROTEST_STILL_NULL_WEEKS:
            assert row.shadow_protest_pressure_z is None, (
                f"{week}: shadow_protest_pressure_z expected NULL (still gated "
                f"by sparse_protest_baseline_flag)"
            )
        else:
            assert row.shadow_protest_pressure_z is not None, (
                f"{week}: shadow_protest_pressure_z expected non-NULL"
            )


@requires_bigquery
def test_kenya_flipped_rows_matches_observation_baseline():
    query = f"""
        SELECT
          COUNT(*) AS total_rows,
          COUNTIF(signal_valid = FALSE AND shadow_global_conditions_valid = TRUE) AS flipped_rows
        FROM `{PROJECT_ID}.features.acled_pressure_signals`
        WHERE country = "Kenya"
    """
    row = list(_client().query(query).result())[0]
    assert row.total_rows == KENYA_TOTAL_ROWS, (
        f"expected {KENYA_TOTAL_ROWS} Kenya rows, got {row.total_rows} -- "
        f"backfill state has changed since this baseline was established"
    )
    assert row.flipped_rows == KENYA_FLIPPED_ROWS, (
        f"expected {KENYA_FLIPPED_ROWS} flipped rows, got {row.flipped_rows} -- "
        f"drift on the TD-136 Option E observation baseline"
    )
