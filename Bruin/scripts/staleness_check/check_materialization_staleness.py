"""
check_materialization_staleness.py
===================================
Materialization-staleness guardrail for the Bruin/BigQuery DAG (ADR-0005).

WHY THIS SCRIPT EXISTS
----------------------
This project has now hit the same failure category three separate times
(TD-38, TD-40, TD-54): an asset's *definition* or *upstream data* changes,
but a downstream table that depends on it is not rematerialized, leaving the
live warehouse in a silently inconsistent state -- downstream tables built
from upstream state that no longer exists. Bruin's DAG guarantees ordering
*within* a run, but nothing detects a partial cascade *between* runs.

This script makes that state visible and CI-enforceable:

    For every dependency edge (A depends on B) where both A and B are
    BigQuery table materializations, if B's last-modified time is newer
    than A's, then A was built from a version of B that has since been
    replaced -- A is stale relative to its own declared input.

Deliberately-accepted gaps (e.g. the TD-54/TD-49 hold on cascading the
post-TD-47 dnscheck volume into intelligence.protocol_signal_regimes) live
in staleness_allowlist.json next to this script, each entry carrying a TD
reference and a one-line reason. Allowlisted violations are reported but do
not fail the check; only NEW, undocumented staleness exits non-zero.

MECHANISM NOTES (verified 2026-07-05, see ADR-0005)
---------------------------------------------------
- The dependency graph comes from `bruin internal parse-pipeline`, which
  emits the whole pipeline as JSON in one call and works without .bruin.yml
  (parsing needs no connection config, so it runs in CI from a bare
  checkout). It is an *internal* bruin command, so its output shape is
  validated defensively below and the script exits 2 with a clear message
  if a bruin upgrade ever changes it.
- Last-modified timestamps come from each dataset's `__TABLES__` metatable
  (`last_modified_time`, epoch millis). Two seemingly-nicer alternatives
  were checked and do NOT work here: INFORMATION_SCHEMA.TABLES has no
  last-modified column at all, and the region-wide
  INFORMATION_SCHEMA.TABLE_STORAGE view is access-denied for this
  project's accounts.
- Only assets with type=bq.sql and materialization.type=table are
  monitored. Python assets are skipped because their declared names do not
  reliably map to BigQuery tables (e.g. load.ooni_to_gcs writes to GCS;
  the raw.* assets' declared dataset does not exist -- see TD-42), views
  are skipped because they read live and cannot be data-stale, and
  check-only assets (no materialization) produce no table to compare.
- No tolerance window is applied. Within a single `bruin run`, upstreams
  finish before downstreams start, so timestamps are correctly ordered;
  any inversion means the downstream genuinely was not rebuilt after its
  upstream changed. Caveat: rerunning an upstream with byte-identical
  output still bumps its timestamp and will flag downstreams -- that is
  accepted (the check cannot cheaply prove output equality; rematerialize
  the downstream or allowlist with a TD reference).

EXIT CODES
----------
    0  no violations, or every violation is allowlisted
    1  at least one NEW (non-allowlisted) stale edge
    2  operational error (bruin parse failed/changed shape, BigQuery
       unreachable, malformed allowlist)

USAGE
-----
    python Bruin/scripts/staleness_check/check_materialization_staleness.py \\
        [--project-id encoded-joy-485413-k5] \\
        [--pipeline-dir Bruin] \\
        [--allowlist Bruin/scripts/staleness_check/staleness_allowlist.json]

Defaults resolve relative to this file's location and the
GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID environment variables, so a bare
invocation works both in the Codespace and in CI.
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from google.cloud import bigquery

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
log = logging.getLogger("staleness_check")

SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_PIPELINE_DIR = SCRIPT_DIR.parents[1]  # Bruin/
DEFAULT_ALLOWLIST = SCRIPT_DIR / "staleness_allowlist.json"

EXIT_OK = 0
EXIT_NEW_VIOLATIONS = 1
EXIT_OPERATIONAL = 2


def parse_pipeline(pipeline_dir: Path) -> list[dict]:
    """Run `bruin internal parse-pipeline` and return the asset list.

    Validates the output shape defensively: this is an internal bruin
    command, so a CLI upgrade could change it without notice. Any shape
    surprise is an operational error (exit 2), never a silent pass.
    """
    try:
        proc = subprocess.run(
            ["bruin", "internal", "parse-pipeline", str(pipeline_dir)],
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        log.error("bruin CLI not found on PATH")
        sys.exit(EXIT_OPERATIONAL)
    except subprocess.CalledProcessError as exc:
        log.error("bruin internal parse-pipeline failed: %s", exc.stderr.strip())
        sys.exit(EXIT_OPERATIONAL)

    try:
        pipeline = json.loads(proc.stdout)
        assets = pipeline["assets"]
        assert isinstance(assets, list) and assets
        for a in assets:
            assert "name" in a and "type" in a
    except (json.JSONDecodeError, KeyError, AssertionError) as exc:
        log.error(
            "bruin internal parse-pipeline output did not match the expected "
            "shape (assets[].name/type/upstreams). The bruin CLI may have "
            "changed its internal output format -- see ADR-0005 mechanism "
            "notes. Parse error: %r",
            exc,
        )
        sys.exit(EXIT_OPERATIONAL)

    return assets


def monitored_assets(assets: list[dict]) -> tuple[dict[str, dict], list[tuple[str, str]]]:
    """Split assets into monitored (bq.sql table materializations) and
    skipped (everything whose declared name cannot be trusted to map to a
    comparable BigQuery table -- python assets, views, check-only assets)."""
    monitored: dict[str, dict] = {}
    skipped: list[tuple[str, str]] = []
    for a in assets:
        mat = (a.get("materialization") or {}).get("type") or ""
        if a["type"] == "bq.sql" and mat == "table":
            monitored[a["name"]] = a
        else:
            reason = f"type={a['type']}, materialization={mat or 'none'}"
            skipped.append((a["name"], reason))
    return monitored, skipped


def fetch_last_modified(client: bigquery.Client, project_id: str,
                        datasets: list[str]) -> dict[str, int]:
    """Return {dataset.table: last_modified_epoch_millis} for every table in
    the given datasets, via each dataset's __TABLES__ metatable."""
    union = "\nUNION ALL\n".join(
        f"SELECT '{ds}' AS ds, table_id, last_modified_time "
        f"FROM `{project_id}.{ds}.__TABLES__`"
        for ds in datasets
    )
    try:
        rows = client.query(union).result()
    except Exception as exc:  # operational, not a staleness finding
        log.error("BigQuery __TABLES__ metadata query failed: %s", exc)
        sys.exit(EXIT_OPERATIONAL)
    return {f"{r.ds}.{r.table_id}": int(r.last_modified_time) for r in rows}


def load_allowlist(path: Path) -> dict[tuple[str, str], dict]:
    """Load the allowlist; every entry must carry downstream, upstream, a
    TD reference, and a reason -- an entry without provenance is malformed."""
    if not path.exists():
        log.warning("allowlist file not found at %s -- treating as empty", path)
        return {}
    try:
        entries = json.loads(path.read_text())
        assert isinstance(entries, list)
        allow: dict[tuple[str, str], dict] = {}
        for e in entries:
            for field in ("downstream", "upstream", "td_ref", "reason"):
                assert e.get(field), f"allowlist entry missing '{field}': {e}"
            allow[(e["downstream"], e["upstream"])] = e
        return allow
    except (json.JSONDecodeError, AssertionError) as exc:
        log.error("malformed allowlist %s: %s", path, exc)
        sys.exit(EXIT_OPERATIONAL)


def fmt_ts(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[2])
    parser.add_argument(
        "--project-id",
        default=os.environ.get("GOOGLE_CLOUD_PROJECT")
        or os.environ.get("GCP_PROJECT_ID"),
        help="GCP project id (default: GOOGLE_CLOUD_PROJECT / GCP_PROJECT_ID env)",
    )
    parser.add_argument("--pipeline-dir", type=Path, default=DEFAULT_PIPELINE_DIR)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    args = parser.parse_args()

    if not args.project_id:
        log.error("no project id: pass --project-id or set GOOGLE_CLOUD_PROJECT")
        return EXIT_OPERATIONAL

    assets = parse_pipeline(args.pipeline_dir)
    monitored, skipped = monitored_assets(assets)
    allowlist = load_allowlist(args.allowlist)

    log.info(
        "parsed %d assets: %d monitored (bq.sql table), %d skipped",
        len(assets), len(monitored), len(skipped),
    )
    for name, reason in skipped:
        log.debug("skipped %s (%s)", name, reason)

    datasets = sorted({n.split(".")[0] for n in monitored})
    client = bigquery.Client(project=args.project_id)
    last_modified = fetch_last_modified(client, args.project_id, datasets)

    # A monitored asset whose table does not exist is reported but does not
    # fail the check (it may be brand-new and legitimately not yet run);
    # its edges cannot be evaluated either way.
    missing = sorted(n for n in monitored if n not in last_modified)
    for name in missing:
        log.warning("monitored asset has no live table: %s", name)

    checked_edges = 0
    skipped_edges = 0
    new_violations: list[str] = []
    allowlisted_hits: set[tuple[str, str]] = set()

    for name, asset in sorted(monitored.items()):
        for up in asset.get("upstreams") or []:
            if up.get("type") != "asset":
                skipped_edges += 1
                continue
            up_name = up.get("value")
            if (up_name not in monitored or name not in last_modified
                    or up_name not in last_modified):
                skipped_edges += 1
                continue
            checked_edges += 1
            ts_down, ts_up = last_modified[name], last_modified[up_name]
            if ts_up <= ts_down:
                continue
            days = (ts_up - ts_down) / 86_400_000
            detail = (
                f"{name} (built {fmt_ts(ts_down)}) is stale relative to "
                f"{up_name} (modified {fmt_ts(ts_up)}, {days:.1f} days newer)"
            )
            entry = allowlist.get((name, up_name))
            if entry:
                allowlisted_hits.add((name, up_name))
                log.info("ALLOWLISTED [%s] %s -- %s",
                         entry["td_ref"], detail, entry["reason"])
            else:
                new_violations.append(detail)
                log.error("NEW STALENESS: %s", detail)

    # Allowlist hygiene: entries that no longer match any live violation
    # should be pruned once their TD item resolves, not accumulate forever.
    for key, entry in allowlist.items():
        if key not in allowlisted_hits:
            log.warning(
                "allowlist entry no longer matches a live violation "
                "(resolved? prune it): %s <- %s [%s]",
                key[0], key[1], entry["td_ref"],
            )

    log.info(
        "checked %d table-to-table edges (%d skipped: non-table endpoint), "
        "%d allowlisted violation(s), %d NEW violation(s), %d missing table(s)",
        checked_edges, skipped_edges, len(allowlisted_hits),
        len(new_violations), len(missing),
    )

    if new_violations:
        log.error(
            "FAIL: %d new stale edge(s). Either rematerialize the stale "
            "asset(s) downstream-of-change, or -- if the gap is deliberate -- "
            "add an allowlist entry with a TD reference and reason in %s.",
            len(new_violations), args.allowlist,
        )
        return EXIT_NEW_VIOLATIONS

    log.info("PASS: no undocumented staleness.")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
