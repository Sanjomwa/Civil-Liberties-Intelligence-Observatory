"""
ooni_agreement_check.py
========================
Standing OONI agreement-check guardrail (TD-100 / ADR-0013, steps 1-4).

WHY THIS SCRIPT EXISTS
-----------------------
CLIO has caught three real problems with its OONI-derived classifications,
all by accident, not by any standing check: TD-71 (an unexcluded DNS bogon
canary hostname inflated the flagship Finance Bill 2024 figure from 0 to
177, caught by OONI's own team), TD-93 (Signal's ANOMALOUS verdict was
62.5% driven by a legacy-domain NXDOMAIN artifact OONI itself calls
FAILED, caught by a one-off audit during an unrelated milestone review),
and a third (dnscheck evidential coupling, deliberately out of scope
here). The fix method behind the first two -- sample CLIO measurements by
report_id, fetch OONI's own real classification for the same
measurements via their public /api/v1/measurements API, compare booleans
against CLIO's verdict -- has only ever been run by hand, once per
incident. This script turns that method into reusable, resumable
infrastructure. Only steps 1-4 of ADR-0013 are built here: the harness
(this file), the dispatch-only workflow, and two reminder hooks. The
three baseline audits (whatsapp/telegram/dnscheck) and enabling the cron
are separate, later sessions.

TWO CORRECTIONS FOUND VERIFYING AGAINST THE LIVE SCHEMA BEFORE WRITING
ANY CODE (see reports.md for the full session account; both are
load-bearing, not cosmetic)
------------------------------------------------------------------------
  1. report_id is NOT a column of the published verdict table
     (int.ooni_measurement_verdicts) -- it lives only in
     stg.ooni_measurements, joined here on measurement_id.
  2. OONI's API returns ONE RESULT PER (report_id, input) PAIR, not one
     result per report_id. A single-input test (signal, whatsapp,
     telegram, psiphon) has exactly one result per report_id (input is
     null), but a multi-input test (dnscheck: one input per resolver
     tested) returns many -- a live dnscheck fetch during this build
     returned 42 results for one report_id. Every fetch/compare/match
     step below keys off (report_id, input), never report_id alone, or
     multi-input tests silently under-match.

The verdict-vocabulary mapping (config/verdict_mapping.yml) is also
GLOBAL, not per-test-type, for the same reason: CLIO's ooni_verdict
column has one shared accepted_values check (OK/CONFIRMED/ANOMALOUS/
FAILED) across every test_name, not a per-test vocabulary -- confirmed
against the live @bruin header before this was written. See that file's
own header for the full reasoning, including why its precedence
(CONFIRMED > FAILED > ANOMALOUS > OK) reuses TD-93's already-validated
rule rather than a newly guessed one.

MODES
-----
  baseline  -- one-off, wide sample (--strategy full or --strategy
              stratified) for a dedicated per-test-type baseline audit
              session (separate, later relay prompts -- this session
              only builds the strategy, does not run it against real
              data at baseline scale).
  monitor   -- the panel (config/panel.json) plus a rotating sample of
              signature cells not recently covered (config/
              coverage_log.json). This is what the scheduled workflow
              will run once the cron is enabled (a later relay prompt).

RATE LIMIT
----------
OONI's public API is rate-limited to roughly 1 request/second in
practice (a measured constraint, not a documented SLA). Every fetch in
this script sleeps RATE_LIMIT_SECONDS between report_id calls,
sequentially -- no concurrency.

RESUMABILITY -- two different persistent files, not to be confused
------------------------------------------------------------------
  - a per-run FETCH CHECKPOINT (.checkpoints/<test_type>_<mode>.json,
    gitignored): which report_ids THIS run has already fetched from
    OONI, so an interrupted run resumes without re-fetching or
    re-spending the rate-limit budget already used.
  - the CROSS-RUN COVERAGE LOG (config/coverage_log.json, versioned):
    which (test_type, clio_verdict, failure_type) signature cells have
    been sampled, and when, across ALL past monitor runs -- steers the
    rotation, does not affect within-run fetch skipping.

EXIT CODES
----------
    0  PASS -- no new disagreement signatures, panel unchanged
    1  new, non-allowlisted disagreement signature found
    2  panel regression -- CLIO's own verdict changed on a panel row
    3  panel external drift -- OONI's real answer changed on a panel row
    4  INCONCLUSIVE -- fetch error rate exceeded 20%, results not trusted
    5  operational error (BigQuery, config, or CLI usage failure)
If more than one condition applies, the returned code follows THIS
precedence, most severe first -- NOT numeric order: INCONCLUSIVE (4, an
untrustworthy fetch rate suppresses everything computed from it) >
PANEL_REGRESSION (2) > NEW_DISAGREEMENT (1) > PANEL_EXTERNAL_DRIFT (3) >
OK (0). Every condition found is still logged regardless of which code is
returned.

USAGE
-----
    python Bruin/scripts/agreement_check/ooni_agreement_check.py \\
        --test-type signal --mode monitor

    python Bruin/scripts/agreement_check/ooni_agreement_check.py \\
        --test-type dnscheck --mode baseline --strategy stratified

    # see what would be sampled, touch neither the OONI API nor BigQuery
    python Bruin/scripts/agreement_check/ooni_agreement_check.py \\
        --test-type signal --mode monitor --dry-run

PANEL ENTRY SCHEMA (config/panel.json, populated by later baseline
sessions, not by this one)
------------------------------------------------------------------------
    {
      "test_name": "signal",
      "measurement_id": "...",
      "report_id": "...",
      "input": null,
      "clio_verdict": "ANOMALOUS",
      "ooni_anomaly": true,
      "ooni_confirmed": false,
      "ooni_failure": false,
      "recorded_at": "2026-08-20T00:00:00Z"
    }

The audit.ooni_agreement_runs table this script writes to lives OUTSIDE
Bruin's DAG on purpose -- no Bruin asset declares it, so it can never
trip the ADR-0005 staleness check or appear in `bruin validate`'s scope.

TD-101 (dnscheck characterization, added after the initial TD-100 build):
every run also writes one row PER SAMPLED MEASUREMENT to
audit.ooni_agreement_findings (same outside-the-DAG reasoning), covering
every outcome -- AGREEMENT/DISAGREEMENT/UNSCORED/UNMATCHED/PANEL -- not
just disagreements, plus OONI's raw booleans/scores.accuracy and the
per-test-type CLIO driver-column value (DRIVER_COLUMN_BY_TEST_TYPE), so a
later analytical session can characterize a test type's disagreement
shape without re-spending the OONI API's ~1 req/sec budget. Also new:
--strategy stratified's second dimension is test-type-aware
(stratify_expr) rather than always FAILURE_TYPE_SQL -- dnscheck
stratifies by its own dnscheck_bootstrap_failure value instead, since
FAILURE_TYPE_SQL always resolves to the literal 'none' for dnscheck (its
five inputs are never populated for this test type -- that IS TD-101's
finding), which previously hid every distinct failure value inside one
bucket per verdict.
"""

import argparse
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml
from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                     stream=sys.stdout)
log = logging.getLogger("ooni_agreement_check")

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "config"
MAPPING_PATH = CONFIG_DIR / "verdict_mapping.yml"
PANEL_PATH = CONFIG_DIR / "panel.json"
COVERAGE_LOG_PATH = CONFIG_DIR / "coverage_log.json"
ALLOWLIST_PATH = SCRIPT_DIR / "allowlist.yml"
CHECKPOINT_DIR = SCRIPT_DIR / ".checkpoints"

VERDICT_TABLE = "int.ooni_measurement_verdicts"
MEASUREMENTS_TABLE = "stg.ooni_measurements"
SUMMARY_TABLE = "stg.ooni_measurement_summary"
AUDIT_DATASET = "audit"
AUDIT_TABLE = "audit.ooni_agreement_runs"
AUDIT_FINDINGS_TABLE = "audit.ooni_agreement_findings"
BQ_LOCATION = "us-central1"  # matches int./stg. datasets, confirmed live before writing DDL

# TD-101 (dnscheck characterization): the per-test-type column in
# stg.ooni_measurement_summary that drives (or, for dnscheck, currently
# fails to fully drive) that test's classification -- persisted per finding
# row so a later session can analyze it without re-fetching from OONI's
# rate-limited API. Confirmed live via INFORMATION_SCHEMA.COLUMNS before
# writing this. Deliberately incomplete: only test types this project has
# already investigated (dnscheck via TD-101, the others via TD-91/TD-93)
# have a wired driver column; any other test_type gets NULL, which is
# correct ("not applicable"/"not yet characterized"), not a bug.
DRIVER_COLUMN_BY_TEST_TYPE = {
    "dnscheck": "dnscheck_bootstrap_failure",
    "signal": "signal_backend_failure",
    "whatsapp": "whatsapp_web_failure",
    "telegram": "telegram_web_failure",
    "psiphon": "psiphon_failure",
}

OONI_API_URL = "https://api.ooni.org/api/v1/measurements"
RATE_LIMIT_SECONDS = 1.05
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2.0
INCONCLUSIVE_ERROR_RATE = 0.20

ROTATING_SAMPLE_PER_CELL = 10
ROTATING_SAMPLE_MAX_CELLS = 20  # caps a monitor run near ~200 report_ids, ~3.5 min at the rate limit
STRATIFIED_PER_CELL = 25
STRATIFIED_CATCHALL = 1000

EXIT_OK = 0
EXIT_NEW_DISAGREEMENT = 1
EXIT_PANEL_REGRESSION = 2
EXIT_PANEL_EXTERNAL_DRIFT = 3
EXIT_INCONCLUSIVE = 4
EXIT_OPERATIONAL = 5

# Derived per-row failure-type expression, shared by every sampling query
# below. The verdict table has no single failure_type column; this
# collapses the five real, mutually-exclusive-in-practice raw signal
# columns (confirmed live via INFORMATION_SCHEMA.COLUMNS before writing
# this) into one string for stratified-cell grouping and disagreement
# signatures. Columns are qualified `v.` because every query below now also
# joins stg.ooni_measurement_summary (aliased `s`), which has its own,
# same-named psiphon_failure/measurement_failure/signal_legacy_endpoint_
# nxdomain_only columns -- unqualified references would be ambiguous once
# both tables are in scope.
FAILURE_TYPE_SQL = """
  CASE
    WHEN v.psiphon_failure IS NOT NULL
      THEN CONCAT('psiphon_failure:', v.psiphon_failure)
    WHEN v.signal_legacy_endpoint_nxdomain_only IS TRUE
      THEN 'signal_legacy_nxdomain'
    WHEN v.control_failure IS NOT NULL
      THEN CONCAT('control_failure:', v.control_failure)
    WHEN v.web_blocking_type IS NOT NULL
      THEN CONCAT('web_blocking_type:', v.web_blocking_type)
    WHEN v.measurement_failure IS NOT NULL
      THEN CONCAT('measurement_failure:', v.measurement_failure)
    ELSE 'none'
  END
""".strip()


def stratify_expr(test_type: str) -> str:
    """The SQL expression used as the second stratification dimension for
    --strategy stratified and for monitor mode's rotating-sample cells.

    Defaults to the shared FAILURE_TYPE_SQL above. TD-101 Task 4a: dnscheck
    gets its own driver-column-based expression instead, because
    FAILURE_TYPE_SQL always collapses to the literal 'none' for dnscheck --
    none of its five inputs are ever populated for this test type, which IS
    TD-101's own finding -- so using it as the stratification key previously
    hid every distinct dnscheck_bootstrap_failure value inside one bucket
    per ooni_verdict (2 cells total: OK+none, ANOMALOUS+none, exactly what
    the prior session's baseline --dry-run reported). NULL is normalized to
    the literal string '(null)' so it sorts and groups as its own cell
    rather than requiring IS NOT DISTINCT FROM handling downstream.
    """
    if test_type == "dnscheck":
        return "IFNULL(s.dnscheck_bootstrap_failure, '(null)')"
    return FAILURE_TYPE_SQL


# --------------------------------------------------------------------------
# config I/O
# --------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    if not path.exists():
        log.error("config file not found: %s", path)
        sys.exit(EXIT_OPERATIONAL)
    return yaml.safe_load(path.read_text()) or {}


def load_json(path: Path) -> dict:
    if not path.exists():
        log.error("config file not found: %s", path)
        sys.exit(EXIT_OPERATIONAL)
    return json.loads(path.read_text())


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=False) + "\n")


def ooni_label(anomaly: bool, confirmed: bool, failure: bool) -> str:
    """Resolve OONI's three non-exclusive booleans to one label, per
    config/verdict_mapping.yml's precedence (CONFIRMED > FAILED >
    ANOMALOUS > OK) -- TD-93's already-validated rule, reused verbatim."""
    if confirmed:
        return "CONFIRMED"
    if failure:
        return "FAILED"
    if anomaly:
        return "ANOMALOUS"
    return "OK"


# --------------------------------------------------------------------------
# BigQuery sampling (test_type/verdict/failure_type always passed as query
# parameters, never string-interpolated -- failure_type in particular can
# carry arbitrary probe-reported error text, e.g. psiphon_failure values
# like "clientlib: tunnel establishment timeout", which would break a
# naive quoted string literal)
# --------------------------------------------------------------------------

def bq_client(project_id: str) -> bigquery.Client:
    return bigquery.Client(project=project_id, location=BQ_LOCATION)


def run_query(client: bigquery.Client, sql: str, params: list | None = None):
    job_config = bigquery.QueryJobConfig(query_parameters=params or [])
    return client.query(sql, job_config=job_config)


def rows_to_dicts(query_job) -> list:
    return [dict(r.items()) for r in query_job.result()]


def _select_cols(test_type: str) -> str:
    """Shared SELECT list: sample-key columns (measurement_id/test_name/
    ooni_verdict/failure_type/report_id/input, as before) plus the extra
    per-row context TD-101 Task 1's findings table needs -- probe_asn,
    country, measurement_date (all already on the verdict table `v`), and
    probe_version/clio_driver_value (from the newly-joined `s` =
    stg.ooni_measurement_summary). clio_driver_value is NULL for any
    test_type not yet in DRIVER_COLUMN_BY_TEST_TYPE -- correct, not a bug.
    """
    driver_col = DRIVER_COLUMN_BY_TEST_TYPE.get(test_type)
    driver_expr = f"s.{driver_col}" if driver_col else "CAST(NULL AS STRING)"
    return f"""
        v.measurement_id, v.test_name, v.ooni_verdict, v.probe_asn,
        v.country, v.measurement_date,
        {FAILURE_TYPE_SQL} AS failure_type,
        {driver_expr} AS clio_driver_value,
        s.test_version AS probe_version,
        m.report_id, m.input
    """


def _from_joins(project_id: str) -> str:
    return f"""
      FROM `{project_id}.{VERDICT_TABLE}` v
      JOIN `{project_id}.{MEASUREMENTS_TABLE}` m
        ON m.measurement_id = v.measurement_id
      LEFT JOIN `{project_id}.{SUMMARY_TABLE}` s
        ON s.measurement_id = v.measurement_id
    """


def sql_full_sample(project_id: str, test_type: str) -> str:
    return f"""
      SELECT {_select_cols(test_type)}
      {_from_joins(project_id)}
      WHERE v.test_name = @test_type
        AND m.report_id IS NOT NULL
    """


def sql_stratified_cells(project_id: str, test_type: str) -> str:
    return f"""
      SELECT
        v.ooni_verdict, {stratify_expr(test_type)} AS failure_type, COUNT(*) AS n
      {_from_joins(project_id)}
      WHERE v.test_name = @test_type
        AND m.report_id IS NOT NULL
      GROUP BY 1, 2
      ORDER BY n DESC
    """


def sql_cell_sample(project_id: str, test_type: str, limit: int) -> str:
    # limit is embedded directly (BigQuery Standard SQL LIMIT cannot take a
    # query parameter); always an already-validated int from min(N, cell["n"]).
    return f"""
      SELECT {_select_cols(test_type)}
      {_from_joins(project_id)}
      WHERE v.test_name = @test_type
        AND m.report_id IS NOT NULL
        AND v.ooni_verdict IS NOT DISTINCT FROM @ooni_verdict
        AND ({stratify_expr(test_type)}) = @failure_type
      ORDER BY RAND()
      LIMIT {limit}
    """


def sql_uniform_sample(project_id: str, test_type: str, limit: int) -> str:
    return f"""
      SELECT {_select_cols(test_type)}
      {_from_joins(project_id)}
      WHERE v.test_name = @test_type
        AND m.report_id IS NOT NULL
      ORDER BY RAND()
      LIMIT {limit}
    """


def cell_params(test_type: str, ooni_verdict, failure_type: str) -> list:
    return [
        bigquery.ScalarQueryParameter("test_type", "STRING", test_type),
        bigquery.ScalarQueryParameter("ooni_verdict", "STRING", ooni_verdict),
        bigquery.ScalarQueryParameter("failure_type", "STRING", failure_type),
    ]


def sample_baseline_full(client, project_id, test_type) -> list:
    log.info("baseline/full: pulling every sampled row for test_type=%s "
              "-- this can be large", test_type)
    params = [bigquery.ScalarQueryParameter("test_type", "STRING", test_type)]
    rows = rows_to_dicts(run_query(client, sql_full_sample(project_id, test_type), params))
    log.info("baseline/full: %d row(s)", len(rows))
    return rows


def sample_baseline_stratified(client, project_id, test_type) -> list:
    params = [bigquery.ScalarQueryParameter("test_type", "STRING", test_type)]
    cells = rows_to_dicts(run_query(client, sql_stratified_cells(project_id, test_type), params))
    log.info("baseline/stratified: %d signature cell(s) enumerated for "
              "test_type=%s", len(cells), test_type)
    sampled = []
    for cell in cells:
        n = min(STRATIFIED_PER_CELL, cell["n"])
        sql = sql_cell_sample(project_id, test_type, n)
        cparams = cell_params(test_type, cell["ooni_verdict"], cell["failure_type"])
        rows = rows_to_dicts(run_query(client, sql, cparams))
        if len(rows) < n:
            log.warning("baseline/stratified: cell ooni_verdict=%s failure_type=%s "
                        "only had %d live row(s), short of the requested %d",
                        cell["ooni_verdict"], cell["failure_type"], len(rows), n)
        sampled.extend(rows)

    catchall_sql = sql_uniform_sample(project_id, test_type, STRATIFIED_CATCHALL)
    catchall = rows_to_dicts(run_query(client, catchall_sql, params))
    log.info("baseline/stratified: %d cell-sampled row(s) + %d catch-all "
              "row(s) sampled (deduped below)", len(sampled), len(catchall))

    by_id = {r["measurement_id"]: r for r in sampled + catchall}
    log.info("baseline/stratified: %d unique row(s) after dedup", len(by_id))
    return list(by_id.values())


def sample_monitor(client, project_id, test_type, coverage_log) -> list:
    panel = load_json(PANEL_PATH)
    panel_rows = [e for e in panel.get("entries", []) if e.get("test_name") == test_type]
    if panel_rows:
        log.info("monitor: %d panel entry/entries for test_type=%s", len(panel_rows), test_type)
    else:
        log.info("monitor: panel is empty for test_type=%s (expected in this "
                  "build session -- populated by the later baseline sessions)", test_type)

    params = [bigquery.ScalarQueryParameter("test_type", "STRING", test_type)]
    cells = rows_to_dicts(run_query(client, sql_stratified_cells(project_id, test_type), params))

    def cell_key(c):
        return f"{test_type}|{c['ooni_verdict']}|{c['failure_type']}"

    cells_seen = coverage_log.setdefault("cells", {})

    def last_sampled(c):
        entry = cells_seen.get(cell_key(c))
        return entry["last_sampled_at"] if entry else ""  # empty string sorts first: never sampled

    cells.sort(key=last_sampled)
    chosen = cells[:ROTATING_SAMPLE_MAX_CELLS]
    log.info("monitor: rotating sample choosing %d of %d live cell(s) "
              "(least-recently-covered first)", len(chosen), len(cells))

    rotating_rows = []
    for cell in chosen:
        n = min(ROTATING_SAMPLE_PER_CELL, cell["n"])
        sql = sql_cell_sample(project_id, test_type, n)
        cparams = cell_params(test_type, cell["ooni_verdict"], cell["failure_type"])
        rows = rows_to_dicts(run_query(client, sql, cparams))
        rotating_rows.extend(rows)
        cells_seen[cell_key(cell)] = {
            "test_type": test_type,
            "ooni_verdict": cell["ooni_verdict"],
            "failure_type": cell["failure_type"],
            "last_sampled_at": datetime.now(timezone.utc).isoformat(),
            "sampled_count": len(rows),
        }

    # Panel entries come from config/panel.json, not a live BQ row, so they
    # don't carry the Task 1 findings-table context columns (probe_asn,
    # country, measurement_date, clio_driver_value, probe_version) --
    # explicitly None here rather than absent, so every row compare() sees
    # has the same shape regardless of source.
    panel_as_rows = [
        {
            "measurement_id": e["measurement_id"], "test_name": e["test_name"],
            "ooni_verdict": e["clio_verdict"], "failure_type": None,
            "report_id": e["report_id"], "input": e.get("input"),
            "probe_asn": None, "country": None, "measurement_date": None,
            "clio_driver_value": None, "probe_version": None,
            "_is_panel": True,
        }
        for e in panel_rows
    ]
    log.info("monitor: %d rotating-sample row(s) + %d panel row(s)",
              len(rotating_rows), len(panel_as_rows))
    return panel_as_rows + rotating_rows


# --------------------------------------------------------------------------
# OONI API fetch (rate-limited, retried, paginated, checkpointed)
# --------------------------------------------------------------------------

def checkpoint_path(test_type: str, mode: str) -> Path:
    return CHECKPOINT_DIR / f"{test_type}_{mode}.json"


def load_checkpoint(test_type: str, mode: str) -> dict:
    p = checkpoint_path(test_type, mode)
    if p.exists():
        return json.loads(p.read_text())
    return {"fetched": {}, "errored": []}


def save_checkpoint(test_type: str, mode: str, state: dict) -> None:
    p = checkpoint_path(test_type, mode)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2))


def _backoff_sleep(attempt: int, reason) -> None:
    sleep_for = RETRY_BACKOFF_BASE ** attempt
    log.warning("retry %d/%d (%s); sleeping %.1fs", attempt, MAX_RETRIES, reason, sleep_for)
    time.sleep(sleep_for)


def _get_with_retry(url: str, params: dict | None):
    """GET with retry/backoff on transient failures only (network errors,
    429, 5xx). Any other 4xx fails immediately -- retrying a permanent
    client error just burns the rate-limit budget for nothing."""
    attempt = 0
    while True:
        try:
            resp = requests.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            attempt += 1
            if attempt > MAX_RETRIES:
                raise
            _backoff_sleep(attempt, exc)
            continue
        if resp.status_code == 429 or resp.status_code >= 500:
            attempt += 1
            if attempt > MAX_RETRIES:
                resp.raise_for_status()
            _backoff_sleep(attempt, f"status {resp.status_code}")
            continue
        resp.raise_for_status()
        return resp


def fetch_report(report_id: str) -> list:
    """Fetch every result for one report_id, following pagination via
    metadata.next_url. Raises on exhausted retries or a permanent HTTP
    error -- the caller counts that as a fetch error for this report_id."""
    results = []
    url = OONI_API_URL
    params = {"report_id": report_id}
    while url:
        resp = _get_with_retry(url, params)
        body = resp.json()
        results.extend(body.get("results", []))
        url = body.get("metadata", {}).get("next_url")
        params = None  # next_url already carries every query param
        if url:
            time.sleep(RATE_LIMIT_SECONDS)
    return results


def fetch_all(sample_rows: list, test_type: str, mode: str, dry_run: bool) -> tuple:
    """Fetch OONI's real results for every unique report_id in the sample.
    Returns (results_by_report_id, fetch_error_count, total_report_ids)."""
    unique_report_ids = sorted({r["report_id"] for r in sample_rows if r.get("report_id")})
    log.info("fetch: %d unique report_id(s) to fetch (sample had %d row(s))",
              len(unique_report_ids), len(sample_rows))

    if dry_run:
        log.info("--dry-run: not calling the OONI API. Would fetch %d report_id(s).",
                  len(unique_report_ids))
        return {}, 0, len(unique_report_ids)

    state = load_checkpoint(test_type, mode)
    fetched = state["fetched"]
    errored = set(state["errored"])

    remaining = [rid for rid in unique_report_ids if rid not in fetched and rid not in errored]
    if fetched or errored:
        log.info("resuming from checkpoint: %d already fetched, %d already "
                  "errored, %d remaining", len(fetched), len(errored), len(remaining))

    for i, report_id in enumerate(remaining, 1):
        try:
            results = fetch_report(report_id)
            fetched[report_id] = results
        except requests.RequestException as exc:
            log.error("fetch failed for report_id=%s after retries: %s", report_id, exc)
            errored.add(report_id)
        if i % 10 == 0 or i == len(remaining):
            state["errored"] = sorted(errored)
            save_checkpoint(test_type, mode, state)
        time.sleep(RATE_LIMIT_SECONDS)

    state["errored"] = sorted(errored)
    save_checkpoint(test_type, mode, state)

    error_count = len(errored & set(unique_report_ids))

    # Reaching here means the fetch loop ran to completion (no crash, no
    # KeyboardInterrupt) -- the checkpoint has served its only purpose
    # (surviving an interruption mid-run) and must NOT persist into the
    # next invocation. Without this, a later run's `remaining` filter would
    # skip every report_id already seen and `compare()` would silently
    # score against this run's stale cached OONI answers -- exactly
    # backwards for a guardrail whose job is catching OONI's answer
    # changing over time (exit 3) or CLIO regressing (exit 2). A genuine
    # interruption (process killed mid-loop) never reaches this line, so
    # its incrementally-saved checkpoint is untouched and still resumable.
    checkpoint_path(test_type, mode).unlink(missing_ok=True)

    return fetched, error_count, len(unique_report_ids)


# --------------------------------------------------------------------------
# compare + bucket
# --------------------------------------------------------------------------

def _base_finding(test_type: str, row: dict) -> dict:
    """The context columns shared by every findings row for TD-101 Task 1's
    audit.ooni_agreement_findings table, regardless of outcome. Populated
    from the sample row (see _select_cols); None for anything a panel row
    doesn't carry (see sample_monitor's panel_as_rows)."""
    measurement_date = row.get("measurement_date")
    return {
        "test_type": test_type,
        "report_id": row.get("report_id"),
        "input": row.get("input"),
        "measurement_id": row.get("measurement_id"),
        "clio_verdict": row.get("ooni_verdict"),
        "clio_driver_value": row.get("clio_driver_value"),
        "probe_asn": row.get("probe_asn"),
        "country": row.get("country"),
        "measurement_date": str(measurement_date) if measurement_date is not None else None,
        "probe_version": row.get("probe_version"),
        "measurement_uid": None,
        "ooni_verdict": None,
        "ooni_anomaly": None,
        "ooni_confirmed": None,
        "ooni_failure": None,
        "ooni_scores_accuracy": None,
        "outcome": None,
        "disagreement_signature": None,
        "allowlist_hit": False,
        "_sig": None,  # internal only, stripped before the BQ insert -- see write_findings
    }


def compare(sample_rows: list, fetched: dict, mapping: dict, test_type: str) -> dict:
    """Compare every sampled row's stored CLIO verdict against OONI's real,
    live classification for the same (report_id, input). Returns both the
    existing aggregate summary structures (unchanged shape, for
    audit.ooni_agreement_runs and the console log) and, new for TD-101 Task
    1, a `findings` list with one row per sample_rows entry -- every
    outcome (AGREEMENT/DISAGREEMENT/UNSCORED/UNMATCHED/PANEL), not just
    disagreements -- for audit.ooni_agreement_findings."""
    unscored_values = set(mapping.get("unscored_clio_values") or [])
    agreement = 0
    disagreements: dict = {}
    disagreement_examples: dict = {}
    unscored = 0
    unmatched = 0
    panel_results = []
    findings = []

    for row in sample_rows:
        clio_verdict = row.get("ooni_verdict")
        is_panel = row.get("_is_panel", False)
        report_id = row.get("report_id")
        ooni_results = fetched.get(report_id)
        finding = _base_finding(test_type, row)

        if ooni_results is None:
            unmatched += 1
            finding["outcome"] = "UNMATCHED"
            findings.append(finding)
            continue

        match = next(
            (r for r in ooni_results if (r.get("input") or None) == (row.get("input") or None)),
            None,
        )
        if match is None:
            unmatched += 1
            finding["outcome"] = "UNMATCHED"
            findings.append(finding)
            continue

        ooni_verdict = ooni_label(
            bool(match.get("anomaly")), bool(match.get("confirmed")), bool(match.get("failure")),
        )
        finding.update({
            "measurement_uid": match.get("measurement_uid"),
            "ooni_verdict": ooni_verdict,
            "ooni_anomaly": bool(match.get("anomaly")),
            "ooni_confirmed": bool(match.get("confirmed")),
            "ooni_failure": bool(match.get("failure")),
            "ooni_scores_accuracy": (match.get("scores") or {}).get("accuracy"),
        })

        if is_panel:
            finding["outcome"] = "PANEL"
            findings.append(finding)
            panel_results.append({
                "measurement_id": row["measurement_id"],
                "clio_verdict_now": clio_verdict,
                "ooni_anomaly_now": bool(match.get("anomaly")),
                "ooni_confirmed_now": bool(match.get("confirmed")),
                "ooni_failure_now": bool(match.get("failure")),
                "ooni_verdict_now": ooni_verdict,
            })
            continue

        if clio_verdict is None or clio_verdict in unscored_values:
            unscored += 1
            finding["outcome"] = "UNSCORED"
            findings.append(finding)
            continue

        if clio_verdict == ooni_verdict:
            agreement += 1
            finding["outcome"] = "AGREEMENT"
            findings.append(finding)
            continue

        sig = (
            row["test_name"], clio_verdict,
            bool(match.get("anomaly")), bool(match.get("confirmed")), bool(match.get("failure")),
            row.get("input") or None,
        )
        disagreements[sig] = disagreements.get(sig, 0) + 1
        disagreement_examples.setdefault(sig, row["measurement_id"])
        finding["outcome"] = "DISAGREEMENT"
        finding["disagreement_signature"] = json.dumps(list(sig))
        finding["_sig"] = sig
        findings.append(finding)

    return {
        "agreement_count": agreement,
        "unscored_count": unscored,
        "unmatched_count": unmatched,
        "disagreements": disagreements,
        "disagreement_examples": disagreement_examples,
        "panel_results": panel_results,
        "findings": findings,
    }


def serialize_disagreements(disagreements: dict, examples: dict) -> list:
    return [
        {
            "test_name": sig[0], "clio_verdict": sig[1],
            "ooni_anomaly": sig[2], "ooni_confirmed": sig[3], "ooni_failure": sig[4],
            "hostname_or_target": sig[5],
            "count": count,
            "example_measurement_id": examples.get(sig),
        }
        for sig, count in disagreements.items()
    ]


# --------------------------------------------------------------------------
# allowlist
# --------------------------------------------------------------------------

def load_allowlist() -> list:
    return load_yaml(ALLOWLIST_PATH).get("entries") or []


def allowlist_match(entry: dict, sig: tuple) -> bool:
    test_name, clio_verdict, anomaly, confirmed, failure, hostname = sig
    if entry.get("test_name") != test_name:
        return False
    if entry.get("clio_verdict") != clio_verdict:
        return False
    if bool(entry.get("ooni_anomaly")) != anomaly:
        return False
    if bool(entry.get("ooni_confirmed")) != confirmed:
        return False
    if bool(entry.get("ooni_failure")) != failure:
        return False
    eh = entry.get("hostname_or_target")
    if eh != "*" and eh != hostname:
        return False
    return True


def check_allowlist(disagreements: dict, allowlist: list) -> tuple:
    new_sigs: dict = {}
    allowlisted: dict = {}
    for sig, count in disagreements.items():
        hit = next((e for e in allowlist if allowlist_match(e, sig)), None)
        if hit:
            allowlisted[sig] = (count, hit)
        else:
            new_sigs[sig] = count
    return new_sigs, allowlisted


# --------------------------------------------------------------------------
# panel check
# --------------------------------------------------------------------------

def check_panel(panel: dict, panel_results: list) -> tuple:
    entries_by_id = {e["measurement_id"]: e for e in panel.get("entries", [])}
    regressions = []
    drifts = []
    for pr in panel_results:
        entry = entries_by_id.get(pr["measurement_id"])
        if not entry:
            continue
        if pr["clio_verdict_now"] != entry["clio_verdict"]:
            regressions.append({
                "measurement_id": pr["measurement_id"],
                "recorded_clio_verdict": entry["clio_verdict"],
                "current_clio_verdict": pr["clio_verdict_now"],
            })
        recorded_ooni = ooni_label(
            bool(entry.get("ooni_anomaly")), bool(entry.get("ooni_confirmed")),
            bool(entry.get("ooni_failure")),
        )
        if pr["ooni_verdict_now"] != recorded_ooni:
            drifts.append({
                "measurement_id": pr["measurement_id"],
                "recorded_ooni_verdict": recorded_ooni,
                "current_ooni_verdict": pr["ooni_verdict_now"],
            })
    return regressions, drifts


# --------------------------------------------------------------------------
# audit table (deliberately outside the Bruin DAG -- see module docstring)
# --------------------------------------------------------------------------

def ensure_audit_table(client: bigquery.Client, project_id: str) -> None:
    client.query(
        f"CREATE SCHEMA IF NOT EXISTS `{project_id}.{AUDIT_DATASET}` "
        f"OPTIONS(location='{BQ_LOCATION}')"
    ).result()
    client.query(f"""
        CREATE TABLE IF NOT EXISTS `{project_id}.{AUDIT_TABLE}` (
          run_id STRING,
          run_timestamp TIMESTAMP,
          test_type STRING,
          mode STRING,
          strategy STRING,
          sample_size INT64,
          fetched_report_ids INT64,
          agreement_count INT64,
          disagreement_count INT64,
          unscored_count INT64,
          unmatched_count INT64,
          disagreement_signatures STRING,
          panel_status STRING,
          fetch_error_rate FLOAT64,
          exit_code INT64
        )
    """).result()
    # CREATE TABLE IF NOT EXISTS is a no-op against a table that already
    # exists under an older schema -- confirmed live during this session:
    # TD-100's own earlier run had already created this table without
    # run_id, and the CREATE above silently did nothing to it, so the very
    # first write_run() call under TD-101 failed ("no such field: run_id.").
    # This ALTER is the actual migration; idempotent and safe to run every
    # invocation.
    client.query(f"""
        ALTER TABLE `{project_id}.{AUDIT_TABLE}`
        ADD COLUMN IF NOT EXISTS run_id STRING
    """).result()


def write_run(client: bigquery.Client, project_id: str, row: dict) -> None:
    ensure_audit_table(client, project_id)
    errors = client.insert_rows_json(f"{project_id}.{AUDIT_TABLE}", [row])
    if errors:
        log.error("failed to write run row to %s: %s", AUDIT_TABLE, errors)
    else:
        log.info("wrote run summary to %s.%s", project_id, AUDIT_TABLE)


def ensure_findings_table(client: bigquery.Client, project_id: str) -> None:
    """TD-101 Task 1: per-measurement findings, one row per sampled row per
    run, written in addition to (never instead of) the run-summary row
    above. Same DAG-exclusion reasoning as audit.ooni_agreement_runs -- no
    Bruin asset declares this table, so it can never trip the ADR-0005
    staleness check or appear in `bruin validate`'s scope."""
    client.query(
        f"CREATE SCHEMA IF NOT EXISTS `{project_id}.{AUDIT_DATASET}` "
        f"OPTIONS(location='{BQ_LOCATION}')"
    ).result()
    client.query(f"""
        CREATE TABLE IF NOT EXISTS `{project_id}.{AUDIT_FINDINGS_TABLE}` (
          run_id STRING,
          test_type STRING,
          report_id STRING,
          input STRING,
          measurement_id STRING,
          measurement_uid STRING,
          clio_verdict STRING,
          ooni_verdict STRING,
          ooni_anomaly BOOL,
          ooni_confirmed BOOL,
          ooni_failure BOOL,
          ooni_scores_accuracy FLOAT64,
          clio_driver_value STRING,
          probe_asn INT64,
          country STRING,
          measurement_date DATE,
          probe_version STRING,
          outcome STRING,
          disagreement_signature STRING,
          allowlist_hit BOOL,
          fetched_at TIMESTAMP
        )
    """).result()


def write_findings(client: bigquery.Client, project_id: str, run_id: str,
                    findings: list, fetched_at: str) -> None:
    """Batched insert (BigQuery's streaming-insert API has practical
    per-request size limits, so 1,000-2,000-row baseline runs are chunked
    rather than sent in one call)."""
    if not findings:
        return
    ensure_findings_table(client, project_id)
    rows = []
    for f in findings:
        row = {k: v for k, v in f.items() if not k.startswith("_")}
        row["run_id"] = run_id
        row["fetched_at"] = fetched_at
        rows.append(row)

    batch_size = 500
    total_errors = 0
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        errors = client.insert_rows_json(f"{project_id}.{AUDIT_FINDINGS_TABLE}", batch)
        if errors:
            total_errors += len(errors)
            log.error("failed to write %d finding row(s) in batch starting at "
                      "%d: %s", len(errors), i, errors)
    if total_errors == 0:
        log.info("wrote %d finding row(s) to %s.%s", len(rows), project_id, AUDIT_FINDINGS_TABLE)
    else:
        log.error("wrote findings to %s.%s with %d row-level error(s) -- see above",
                  AUDIT_FINDINGS_TABLE, project_id, total_errors)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OONI agreement-check harness (TD-100/ADR-0013 steps 1-4): "
                    "sample CLIO's own OONI verdicts, fetch OONI's real "
                    "classification for the same measurements, compare, and "
                    "flag new disagreement signatures or panel drift.",
    )
    parser.add_argument("--test-type", required=True,
                        help="OONI test_name to check, e.g. signal, whatsapp, "
                             "telegram, dnscheck, psiphon")
    parser.add_argument("--mode", required=True, choices=["baseline", "monitor"])
    parser.add_argument("--strategy", choices=["full", "stratified"], default="stratified",
                        help="baseline mode only; ignored in monitor mode")
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCP_PROJECT_ID"),
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="show what would be sampled/fetched; no OONI API "
                             "calls, no BigQuery writes")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.project_id:
        log.error("no project id: pass --project-id or set GOOGLE_CLOUD_PROJECT")
        return EXIT_OPERATIONAL

    mapping = load_yaml(MAPPING_PATH)
    panel = load_json(PANEL_PATH)
    coverage_log = load_json(COVERAGE_LOG_PATH) if args.mode == "monitor" else {"cells": {}}

    client = bq_client(args.project_id)

    strategy = args.strategy if args.mode == "baseline" else None
    if args.mode == "baseline":
        if strategy == "full":
            sample_rows = sample_baseline_full(client, args.project_id, args.test_type)
        else:
            sample_rows = sample_baseline_stratified(client, args.project_id, args.test_type)
    else:
        sample_rows = sample_monitor(client, args.project_id, args.test_type, coverage_log)

    fetched, error_count, total_report_ids = fetch_all(
        sample_rows, args.test_type, args.mode, args.dry_run)

    if args.dry_run:
        log.info("--dry-run complete: sampled %d row(s), %d unique report_id(s). "
                  "No API calls, no BigQuery writes, no config files changed.",
                  len(sample_rows), total_report_ids)
        return EXIT_OK

    error_rate = error_count / total_report_ids if total_report_ids else 0.0
    inconclusive = error_rate > INCONCLUSIVE_ERROR_RATE

    run_id = uuid.uuid4().hex
    fetched_at = datetime.now(timezone.utc).isoformat()

    result = compare(sample_rows, fetched, mapping, args.test_type)
    allowlist = load_allowlist()
    new_disagreements, allowlisted = check_allowlist(result["disagreements"], allowlist)
    regressions, drifts = check_panel(panel, result["panel_results"])

    # TD-101 Task 1: backfill allowlist_hit on the per-row findings now that
    # the allowlist check has run (compare() itself doesn't see the
    # allowlist). allowlisted's keys are exactly the disagreement
    # signatures that matched; every finding's own "_sig" (None for any
    # non-DISAGREEMENT outcome) tells us which row to flag.
    allowlisted_sigs = set(allowlisted.keys())
    for f in result["findings"]:
        if f.get("_sig") is not None:
            f["allowlist_hit"] = f["_sig"] in allowlisted_sigs

    if args.mode == "monitor":
        save_json(COVERAGE_LOG_PATH, coverage_log)

    panel_entries_for_type = [e for e in panel.get("entries", []) if e.get("test_name") == args.test_type]
    if not panel_entries_for_type:
        panel_status = "EMPTY"
    elif regressions:
        panel_status = "REGRESSION"
    elif drifts:
        panel_status = "EXTERNAL_DRIFT"
    else:
        panel_status = "UNCHANGED"

    log.info(
        "RESULT test_type=%s mode=%s: agreement=%d disagreement=%d (new=%d "
        "allowlisted=%d) unscored=%d unmatched=%d fetch_error_rate=%.1f%% "
        "panel_status=%s",
        args.test_type, args.mode, result["agreement_count"],
        sum(result["disagreements"].values()), sum(new_disagreements.values()),
        sum(c for c, _ in allowlisted.values()), result["unscored_count"],
        result["unmatched_count"], error_rate * 100, panel_status,
    )

    for sig, count in new_disagreements.items():
        log.error(
            "NEW DISAGREEMENT SIGNATURE (x%d): test_name=%s clio_verdict=%s "
            "ooni(anomaly=%s,confirmed=%s,failure=%s) hostname_or_target=%s example=%s",
            count, *sig, result["disagreement_examples"].get(sig),
        )
    for entry_count, entry in allowlisted.values():
        log.info("ALLOWLISTED [%s] (x%d): %s", entry.get("td_ref"), entry_count, entry.get("reason"))
    for r in regressions:
        log.error("PANEL REGRESSION (CLIO-side): %s", r)
    for d in drifts:
        log.warning("PANEL EXTERNAL DRIFT (OONI-side): %s", d)

    if inconclusive:
        exit_code = EXIT_INCONCLUSIVE
        log.error("INCONCLUSIVE: fetch error rate %.1f%% exceeds the %.0f%% "
                  "threshold -- results below are not trusted.",
                  error_rate * 100, INCONCLUSIVE_ERROR_RATE * 100)
    elif regressions:
        exit_code = EXIT_PANEL_REGRESSION
    elif new_disagreements:
        exit_code = EXIT_NEW_DISAGREEMENT
    elif drifts:
        exit_code = EXIT_PANEL_EXTERNAL_DRIFT
    else:
        exit_code = EXIT_OK
        log.info("PASS: no new disagreement signatures, panel unchanged.")

    write_run(client, args.project_id, {
        "run_id": run_id,
        "run_timestamp": fetched_at,
        "test_type": args.test_type,
        "mode": args.mode,
        "strategy": strategy or "",
        "sample_size": len(sample_rows),
        "fetched_report_ids": total_report_ids - error_count,
        "agreement_count": result["agreement_count"],
        "disagreement_count": sum(result["disagreements"].values()),
        "unscored_count": result["unscored_count"],
        "unmatched_count": result["unmatched_count"],
        "disagreement_signatures": json.dumps(
            serialize_disagreements(result["disagreements"], result["disagreement_examples"])),
        "panel_status": panel_status,
        "fetch_error_rate": error_rate,
        "exit_code": exit_code,
    })

    # TD-101 Task 1: one row per sampled measurement, every outcome (not
    # just disagreements) -- written in addition to the run-summary row
    # above, never instead of it.
    write_findings(client, args.project_id, run_id, result["findings"], fetched_at)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
