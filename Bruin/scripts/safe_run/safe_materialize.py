"""
safe_materialize.py
===================
Cascade-safe materialization wrapper for the Bruin/BigQuery DAG (ADR-0012).

WHY THIS SCRIPT EXISTS
----------------------
ADR-0005's staleness check detects downstream tables built from upstream
state that has since changed. It detects; it does not prevent. On
2026-08-16 it fired with 6 new violations because a fix session the day
before rematerialized two upstream assets and rebuilt nothing below them --
the same partial-cascade shape ADR-0005 was written for (TD-38, TD-40,
TD-54), reintroduced by hand.

The failure was not cadence (the pipeline is not run often enough); it was
completeness inside one session. This wrapper closes that gap
mechanically:

    1. always `bruin run --downstream <asset>` -- never a bare
       single-asset run, so the cascade is not a thing a person or an
       agent has to remember;
    2. run the ADR-0005 staleness check in the same invocation, so the
       verdict arrives in the same minute rather than in tomorrow's
       06:00 UTC CI email.

This script is the only sanctioned way to materialize anything in this
repository. The daily CI staleness workflow stays exactly as it is, as a
backstop for anything that bypasses this script (a bare `bruin run`, a
direct `bq` DDL, a dashboard-side edit).

WHAT THIS SCRIPT DOES NOT DO
----------------------------
It does not prove correctness. The staleness check compares timestamps,
never contents (ADR-0005's own closing limitation). A green run here means
"everything declared-downstream was rebuilt after its upstream" -- not
"the numbers are right." Quality checks (`bruin run` executes `main` and
`checks` by default) and `pytest` remain separate obligations.

It also cannot cascade through intelligence.acled_pressure_regimes. That
asset is `strategy: merge` under an EXECUTION CONTRACT of exactly one
country x one new week x one execution, and its upstream precondition
check (intelligence.acled_pressure_regimes_precondition_check) calls
ERROR() when more than one week is in scope -- which is every run that
uses pipeline.yml's default `target_week=""`. A cascade that reaches it
therefore aborts there and leaves everything below it unbuilt. This
script refuses up front instead of discovering that mid-cascade; see
--allow-contract-bound and the remediation text it prints.

Verified live 2026-08-16 (ADR-0012 build session) against bruin
v0.11.664: `bruin run assets/intelligence/acled_pressure_regimes_precondition.sql`
with no --var override (default target_week="") fails exactly as
predicted -- "Found 1523 distinct week_start_date value(s) for
target_week=<unset>" -- confirming this refusal is not theoretical.

EXIT CODES
----------
    0  cascade succeeded and the staleness check passed
    1  staleness check reported NEW (non-allowlisted) violations
    2  staleness check hit an operational error (bruin/BigQuery/allowlist)
    3  refused before running anything (contract-bound asset in scope,
       or a usage/resolution error)
    4  `bruin run` failed; the staleness check was still run and its
       findings printed, but the run itself did not complete

USAGE
-----
    # normal case -- one touched asset, full downstream cascade + check
    python Bruin/scripts/safe_run/safe_materialize.py \\
        Bruin/assets/intermediate/int.ooni_experiment_results.sql

    # several assets touched in one fix session (the 2026-08-16 case)
    python Bruin/scripts/safe_run/safe_materialize.py \\
        Bruin/assets/intermediate/int.ooni_experiment_results.sql \\
        Bruin/assets/staging/stg.google_transparency_requests.sql

    # see the blast radius and cost estimate, run nothing
    python Bruin/scripts/safe_run/safe_materialize.py --dry-run <asset>

    # pass flags through to bruin (everything after -- is forwarded)
    python Bruin/scripts/safe_run/safe_materialize.py <asset> -- --var country="Kenya"
"""

import argparse
import logging
import re
import subprocess
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
PIPELINE_DIR = SCRIPT_DIR.parents[1]  # Bruin/
STALENESS_DIR = SCRIPT_DIR.parent / "staleness_check"
STALENESS_SCRIPT = STALENESS_DIR / "check_materialization_staleness.py"

sys.path.insert(0, str(STALENESS_DIR))

# Reused, not reimplemented: one parser of `bruin internal parse-pipeline`
# output, with one defensive shape check, in one place. Mirrors the way
# steady_state/run_acled_regime_week.py imports from the backfill script.
from check_materialization_staleness import parse_pipeline  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("safe_materialize")

EXIT_OK = 0
EXIT_NEW_STALENESS = 1
EXIT_OPERATIONAL = 2
EXIT_REFUSED = 3
EXIT_BRUIN_FAILED = 4

# Assets that must not be reached by an ordinary --downstream cascade,
# with the remediation for each. Keyed by declared asset name.
CONTRACT_BOUND_ASSETS = {
    "intelligence.acled_pressure_regimes": (
        "strategy: merge, under the EXECUTION CONTRACT in its own header "
        "(one country x one new week x one execution). A cascade carrying "
        "pipeline.yml's default target_week=\"\" trips its precondition "
        "check (ERROR) and stops there, leaving every asset below it "
        "unbuilt.\n"
        "        Remediation: rebuild the chain UP TO features."
        "acled_pressure_signals with this script, then advance the regime "
        "table with scripts/steady_state/run_acled_regime_week.py (one new "
        "week) or scripts/historical_initializer/"
        "backfill_acled_pressure_regimes.py (sequential replay -- hours, "
        "1,523 weeks for Kenya), then run this script again from "
        "intelligence.acled_pressure_regimes to cascade the marts."
    ),
}

# Per-rebuild scan volumes, measured in the 2026-07-06 cost audit
# (INFORMATION_SCHEMA.JOBS_BY_PROJECT, on-demand us-central1 at
# $6.25/TiB). Every asset not listed here was measured sub-GiB per
# materialization; they are counted but not priced.
MEASURED_REBUILD_GIB = {
    "stg.ooni_measurements": 11.4,
    "stg.ooni_dns_observations": 30.0,
    "stg.ooni_tcp_observations": 30.0,
    "stg.ooni_tls_observations": 30.0,
    "stg.ooni_http_observations": 30.0,
}
USD_PER_TIB = 6.25


def read_asset_name(path: Path) -> str:
    """Extract the declared `name:` from an asset file's @bruin header.

    The terminator is matched as `@bruin */` or `@bruin \"\"\"`, not a bare
    `@bruin`: assets/intelligence/acled_pressure_regimes.sql contains the
    literal string "@bruin" inside its description prose (line 106, "this
    asset's @bruin header"), and a naive non-greedy match to the next bare
    "@bruin" truncates the header before `depends:`. Verified against that
    exact file 2026-08-16: the terminator-aware regex correctly skips the
    false match and resolves the real header at line 255.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        log.error("cannot read asset file %s: %s", path, exc)
        sys.exit(EXIT_REFUSED)
    header = re.search(r'@bruin(.*?)@bruin\s*(?:\*/|""")', text, re.S)
    if not header:
        log.error("no @bruin header found in %s", path)
        sys.exit(EXIT_REFUSED)
    name = re.search(r"^name:\s*(\S+)", header.group(1), re.M)
    if not name:
        log.error("@bruin header in %s declares no name:", path)
        sys.exit(EXIT_REFUSED)
    return name.group(1)


def build_children(assets: list[dict]) -> dict[str, list[str]]:
    """Invert the declared dependency graph: upstream -> [downstream...]."""
    children: dict[str, list[str]] = {}
    for asset in assets:
        for up in asset.get("upstreams") or []:
            if up.get("type") != "asset":
                continue
            children.setdefault(up["value"], []).append(asset["name"])
    return children


def downstream_closure(children: dict[str, list[str]], root: str) -> set[str]:
    """Every asset transitively downstream of root (root excluded)."""
    seen: set[str] = set()
    stack = [root]
    while stack:
        for child in children.get(stack.pop(), []):
            if child not in seen:
                seen.add(child)
                stack.append(child)
    return seen


def dedupe_roots(roots: list[str], children: dict[str, list[str]]) -> list[str]:
    """Drop any root already covered by another root's cascade.

    A fix session that touched both an asset and something below it should
    run one cascade from the higher asset, not two overlapping ones.
    """
    keep = []
    for candidate in roots:
        covered_by = [
            other for other in roots
            if other != candidate and candidate in downstream_closure(children, other)
        ]
        if covered_by:
            log.info(
                "skipping %s as a starting point -- already inside the cascade from %s",
                candidate, ", ".join(sorted(covered_by)),
            )
        else:
            keep.append(candidate)
    return keep


def describe_scope(names: set[str]) -> str:
    """Human-readable cost/scope note for a set of assets to be rebuilt."""
    priced = {n: MEASURED_REBUILD_GIB[n] for n in names if n in MEASURED_REBUILD_GIB}
    gib = sum(priced.values())
    usd = gib / 1024 * USD_PER_TIB
    lines = [f"    {len(names)} asset(s) will be rebuilt (bruin decides execution order)"]
    for name in sorted(names):
        mark = f"  ~{MEASURED_REBUILD_GIB[name]:.0f} GiB/rebuild" if name in priced else ""
        lines.append(f"      - {name}{mark}")
    if priced:
        lines.append(
            f"    estimated billed scan: ~{gib:.0f} GiB (~${usd:.2f} at "
            f"${USD_PER_TIB}/TiB on-demand), from the 2026-07-06 cost audit's "
            f"measured per-rebuild figures; {len(names) - len(priced)} other "
            f"asset(s) were measured sub-GiB and are not priced here"
        )
    else:
        lines.append(
            "    estimated billed scan: below the cost audit's measurement "
            "floor (every asset in scope was measured sub-GiB per rebuild)"
        )
    return "\n".join(lines)


def check_contract_bound(names: set[str], allow: bool) -> None:
    hits = sorted(names & set(CONTRACT_BOUND_ASSETS))
    if not hits:
        return
    for name in hits:
        log.error("REFUSING: %s is in the cascade.\n        %s",
                  name, CONTRACT_BOUND_ASSETS[name])
    if allow:
        log.warning(
            "--allow-contract-bound was passed: proceeding anyway. Expect the "
            "precondition check to fail and the cascade to stop there."
        )
        return
    log.error(
        "Nothing has been run. Re-invoke with --allow-contract-bound only if "
        "you have read the remediation above and intend the cascade to stop."
    )
    sys.exit(EXIT_REFUSED)


def run_bruin(asset_path: Path, passthrough: list[str]) -> int:
    """Invoke `bruin run --downstream <asset>`, streaming output live.

    Output is deliberately NOT captured (unlike backfill_acled_pressure_
    regimes.py, which captures per-week): a cascade can take minutes and
    the operator needs to see per-asset progress as it happens.
    """
    cmd = ["bruin", "run", "--downstream", str(asset_path), *passthrough]
    log.info("running: %s   (cwd=%s)", " ".join(cmd), PIPELINE_DIR)
    started = time.monotonic()
    try:
        proc = subprocess.run(cmd, cwd=str(PIPELINE_DIR))
    except FileNotFoundError:
        log.error("bruin CLI not found on PATH")
        sys.exit(EXIT_OPERATIONAL)
    log.info("bruin exited %d after %.0fs", proc.returncode, time.monotonic() - started)
    return proc.returncode


def run_staleness_check() -> int:
    log.info("running ADR-0005 staleness check (%s)", STALENESS_SCRIPT.name)
    proc = subprocess.run([sys.executable, str(STALENESS_SCRIPT)])
    return proc.returncode


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Cascade-safe materialization wrapper (ADR-0012): always "
                    "runs bruin run --downstream, then the ADR-0005 staleness "
                    "check.",
        epilog="Anything after `--` is passed through to bruin verbatim "
               "(e.g. -- --var country=\"Kenya\").",
    )
    parser.add_argument("assets", nargs="+", type=Path,
                        help="path(s) to the asset file(s) that were changed")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the cascade scope and cost estimate, run nothing")
    parser.add_argument("--allow-contract-bound", action="store_true",
                        help="proceed even though a contract-bound asset is in "
                             "the cascade (see CONTRACT_BOUND_ASSETS)")
    # argparse cannot host two greedy positional lists, so the bruin
    # passthrough is split off manually on the first bare "--".
    argv = sys.argv[1:]
    if "--" in argv:
        cut = argv.index("--")
        argv, passthrough = argv[:cut], argv[cut + 1:]
    else:
        passthrough = []
    args = parser.parse_args(argv)
    args.passthrough = passthrough
    return args


def main() -> int:
    args = parse_args()
    passthrough = list(args.passthrough)

    paths = []
    for raw in args.assets:
        path = raw if raw.is_absolute() else Path.cwd() / raw
        if not path.exists():
            log.error("asset file not found: %s", raw)
            return EXIT_REFUSED
        paths.append(path.resolve())

    by_name = {read_asset_name(p): p for p in paths}
    assets = parse_pipeline(PIPELINE_DIR)
    known = {a["name"] for a in assets}
    for name in by_name:
        if name not in known:
            log.error("asset %s is not in the parsed pipeline at %s", name, PIPELINE_DIR)
            return EXIT_REFUSED

    children = build_children(assets)
    roots = dedupe_roots(list(by_name), children)

    scope: set[str] = set()
    for root in roots:
        scope |= {root} | downstream_closure(children, root)

    log.info("cascade plan: %d starting asset(s) -> %d asset(s) total\n%s",
             len(roots), len(scope), describe_scope(scope))

    check_contract_bound(scope, args.allow_contract_bound)

    if args.dry_run:
        log.info("--dry-run: nothing was executed.")
        return EXIT_OK

    failed = []
    for root in roots:
        rc = run_bruin(by_name[root], passthrough)
        if rc != 0:
            failed.append((root, rc))
            log.error(
                "bruin run --downstream %s failed (exit %d). Assets below the "
                "failure point were NOT rebuilt. Resume with `bruin run "
                "--continue` from %s (works only if no asset dependency "
                "changed since), or re-invoke this script once the cause is "
                "fixed. Running the staleness check anyway -- a partial "
                "cascade is exactly when its report is most useful.",
                by_name[root], rc, PIPELINE_DIR,
            )
            break

    staleness_rc = run_staleness_check()

    if failed:
        log.error("RESULT: cascade INCOMPLETE (bruin failed on %s); "
                  "staleness check exited %d.", failed[0][0], staleness_rc)
        return EXIT_BRUIN_FAILED
    if staleness_rc == EXIT_OK:
        log.info(
            "RESULT: cascade complete, staleness check PASS. This proves every "
            "declared-downstream table was rebuilt after its upstream -- it "
            "does not prove the numbers are right. Run the test suite "
            "(RUN_BIGQUERY_TESTS=1 pytest) and `bruin validate` before "
            "reporting the work done."
        )
        return EXIT_OK
    log.error("RESULT: cascade complete, but the staleness check exited %d "
              "(1 = new violations, 2 = operational error).", staleness_rc)
    return staleness_rc


if __name__ == "__main__":
    sys.exit(main())
