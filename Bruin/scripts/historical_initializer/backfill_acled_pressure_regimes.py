"""
backfill_acled_pressure_regimes.py
====================================
Sequential historical backfill driver for intelligence.acled_pressure_regimes.

WHAT THIS SCRIPT DOES
---------------------
Invokes the existing intelligence.acled_pressure_regimes Bruin asset once per
week, in chronological order, waiting for each merge to complete before
proceeding to the next week. This satisfies the EXECUTION CONTRACT documented
in the asset's header: the self-referential lag join in CTE-03 requires that
week N-1 is already committed to intelligence.acled_pressure_regimes before
week N's execution begins.

WHY THIS APPROACH
-----------------
The intelligence asset is a stateful regime engine. Persistence-dependent
classifications (REPRESSION, CONTESTATION, MOBILISATION, CONFLICT) require
consecutive qualifying weeks to fire. Running all 1523+ weeks in a single
Bruin execution means every week's persistence context join finds nothing
(the table was empty at execution start), producing is_first_observation_week
= TRUE for every row and suppressing all persistence-dependent regimes.
Sequential single-week execution is the only mechanism that restores correct
persistence chaining without modifying the classification SQL.

EXECUTION MODEL
---------------
1. Acquire lock: write IN_PROGRESS to country_initialization_status.
2. Determine ordered week list from features.acled_pressure_signals.
3. Determine resume point from latest_week_backfilled (checkpoint).
4. For each week from resume point onward:
   a. Invoke: bruin run <asset_path> --var country=... --var target_week=...
   b. Wait for Bruin exit (synchronous subprocess call).
   c. Confirm the week's row now exists in intelligence.acled_pressure_regimes.
   d. Write checkpoint to country_initialization_status.
5. On completion: write COMPLETE + initialized_under_version.
6. On clean staged stop (--max-weeks): write PAUSED.
7. On failure: write FAILED + error_message.

RESUMABILITY
------------
The script is fully resumable. If interrupted at any point, re-running with
the same arguments will:
  - Detect the stale IN_PROGRESS lock (if last_updated_at is old enough).
  - Resume from latest_week_backfilled + 1 week.
  - Verify checkpoint consistency before proceeding.

USAGE
-----
    python backfill_acled_pressure_regimes.py \\
        --project-id encoded-joy-485413-k5 \\
        --country Kenya \\
        --iso2 KE \\
        --asset-path assets/intelligence/acled_pressure_regimes.sql \\
        --mode HISTORICAL_BACKFILL

    # Dry run (no Bruin invocations, no BigQuery writes):
    python backfill_acled_pressure_regimes.py ... --dry-run

    # Override stale lock explicitly:
    python backfill_acled_pressure_regimes.py ... --force-recover-stale-lock

DEPENDENCIES
------------
    pip install google-cloud-bigquery

The script shells out to `bruin` CLI -- ensure `bruin` is on PATH and
authenticated against the target project before running.
"""

import argparse
import logging
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from google.cloud import bigquery

# --- Constants ----------------------------------------------------------------

METHODOLOGY_VERSION = "ACLED_REGIME_ENGINE_V1"  # Must match CTE-01 literal
STATUS_TABLE = "intelligence.country_initialization_status"
INTELLIGENCE_TABLE = "intelligence.acled_pressure_regimes"
FEATURES_TABLE = "features.acled_pressure_signals"

# A lock is considered stale if last_updated_at is older than this (seconds).
STALE_LOCK_THRESHOLD_SECONDS = 7200

# Debug SQL log: every MERGE statement is written here before execution.
# Allows inspection of the exact SQL BigQuery rejects on a type error.
# Set to None to disable file logging once debugging is complete.
DEBUG_SQL_LOG = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "debug_sql.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


# --- SQL Queries --------------------------------------------------------------

def sql_get_status(project_id: str, country: str) -> str:
    """Read current initialization status for a country."""
    return f"""
        SELECT
            initialization_status,
            latest_week_backfilled,
            total_weeks_expected,
            weeks_completed,
            started_at,
            last_updated_at,
            initialization_run_id,
            initialized_under_version
        FROM `{project_id}.{STATUS_TABLE}`
        WHERE country = '{country}'
        LIMIT 1
    """


def sql_get_ordered_weeks(project_id: str, country: str) -> str:
    """Return all available weeks for a country, in chronological order."""
    return f"""
        SELECT DISTINCT week_start_date
        FROM `{project_id}.{FEATURES_TABLE}`
        WHERE country = '{country}'
          AND week_start_date IS NOT NULL
        ORDER BY week_start_date ASC
    """


def sql_get_max_committed_week(project_id: str, country: str) -> str:
    """Return the most recent week_start_date in the intelligence table."""
    return f"""
        SELECT MAX(week_start_date) AS max_week
        FROM `{project_id}.{INTELLIGENCE_TABLE}`
        WHERE country = '{country}'
    """


def sql_confirm_week_committed(project_id: str, country: str, week: str) -> str:
    """Check whether a specific week exists in the intelligence table."""
    return f"""
        SELECT COUNT(*) AS row_count
        FROM `{project_id}.{INTELLIGENCE_TABLE}`
        WHERE country = '{country}'
          AND week_start_date = DATE('{week}')
    """


def sql_upsert_status(
    project_id: str,
    country: str,
    iso2: str,
    status: str,
    run_id: str,
    mode: str,
    earliest_week: Optional[str],
    total_weeks: Optional[int],
    latest_week_backfilled=None,
    weeks_completed: Optional[int] = None,
    started_at: Optional[str] = None,
    initialized_at: Optional[str] = None,
    initialized_under_version: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """
    Upsert (MERGE) a country row into country_initialization_status.

    TYPE CASTING NOTE:
    BigQuery MERGE...USING infers column types from SELECT expressions.
    Plain quoted strings are typed STRING -- BigQuery will NOT implicitly
    cast STRING to DATE or TIMESTAMP in a MERGE USING clause.
    Each column type uses an explicit typed helper below.
    """
    now = datetime.now(timezone.utc).isoformat()

    def str_val(v) -> str:
        """STRING: single-quoted literal or CAST(NULL AS STRING)."""
        if v is None:
            return "CAST(NULL AS STRING)"
        escaped = str(v).replace("'", "\\'")
        return f"'{escaped}'"

    def date_val(v) -> str:
        """DATE: DATE('YYYY-MM-DD') or CAST(NULL AS DATE).
        Handles str, datetime.date (returned by BigQuery client), or None.
        Bare NULL is inferred as INT64 by BigQuery in a MERGE USING subquery,
        which then fails assignment to a DATE column. Explicit CAST required.
        """
        if v is None:
            return "CAST(NULL AS DATE)"
        # BigQuery client returns DATE columns as datetime.date objects
        if hasattr(v, "isoformat"):
            s = v.isoformat()
        else:
            s = str(v)
        escaped = s.replace("'", "\\'")
        return f"DATE('{escaped}')"

    def ts_val(v) -> str:
        """TIMESTAMP: TIMESTAMP('...') or CAST(NULL AS TIMESTAMP).
        Handles str, datetime.datetime, or None.
        """
        if v is None:
            return "CAST(NULL AS TIMESTAMP)"
        if hasattr(v, "isoformat"):
            s = v.isoformat()
        else:
            s = str(v)
        escaped = s.replace("'", "\\'")
        return f"TIMESTAMP('{escaped}')"

    def int_val(v) -> str:
        """INT64: bare integer literal or CAST(NULL AS INT64)."""
        if v is None:
            return "CAST(NULL AS INT64)"
        return str(int(v))

    return f"""
        MERGE `{project_id}.{STATUS_TABLE}` T
        USING (
            SELECT
                {str_val(country)}                      AS country,
                {str_val(iso2)}                         AS iso2,
                {str_val(status)}                       AS initialization_status,
                {date_val(earliest_week)}               AS earliest_week_available,
                {date_val(latest_week_backfilled)}      AS latest_week_backfilled,
                {int_val(total_weeks)}                  AS total_weeks_expected,
                {int_val(weeks_completed)}              AS weeks_completed,
                {ts_val(started_at)}                    AS started_at,
                {ts_val(initialized_at)}                AS initialized_at,
                {ts_val(now)}                           AS last_updated_at,
                {str_val(initialized_under_version)}    AS initialized_under_version,
                {str_val(mode)}                         AS initialization_mode,
                {str_val(run_id)}                       AS initialization_run_id,
                {str_val(error_message)}                AS error_message
        ) S ON T.country = S.country
        WHEN MATCHED THEN UPDATE SET
            initialization_status       = S.initialization_status,
            earliest_week_available     = S.earliest_week_available,
            latest_week_backfilled      = S.latest_week_backfilled,
            total_weeks_expected        = S.total_weeks_expected,
            weeks_completed             = S.weeks_completed,
            started_at                  = S.started_at,
            initialized_at              = S.initialized_at,
            last_updated_at             = S.last_updated_at,
            initialized_under_version   = S.initialized_under_version,
            initialization_mode         = S.initialization_mode,
            initialization_run_id       = S.initialization_run_id,
            error_message               = S.error_message
        WHEN NOT MATCHED THEN INSERT (
            country, iso2, initialization_status, earliest_week_available,
            latest_week_backfilled, total_weeks_expected, weeks_completed,
            started_at, initialized_at, last_updated_at,
            initialized_under_version, initialization_mode,
            initialization_run_id, error_message
        ) VALUES (
            S.country, S.iso2, S.initialization_status,
            S.earliest_week_available, S.latest_week_backfilled,
            S.total_weeks_expected, S.weeks_completed,
            S.started_at, S.initialized_at, S.last_updated_at,
            S.initialized_under_version, S.initialization_mode,
            S.initialization_run_id, S.error_message
        )
    """


# --- BigQuery helpers ---------------------------------------------------------

def bq_query(client: bigquery.Client, sql: str) -> list[dict]:
    """Execute a SELECT query and return all rows as a list of dicts."""
    result = client.query(sql).result()
    return [dict(row) for row in result]


def bq_execute(client: bigquery.Client, sql: str, dry_run: bool = False) -> None:
    """Execute a DML statement (MERGE/INSERT/UPDATE). No-op in dry_run mode.

    DEBUG: writes every SQL statement to debug_sql.log before submitting
    to BigQuery. This lets you inspect the exact MERGE text that BigQuery
    rejects on a type error. Remove the logging block once stable.
    """
    if dry_run:
        log.info("[DRY RUN] Would execute:\n%s", sql.strip()[:300])
        return

    # -- DEBUG SQL logging -----------------------------------------------------
    if DEBUG_SQL_LOG:
        with open(DEBUG_SQL_LOG, "a") as f:
            f.write("\n" + "=" * 70 + "\n")
            f.write(f"TIMESTAMP: {datetime.now(timezone.utc).isoformat()}\n")
            f.write(sql)
            f.write("\n" + "=" * 70 + "\n")
        log.info("SQL logged to %s", DEBUG_SQL_LOG)
    # -- END DEBUG -------------------------------------------------------------

    client.query(sql).result()


# --- Lock acquisition ---------------------------------------------------------

def acquire_lock(
    client: bigquery.Client,
    project_id: str,
    country: str,
    iso2: str,
    run_id: str,
    mode: str,
    earliest_week: Optional[str],
    total_weeks: int,
    force_recover: bool,
    dry_run: bool,
) -> dict:
    """
    Acquire the IN_PROGRESS lock for this country.
    Returns the existing status row (or empty dict if no row existed).
    Raises RuntimeError if the lock cannot be acquired safely.

    Lock acquisition rules:
      PENDING / no row  → start fresh, no check needed.
      PAUSED            → safe to resume immediately (intentional staged stop).
                          No staleness check — PAUSED is never written by a
                          crash, only by a clean staged stop via --max-weeks.
      IN_PROGRESS       → check staleness. Refuse if recent (concurrent
                          protection). Recover if stale or --force-recover.
      FAILED            → require --force-recover (human acknowledgement).
      COMPLETE          → nothing to do (caller handles this before lock).
    """
    rows = bq_query(client, sql_get_status(project_id, country))
    existing = rows[0] if rows else {}
    status = existing.get("initialization_status")
    last_updated = existing.get("last_updated_at")

    if status == "PAUSED":
        # Clean intentional stop — always safe to resume immediately.
        log.info(
            "Country '%s' is PAUSED at week %s. Resuming.",
            country, existing.get("latest_week_backfilled"),
        )

    elif status == "IN_PROGRESS":
        if last_updated:
            age_seconds = (datetime.now(timezone.utc) -
                           last_updated).total_seconds()
            if age_seconds < STALE_LOCK_THRESHOLD_SECONDS and not force_recover:
                raise RuntimeError(
                    f"Country '{country}' is already IN_PROGRESS "
                    f"(run_id={existing.get('initialization_run_id')}, "
                    f"last_updated={last_updated}). "
                    f"If stale, re-run with --force-recover-stale-lock."
                )
            log.warning(
                "Recovering stale IN_PROGRESS lock for '%s' "
                "(last_updated=%s, age=%.0fs). Prior run_id=%s.",
                country, last_updated, age_seconds,
                existing.get("initialization_run_id"),
            )
        else:
            if not force_recover:
                raise RuntimeError(
                    f"Country '{country}' is IN_PROGRESS with no last_updated_at. "
                    f"Use --force-recover-stale-lock to override."
                )

    elif status == "FAILED":
        if not force_recover:
            raise RuntimeError(
                f"Country '{country}' has status FAILED "
                f"(error: {existing.get('error_message', 'unknown')}). "
                f"Investigate the failure, then re-run with --force-recover-stale-lock "
                f"to resume from the last checkpoint."
            )
        log.warning(
            "Force-recovering FAILED run for '%s'. Prior error: %s",
            country, existing.get("error_message"),
        )

    log.info("Acquiring lock for '%s' (run_id=%s, mode=%s).",
             country, run_id, mode)

    started_at = datetime.now(timezone.utc).isoformat()
    bq_execute(
        client,
        sql_upsert_status(
            project_id=project_id,
            country=country,
            iso2=iso2,
            status="IN_PROGRESS",
            run_id=run_id,
            mode=mode,
            earliest_week=earliest_week,
            total_weeks=total_weeks,
            latest_week_backfilled=existing.get("latest_week_backfilled"),
            weeks_completed=existing.get("weeks_completed", 0),
            started_at=started_at,
        ),
        dry_run=dry_run,
    )
    return existing


# --- Resume point determination -----------------------------------------------

def determine_resume_point(
    client: bigquery.Client,
    project_id: str,
    country: str,
    existing_status: dict,
    ordered_weeks: list[str],
    dry_run: bool,
) -> int:
    """
    Determine which index in ordered_weeks to start (or resume) from.
    Returns the index of the first week NOT yet committed.
    """
    status_checkpoint = existing_status.get("latest_week_backfilled")
    rows = bq_query(client, sql_get_max_committed_week(project_id, country))
    table_max = rows[0]["max_week"] if rows else None

    # Normalise to string (BigQuery returns datetime.date objects)
    status_str = str(status_checkpoint) if status_checkpoint else None
    table_str = str(table_max) if table_max else None

    log.info(
        "Checkpoint: status_table=%s, intelligence_table_max=%s.",
        status_str, table_str,
    )

    if status_str != table_str:
        log.warning(
            "CHECKPOINT MISMATCH: status table='%s', intelligence table='%s'. "
            "Trusting intelligence table as authoritative.",
            status_str, table_str,
        )
        authoritative = table_str
    else:
        authoritative = status_str

    if authoritative is None:
        log.info("No prior progress found. Starting from week 1.")
        return 0

    try:
        idx = ordered_weeks.index(authoritative)
    except ValueError:
        raise RuntimeError(
            f"Checkpoint week '{authoritative}' not found in "
            f"features.acled_pressure_signals for country '{country}'. "
            f"The features table may have changed. Manual review required."
        )

    resume_idx = idx + 1
    if resume_idx < len(ordered_weeks):
        log.info(
            "Resuming from week %d/%d (%s).",
            resume_idx + 1, len(ordered_weeks), ordered_weeks[resume_idx],
        )
    else:
        log.info("All %d weeks already present in intelligence table.",
                 len(ordered_weeks))
    return resume_idx


# --- Bruin invocation ---------------------------------------------------------

def invoke_bruin(
    asset_path: str,
    project_id: str,
    country: str,
    iso2: str,
    week: str,
    dry_run: bool,
) -> bool:
    """
    Invoke `bruin run <asset> --var ...` for a single week.
    Returns True on success (exit code 0), False on failure.
    """
    cmd = [
        "bruin", "run", asset_path,
        "--var", f"project_id=\"{project_id}\"",
        "--var", f"country=\"{country}\"",
        "--var", f"iso2=\"{iso2}\"",
        "--var", f"target_week=\"{week}\"",
    ]

    if dry_run:
        log.info("[DRY RUN] Would invoke: %s", " ".join(cmd))
        return True

    log.info("Invoking Bruin for week %s ...", week)
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        log.error(
            "Bruin FAILED for week %s (exit=%d).\nSTDOUT:\n%s\nSTDERR:\n%s",
            week, result.returncode,
            result.stdout[-2000:],
            result.stderr[-2000:],
        )
        return False

    log.info("Bruin completed for week %s (exit=0).", week)
    return True


# --- Per-week commit confirmation ---------------------------------------------

def confirm_week_committed(
    client: bigquery.Client,
    project_id: str,
    country: str,
    week: str,
    dry_run: bool,
) -> bool:
    """Verify the week's row exists in intelligence.acled_pressure_regimes."""
    if dry_run:
        return True

    rows = bq_query(client, sql_confirm_week_committed(
        project_id, country, week))
    count = rows[0]["row_count"] if rows else 0

    if count == 0:
        log.error(
            "COMMIT CONFIRMATION FAILED: week %s not found after Bruin exit=0.",
            week,
        )
        return False
    return True


# --- Main loop ----------------------------------------------------------------

def run_backfill(
    project_id: str,
    country: str,
    iso2: str,
    asset_path: str,
    mode: str,
    dry_run: bool,
    force_recover: bool,
    max_weeks: Optional[int] = None,
) -> None:
    """
    Main backfill orchestration loop.
    max_weeks: stop after this many cumulative weeks (staged rollout support).
    COMPLETE is only written when all weeks are processed.
    """
    client = bigquery.Client(project=project_id)
    run_id = str(uuid.uuid4())

    log.info(
        "=== BACKFILL START | country=%s iso2=%s mode=%s run_id=%s dry_run=%s ===",
        country, iso2, mode, run_id, dry_run,
    )

    # 1. Fetch ordered weeks
    log.info("Fetching ordered week list from features table ...")
    week_rows = bq_query(client, sql_get_ordered_weeks(project_id, country))
    if not week_rows:
        raise RuntimeError(
            f"No weeks found in {FEATURES_TABLE} for country='{country}'."
        )
    ordered_weeks = [str(r["week_start_date"]) for r in week_rows]
    total_weeks = len(ordered_weeks)
    earliest_week = ordered_weeks[0]
    latest_week = ordered_weeks[-1]
    log.info("Found %d weeks: %s -> %s.",
             total_weeks, earliest_week, latest_week)

    # 2. Acquire lock
    existing_status = acquire_lock(
        client=client,
        project_id=project_id,
        country=country,
        iso2=iso2,
        run_id=run_id,
        mode=mode,
        earliest_week=earliest_week,
        total_weeks=total_weeks,
        force_recover=force_recover,
        dry_run=dry_run,
    )

    # 3. Determine resume point
    resume_idx = determine_resume_point(
        client=client,
        project_id=project_id,
        country=country,
        existing_status=existing_status,
        ordered_weeks=ordered_weeks,
        dry_run=dry_run,
    )

    weeks_to_process = ordered_weeks[resume_idx:]
    weeks_already_done = resume_idx

    # Checkpoint sync: if mismatch was resolved by trusting the intelligence
    # table, write the corrected checkpoint before entering the loop so a
    # second crash resumes cleanly without another mismatch warning.
    if resume_idx > 0:
        authoritative_checkpoint = ordered_weeks[resume_idx - 1]
        bq_execute(
            client,
            sql_upsert_status(
                project_id=project_id,
                country=country,
                iso2=iso2,
                status="IN_PROGRESS",
                run_id=run_id,
                mode=mode,
                earliest_week=earliest_week,
                total_weeks=total_weeks,
                latest_week_backfilled=authoritative_checkpoint,
                weeks_completed=resume_idx,
            ),
            dry_run=dry_run,
        )
        log.info(
            "Checkpoint synced to '%s' (%d weeks) before loop.",
            authoritative_checkpoint, resume_idx,
        )

    if not weeks_to_process:
        log.info("All %d weeks committed. Setting status to COMPLETE.", total_weeks)
        _write_complete(
            client, project_id, country, iso2, run_id, mode,
            earliest_week, latest_week, total_weeks, total_weeks, dry_run,
        )
        return

    # Apply max_weeks ceiling (cumulative across runs)
    if max_weeks is not None:
        remaining_budget = max_weeks - weeks_already_done
        if remaining_budget <= 0:
            log.info(
                "max_weeks=%d already reached (%d done). Nothing to do.",
                max_weeks, weeks_already_done,
            )
            return
        weeks_to_process = weeks_to_process[:remaining_budget]
        log.info(
            "max_weeks=%d: processing %d weeks this run (budget=%d, done=%d).",
            max_weeks, len(
                weeks_to_process), remaining_budget, weeks_already_done,
        )

    log.info(
        "%d weeks already done, %d to process (total expected: %d).",
        weeks_already_done, len(weeks_to_process), total_weeks,
    )

    # 4. Sequential loop
    try:
        for i, week in enumerate(weeks_to_process):
            global_idx = weeks_already_done + i + 1
            log.info("--- Week %d/%d | %s ---", global_idx, total_weeks, week)

            success = invoke_bruin(
                asset_path=asset_path,
                project_id=project_id,
                country=country,
                iso2=iso2,
                week=week,
                dry_run=dry_run,
            )
            if not success:
                raise RuntimeError(f"Bruin invocation failed for week {week}.")

            committed = confirm_week_committed(
                client=client,
                project_id=project_id,
                country=country,
                week=week,
                dry_run=dry_run,
            )
            if not committed:
                raise RuntimeError(
                    f"Commit confirmation failed for week {week}. "
                    f"Bruin exited 0 but row not found in intelligence table."
                )

            bq_execute(
                client,
                sql_upsert_status(
                    project_id=project_id,
                    country=country,
                    iso2=iso2,
                    status="IN_PROGRESS",
                    run_id=run_id,
                    mode=mode,
                    earliest_week=earliest_week,
                    total_weeks=total_weeks,
                    latest_week_backfilled=week,
                    weeks_completed=global_idx,
                ),
                dry_run=dry_run,
            )
            log.info("Checkpoint written: %d/%d weeks complete.",
                     global_idx, total_weeks)

    except Exception as exc:
        log.error("BACKFILL FAILED: %s", exc)
        bq_execute(
            client,
            sql_upsert_status(
                project_id=project_id,
                country=country,
                iso2=iso2,
                status="FAILED",
                run_id=run_id,
                mode=mode,
                earliest_week=earliest_week,
                total_weeks=total_weeks,
                error_message=str(exc),
            ),
            dry_run=dry_run,
        )
        log.error("=== BACKFILL FAILED | country=%s run_id=%s ===",
                  country, run_id)
        sys.exit(1)

    # 5. Write final status
    final_weeks_done = weeks_already_done + len(weeks_to_process)
    if final_weeks_done >= total_weeks:
        _write_complete(
            client, project_id, country, iso2, run_id, mode,
            earliest_week, latest_week, total_weeks, final_weeks_done, dry_run,
        )
        log.info(
            "=== BACKFILL COMPLETE | country=%s total_weeks=%d run_id=%s ===",
            country, total_weeks, run_id,
        )
    else:
        # Stopped early via --max-weeks. Write PAUSED so the next run resumes
        # immediately without requiring --force-recover-stale-lock.
        # PAUSED is always safe to resume — it is only written by a clean
        # staged stop, never by a crash. The last per-week checkpoint already
        # recorded latest_week_backfilled; this call updates only the status.
        bq_execute(
            client,
            sql_upsert_status(
                project_id=project_id,
                country=country,
                iso2=iso2,
                status="PAUSED",
                run_id=run_id,
                mode=mode,
                earliest_week=earliest_week,
                total_weeks=total_weeks,
                latest_week_backfilled=ordered_weeks[final_weeks_done - 1],
                weeks_completed=final_weeks_done,
            ),
            dry_run=dry_run,
        )
        log.info(
            "=== STAGED STOP | country=%s weeks_done=%d/%d run_id=%s ===\n"
            "    Status set to PAUSED. Re-run without --max-weeks "
            "(or with a higher value) to continue without any flags.",
            country, final_weeks_done, total_weeks, run_id,
        )


def _write_complete(
    client, project_id, country, iso2, run_id, mode,
    earliest_week, latest_week, total_weeks, weeks_completed, dry_run,
):
    initialized_at = datetime.now(timezone.utc).isoformat()
    bq_execute(
        client,
        sql_upsert_status(
            project_id=project_id,
            country=country,
            iso2=iso2,
            status="COMPLETE",
            run_id=run_id,
            mode=mode,
            earliest_week=earliest_week,
            total_weeks=total_weeks,
            latest_week_backfilled=latest_week,
            weeks_completed=weeks_completed,
            initialized_at=initialized_at,
            initialized_under_version=METHODOLOGY_VERSION,
        ),
        dry_run=dry_run,
    )


# --- CLI ----------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Sequential historical backfill for intelligence.acled_pressure_regimes."
    )
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--country", required=True)
    parser.add_argument("--iso2", required=True)
    parser.add_argument("--asset-path", required=True)
    parser.add_argument(
        "--mode",
        choices=["HISTORICAL_BACKFILL",
                 "REBUILD_AFTER_METHOD_CHANGE", "REPAIR_AFTER_FAILURE"],
        default="HISTORICAL_BACKFILL",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force-recover-stale-lock", action="store_true")
    parser.add_argument(
        "--max-weeks", type=int, default=None,
        help="Stop after this many cumulative weeks (staged rollout).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_backfill(
        project_id=args.project_id,
        country=args.country,
        iso2=args.iso2,
        asset_path=args.asset_path,
        mode=args.mode,
        dry_run=args.dry_run,
        force_recover=args.force_recover_stale_lock,
        max_weeks=args.max_weeks,
    )
