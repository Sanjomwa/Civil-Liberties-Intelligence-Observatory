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
6. On failure: write FAILED + error_message.

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
        --asset-path pipelines/civil_liberties_pipeline/assets/intelligence/acled_pressure_regimes.sql \\
        --mode HISTORICAL_BACKFILL

    # Dry run (no Bruin invocations, no BigQuery writes):
    python backfill_acled_pressure_regimes.py ... --dry-run

    # Override stale lock explicitly:
    python backfill_acled_pressure_regimes.py ... --force-recover-stale-lock

DEPENDENCIES
------------
    pip install google-cloud-bigquery

The script shells out to `bruin` CLI — ensure `bruin` is on PATH and
authenticated against the target project before running.
"""

import argparse
import logging
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional

from google.cloud import bigquery

# ─── Constants ────────────────────────────────────────────────────────────────

METHODOLOGY_VERSION = "ACLED_REGIME_ENGINE_V1"  # Must match CTE-01 literal
STATUS_TABLE = "intelligence.country_initialization_status"
INTELLIGENCE_TABLE = "intelligence.acled_pressure_regimes"
FEATURES_TABLE = "features.acled_pressure_signals"

# A lock is considered stale if last_updated_at is older than this (seconds).
# Set generously: 2 hours >> expected per-week Bruin invocation time.
STALE_LOCK_THRESHOLD_SECONDS = 7200

# Logging format includes timestamp, level, and message.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%SZ",
)
log = logging.getLogger(__name__)


# ─── SQL Queries ──────────────────────────────────────────────────────────────

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


def sql_confirm_week_committed(
    project_id: str, country: str, week: str
) -> str:
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
    latest_week_backfilled: Optional[str] = None,
    weeks_completed: Optional[int] = None,
    started_at: Optional[str] = None,
    initialized_at: Optional[str] = None,
    initialized_under_version: Optional[str] = None,
    error_message: Optional[str] = None,
) -> str:
    """
    Upsert (MERGE) a country row into country_initialization_status.
    Used for all status transitions: lock acquisition, per-week checkpoint,
    completion, and failure.

    TYPE CASTING NOTE:
    BigQuery's MERGE...USING clause infers column types from the SELECT
    expressions. Plain quoted string literals are typed as STRING, which
    BigQuery will not implicitly cast to DATE or TIMESTAMP. All DATE and
    TIMESTAMP columns must be wrapped in explicit DATE() / TIMESTAMP()
    casts. STRING and INT64 columns use plain literals.
    """
    now = datetime.now(timezone.utc).isoformat()

    def str_val(v) -> str:
        """STRING column: single-quoted literal or NULL."""
        if v is None:
            return "NULL"
        escaped = str(v).replace("'", "\\'")
        return f"'{escaped}'"

    def date_val(v) -> str:
        """DATE column: DATE('YYYY-MM-DD') or NULL.
        Accepts str, datetime.date, or None.
        BigQuery client returns DATE columns as datetime.date objects,
        not strings — both are handled here.
        """
        if v is None:
            return "NULL"
        if hasattr(v, 'isoformat'):
            date_str = v.isoformat()
        else:
            date_str = str(v)
        escaped = date_str.replace("'", "\\'")
        return f"DATE('{escaped}')"

    def ts_val(v) -> str:
        """TIMESTAMP column: TIMESTAMP('...') or NULL.
        Accepts str, datetime.datetime, or None.
        """
        if v is None:
            return "NULL"
        if hasattr(v, 'isoformat'):
            ts_str = v.isoformat()
        else:
            ts_str = str(v)
        escaped = ts_str.replace("'", "\\'")
        return f"TIMESTAMP('{escaped}')"

    def int_val(v: Optional[int]) -> str:
        """INT64 column: bare integer literal or NULL."""
        if v is None:
            return "NULL"
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


# ─── BigQuery helpers ─────────────────────────────────────────────────────────

def bq_query(client: bigquery.Client, sql: str) -> list[dict]:
    """Execute a query and return all rows as a list of dicts."""
    result = client.query(sql).result()
    return [dict(row) for row in result]


def bq_execute(client: bigquery.Client, sql: str, dry_run: bool = False) -> None:
    """Execute a DML statement (INSERT/MERGE/UPDATE). No-op in dry_run mode."""
    if dry_run:
        log.info("[DRY RUN] Would execute:\n%s", sql.strip()[:300])
        return
    client.query(sql).result()


# ─── Lock acquisition ─────────────────────────────────────────────────────────

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
    Raises RuntimeError if lock cannot be acquired safely.
    """
    rows = bq_query(client, sql_get_status(project_id, country))
    existing = rows[0] if rows else {}
    status = existing.get("initialization_status")
    last_updated = existing.get("last_updated_at")

    if status == "IN_PROGRESS":
        if last_updated:
            age_seconds = (
                datetime.now(timezone.utc) - last_updated
            ).total_seconds()
            if age_seconds < STALE_LOCK_THRESHOLD_SECONDS and not force_recover:
                raise RuntimeError(
                    f"Country '{country}' is already IN_PROGRESS "
                    f"(run_id={existing.get('initialization_run_id')}, "
                    f"last_updated={last_updated}). "
                    f"If this is a stale lock, re-run with --force-recover-stale-lock."
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

    log.info(
        "Acquiring lock for '%s' (run_id=%s, mode=%s).",
        country, run_id, mode,
    )

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


# ─── Resume point determination ───────────────────────────────────────────────

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

    Uses latest_week_backfilled from the status table as the primary checkpoint,
    cross-checked against MAX(week_start_date) from the intelligence table.
    Returns the index of the first week that has NOT yet been committed.
    """
    status_checkpoint = existing_status.get("latest_week_backfilled")

    rows = bq_query(client, sql_get_max_committed_week(project_id, country))
    table_max = rows[0]["max_week"] if rows else None

    # Normalise to string for comparison (BigQuery returns datetime.date objects)
    status_str = str(status_checkpoint) if status_checkpoint else None
    table_str = str(table_max) if table_max else None

    log.info(
        "Checkpoint: status_table=%s, intelligence_table_max=%s.",
        status_str, table_str,
    )

    if status_str != table_str:
        log.warning(
            "CHECKPOINT MISMATCH: status table says '%s', "
            "intelligence table says '%s'. "
            "This may indicate the intelligence table was truncated or "
            "externally modified after the last checkpoint write. "
            "Trusting intelligence table max as the authoritative state.",
            status_str, table_str,
        )
        # Use intelligence table as ground truth — it's the actual output.
        authoritative = table_str
    else:
        authoritative = status_str

    if authoritative is None:
        log.info("No prior progress found. Starting from week 1.")
        return 0

    # Find index of the authoritative checkpoint in ordered_weeks
    try:
        idx = ordered_weeks.index(authoritative)
    except ValueError:
        raise RuntimeError(
            f"Checkpoint week '{authoritative}' not found in "
            f"features.acled_pressure_signals for country '{country}'. "
            f"The features table may have changed. Manual review required."
        )

    resume_idx = idx + 1
    log.info(
        "Resuming from week %d/%d (%s).",
        resume_idx + 1, len(ordered_weeks),
        ordered_weeks[resume_idx] if resume_idx < len(
            ordered_weeks) else "N/A",
    )
    return resume_idx


# ─── Bruin invocation ─────────────────────────────────────────────────────────

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

    NOTE on --var quoting: Bruin requires JSON-quoted strings for string
    variables, e.g. --var country='"Kenya"' (the value must be a JSON string,
    not a bare word). This is documented in Bruin's variable override docs.
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
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        log.error(
            "Bruin FAILED for week %s (exit=%d).\nSTDOUT:\n%s\nSTDERR:\n%s",
            week, result.returncode,
            # Truncate to last 2000 chars for log sanity
            result.stdout[-2000:],
            result.stderr[-2000:],
        )
        return False

    log.info("Bruin completed for week %s (exit=0).", week)
    return True


# ─── Per-week commit confirmation ─────────────────────────────────────────────

def confirm_week_committed(
    client: bigquery.Client,
    project_id: str,
    country: str,
    week: str,
    dry_run: bool,
) -> bool:
    """
    Verify that the week's row now exists in intelligence.acled_pressure_regimes.
    This closes the gap between 'Bruin exited 0' and 'the MERGE actually wrote'.
    """
    if dry_run:
        return True

    rows = bq_query(
        client,
        sql_confirm_week_committed(project_id, country, week)
    )
    count = rows[0]["row_count"] if rows else 0

    if count == 0:
        log.error(
            "COMMIT CONFIRMATION FAILED: week %s not found in "
            "intelligence.acled_pressure_regimes after Bruin exit=0. "
            "Possible BigQuery merge failure or schema mismatch.",
            week,
        )
        return False

    return True


# ─── Main loop ────────────────────────────────────────────────────────────────

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

    Responsibilities (in order):
      1. Connect to BigQuery.
      2. Fetch ordered week list.
      3. Acquire lock (with stale-lock recovery if needed).
      4. Determine resume point; sync status checkpoint if mismatched.
      5. Iterate: invoke Bruin, confirm commit, checkpoint.
      6. Write COMPLETE on success or max_weeks reached, FAILED on any error.

    max_weeks (int | None):
      When set, the driver stops after total weeks_completed reaches this
      value (cumulative across runs). The status is written as IN_PROGRESS
      (not COMPLETE) when stopping mid-backfill via --max-weeks, so a
      subsequent run picks up correctly. COMPLETE is only written when all
      weeks have been processed.
    """
    client = bigquery.Client(project=project_id)
    run_id = str(uuid.uuid4())

    log.info(
        "=== BACKFILL START | country=%s iso2=%s mode=%s run_id=%s dry_run=%s ===",
        country, iso2, mode, run_id, dry_run,
    )

    # ── 1. Fetch ordered weeks ────────────────────────────────────────────────
    log.info("Fetching ordered week list from features table ...")
    week_rows = bq_query(client, sql_get_ordered_weeks(project_id, country))
    if not week_rows:
        raise RuntimeError(
            f"No weeks found in {FEATURES_TABLE} for country='{country}'. "
            f"Verify the feature table is populated before running backfill."
        )
    ordered_weeks = [str(r["week_start_date"]) for r in week_rows]
    total_weeks = len(ordered_weeks)
    earliest_week = ordered_weeks[0]
    latest_week = ordered_weeks[-1]

    log.info(
        "Found %d weeks: %s → %s.",
        total_weeks, earliest_week, latest_week,
    )

    # ── 2. Acquire lock ───────────────────────────────────────────────────────
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

    # ── 3. Determine resume point ─────────────────────────────────────────────
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

    # ── Checkpoint sync (Q1 fix) ──────────────────────────────────────────────
    # If determine_resume_point resolved a mismatch by trusting the intelligence
    # table over the status table, sync the status table now before entering the
    # loop — so a second crash produces a clean resume rather than another mismatch.
    # This is a no-op when both checkpoints already agree.
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
            "Checkpoint synced to '%s' (%d weeks) before entering loop.",
            authoritative_checkpoint, resume_idx,
        )

    if not weeks_to_process:
        log.info(
            "All %d weeks already committed. Nothing to do. "
            "Setting status to COMPLETE.",
            total_weeks,
        )
        _write_complete(
            client, project_id, country, iso2, run_id, mode,
            earliest_week, latest_week, total_weeks, total_weeks, dry_run,
        )
        return

    # Apply max_weeks ceiling (cumulative across runs).
    # If max_weeks=100 and 25 weeks are already done, process 75 more.
    if max_weeks is not None:
        remaining_budget = max_weeks - weeks_already_done
        if remaining_budget <= 0:
            log.info(
                "max_weeks=%d already reached (%d done). Nothing to do this run.",
                max_weeks, weeks_already_done,
            )
            return
        weeks_to_process = weeks_to_process[:remaining_budget]
        log.info(
            "max_weeks=%d: will process up to %d weeks this run "
            "(budget: %d, already done: %d).",
            max_weeks, len(
                weeks_to_process), remaining_budget, weeks_already_done,
        )

    log.info(
        "%d weeks already done, %d to process this run (total expected: %d).",
        weeks_already_done, len(weeks_to_process), total_weeks,
    )

    # ── 4. Sequential loop ────────────────────────────────────────────────────
    try:
        for i, week in enumerate(weeks_to_process):
            global_idx = weeks_already_done + i + 1  # 1-based for logging
            log.info(
                "--- Week %d/%d | %s ---",
                global_idx, total_weeks, week,
            )

            # 4a. Invoke Bruin
            success = invoke_bruin(
                asset_path=asset_path,
                project_id=project_id,
                country=country,
                iso2=iso2,
                week=week,
                dry_run=dry_run,
            )
            if not success:
                raise RuntimeError(
                    f"Bruin invocation failed for week {week}. "
                    f"See error logs above."
                )

            # 4b. Confirm the row is committed
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

            # 4c. Write checkpoint
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
            log.info(
                "Checkpoint written: %d/%d weeks complete.",
                global_idx, total_weeks,
            )

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
        log.error(
            "=== BACKFILL FAILED | country=%s run_id=%s ===", country, run_id
        )
        sys.exit(1)

    # ── 5. Write status after loop ────────────────────────────────────────────
    final_weeks_done = weeks_already_done + len(weeks_to_process)
    all_weeks_done = final_weeks_done >= total_weeks

    if all_weeks_done:
        # Every week has been committed — write COMPLETE.
        _write_complete(
            client, project_id, country, iso2, run_id, mode,
            earliest_week, latest_week, total_weeks, final_weeks_done, dry_run,
        )
        log.info(
            "=== BACKFILL COMPLETE | country=%s total_weeks=%d run_id=%s ===",
            country, total_weeks, run_id,
        )
    else:
        # Stopped early via --max-weeks. Status remains IN_PROGRESS so the
        # next run picks up correctly. The last checkpoint write in the loop
        # already recorded latest_week_backfilled; this log makes the
        # staged-stop explicit.
        log.info(
            "=== STAGED STOP | country=%s weeks_done=%d/%d run_id=%s ===\n"
            "    Re-run without --max-weeks (or with a higher value) to continue.",
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


# ─── CLI ──────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(
        description="Sequential historical backfill for intelligence.acled_pressure_regimes."
    )
    parser.add_argument(
        "--project-id", required=True,
        help="GCP project ID (e.g. encoded-joy-485413-k5).",
    )
    parser.add_argument(
        "--country", required=True,
        help="Country name as it appears in features.acled_pressure_signals (e.g. Kenya).",
    )
    parser.add_argument(
        "--iso2", required=True,
        help="ISO 3166-1 alpha-2 country code (e.g. KE).",
    )
    parser.add_argument(
        "--asset-path", required=True,
        help="Relative path to acled_pressure_regimes.sql from the repo root "
             "(e.g. pipelines/civil_liberties_pipeline/assets/intelligence/acled_pressure_regimes.sql).",
    )
    parser.add_argument(
        "--mode",
        choices=["HISTORICAL_BACKFILL",
                 "REBUILD_AFTER_METHOD_CHANGE", "REPAIR_AFTER_FAILURE"],
        default="HISTORICAL_BACKFILL",
        help="Initialization mode recorded in country_initialization_status.",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print all actions without executing Bruin invocations or BigQuery writes.",
    )
    parser.add_argument(
        "--force-recover-stale-lock", action="store_true",
        help="Override an existing IN_PROGRESS lock without checking staleness threshold.",
    )
    parser.add_argument(
        "--max-weeks", type=int, default=None,
        help=(
            "Stop after this many weeks have been committed in total (cumulative "
            "across runs, not just this run). Used for staged rollout. "
            "Example: --max-weeks 25 stops when weeks_completed reaches 25. "
            "A subsequent run with --max-weeks 100 resumes and stops at 100. "
            "Omit to run to completion."
        ),
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
