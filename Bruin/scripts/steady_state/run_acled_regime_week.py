"""
run_acled_regime_week.py
=========================
Steady-state single-week driver for intelligence.acled_pressure_regimes.

WHY THIS SCRIPT EXISTS (TD-38)
-------------------------------
The regime asset's EXECUTION CONTRACT requires exactly one country, one new
week, per execution (see the "EXECUTION CONTRACT (AUTHORITATIVE)" comment
block in assets/intelligence/acled_pressure_regimes.sql). pipeline.yml's
documented steady-state default is target_week="", but the upstream
features.acled_pressure_signals asset uses strategy: create+replace with no
incremental filter -- it recomputes the country's entire history every run.
Passing target_week="" in steady state would therefore silently violate the
asset's own contract on every scheduled invocation.

This script resolves target_week for steady-state runs instead: it looks up
the single next unprocessed week itself and passes that explicit week to
Bruin. It never falls back to target_week="".

WHAT THIS SCRIPT DOES NOT DO
------------------------------
It does not replay history. If more than one week is pending (e.g. a
scheduled run was skipped), it processes only the single next week and
leaves the rest for the following invocation -- one country, one new week,
per execution, same as the contract requires. Historical replay of many
weeks is backfill_acled_pressure_regimes.py's job, not this script's.

SHARED LOGIC
------------
Ground-truth checkpoint lookup (sql_get_max_committed_week), the available-
week list (sql_get_ordered_weeks), Bruin invocation (invoke_bruin), commit
confirmation (confirm_week_committed), and the status-table upsert/COMPLETE
helpers (sql_upsert_status, _write_complete) are imported from
historical_initializer/backfill_acled_pressure_regimes.py rather than
duplicated here.

USAGE
-----
    python run_acled_regime_week.py \\
        --project-id encoded-joy-485413-k5 \\
        --country Kenya \\
        --iso2 KE \\
        --asset-path assets/intelligence/acled_pressure_regimes.sql

    # Dry run (no Bruin invocation, no BigQuery writes):
    python run_acled_regime_week.py ... --dry-run

Must be run with cwd=Bruin/ (same requirement as the backfill script) so
that --asset-path resolves correctly for the bruin CLI.
"""

import argparse
import logging
import os
import sys
import uuid

from google.cloud import bigquery

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "..", "historical_initializer",
    ),
)

from backfill_acled_pressure_regimes import (  # noqa: E402
    bq_execute,
    bq_query,
    confirm_week_committed,
    invoke_bruin,
    sql_get_max_committed_week,
    sql_get_ordered_weeks,
    sql_upsert_status,
    _write_complete,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)

MODE = "STEADY_STATE"


def find_next_week(client: bigquery.Client, project_id: str, country: str):
    """
    Determine the single next week to process for a steady-state run.

    Ground truth is MAX(week_start_date) in intelligence.acled_pressure_regimes
    (not the status table's checkpoint) -- same authority rule
    determine_resume_point uses in the backfill script. Returns
    (next_week, ordered_weeks) where next_week is the first
    features.acled_pressure_signals row strictly after the committed max, or
    (None, ordered_weeks) if no such week exists yet.
    """
    committed_rows = bq_query(
        client, sql_get_max_committed_week(project_id, country))
    max_committed = committed_rows[0]["max_week"] if committed_rows else None

    week_rows = bq_query(client, sql_get_ordered_weeks(project_id, country))
    ordered_weeks = [r["week_start_date"] for r in week_rows]

    if max_committed is None:
        next_week = ordered_weeks[0] if ordered_weeks else None
        return next_week, ordered_weeks

    candidates = [w for w in ordered_weeks if w > max_committed]
    next_week = candidates[0] if candidates else None
    return next_week, ordered_weeks


def run_steady_state(
    project_id: str,
    country: str,
    iso2: str,
    asset_path: str,
    dry_run: bool,
) -> None:
    client = bigquery.Client(project=project_id)
    run_id = str(uuid.uuid4())

    log.info(
        "=== STEADY-STATE START | country=%s iso2=%s run_id=%s dry_run=%s ===",
        country, iso2, run_id, dry_run,
    )

    next_week, ordered_weeks = find_next_week(client, project_id, country)

    if next_week is None:
        log.info("No new week available for %s, nothing to do.", country)
        return

    week_str = str(next_week)
    log.info("Next week to process for %s: %s", country, week_str)

    success = invoke_bruin(
        asset_path=asset_path,
        project_id=project_id,
        country=country,
        iso2=iso2,
        week=week_str,
        dry_run=dry_run,
    )
    if not success:
        raise RuntimeError(f"Bruin invocation failed for week {week_str}.")

    committed = confirm_week_committed(
        client=client,
        project_id=project_id,
        country=country,
        week=week_str,
        dry_run=dry_run,
    )
    if not committed:
        raise RuntimeError(
            f"Commit confirmation failed for week {week_str}. "
            f"Bruin exited 0 but row not found in intelligence table."
        )

    earliest_week = ordered_weeks[0]
    total_weeks = len(ordered_weeks)
    weeks_completed = ordered_weeks.index(next_week) + 1

    if weeks_completed >= total_weeks:
        _write_complete(
            client, project_id, country, iso2, run_id, MODE,
            str(earliest_week), week_str, total_weeks, weeks_completed,
            dry_run,
        )
        log.info(
            "=== STEADY-STATE COMPLETE | country=%s week=%s "
            "weeks_completed=%d/%d run_id=%s ===",
            country, week_str, weeks_completed, total_weeks, run_id,
        )
    else:
        # More weeks are already queued in features.acled_pressure_signals
        # than this single-week execution processed. Same PAUSED semantics
        # the backfill script uses for a staged stop: always safe to resume,
        # the next scheduled invocation picks up the following week.
        bq_execute(
            client,
            sql_upsert_status(
                project_id=project_id,
                country=country,
                iso2=iso2,
                status="PAUSED",
                run_id=run_id,
                mode=MODE,
                earliest_week=str(earliest_week),
                total_weeks=total_weeks,
                latest_week_backfilled=week_str,
                weeks_completed=weeks_completed,
            ),
            dry_run=dry_run,
        )
        log.info(
            "=== STEADY-STATE STEP | country=%s week=%s "
            "weeks_completed=%d/%d run_id=%s ===\n"
            "    %d week(s) still pending; next scheduled run will pick up "
            "the following week.",
            country, week_str, weeks_completed, total_weeks, run_id,
            total_weeks - weeks_completed,
        )


def parse_args():
    parser = argparse.ArgumentParser(
        description="Steady-state single-week driver for "
        "intelligence.acled_pressure_regimes."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--iso2", required=True)
    parser.add_argument("--asset-path", required=True)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_steady_state(
        project_id=args.project_id,
        country=args.country,
        iso2=args.iso2,
        asset_path=args.asset_path,
        dry_run=args.dry_run,
    )
