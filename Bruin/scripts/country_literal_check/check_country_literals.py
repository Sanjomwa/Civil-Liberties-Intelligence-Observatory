#!/usr/bin/env python3
"""Fail CI when a hardcoded country literal appears in a SQL asset.

Companion to the 2026-07-06 multi-country scaffolding pass (see
decision-log.md): every country scope filter in Bruin/assets/**/*.sql
must go through the pipeline variables ({{ var.country }} /
{{ var.iso2 }}, declared in Bruin/pipeline.yml). The ONE designated
location where raw country literals are legitimate is
marts/dims/dim_country.sql's normalization CTE, where they are mapping
DATA (raw source value -> canonical name/iso2), not scope filters.
That file is allowlisted in country_literal_allowlist.json, which
follows the same TD/ADR-referenced-entry convention as ADR-0005's
staleness allowlist: an entry without a reason and reference is
malformed and fails the check outright.

What this deliberately does NOT cover: Python-level country hardcoding
in ingestion assets (Bruin/assets/ingest/ooni_raw.py pins
PROBE_CC = "KE"; see the technical-debt inventory). Re-ingestion is not
currently runnable in this environment, so that literal is documented
debt rather than something this check can meaningfully enforce yet.

Detection is deliberately narrow to stay false-positive-free: a quoted
string literal whose ENTIRE content is a known country token (currently
KE / KEN / KENYA / Kenya, case-insensitive). Labels that merely contain
a country word (e.g. 'MAJOR_KENYA_PROVIDER') are out of scope -- they
are vocabulary values, tracked separately by the multi-country work.
Extend COUNTRY_TOKENS when a new country's ingestion starts.

Exit codes (same convention as check_materialization_staleness.py):
  0 -- no undocumented country literals
  1 -- new, undocumented country literal(s) found
  2 -- operational error (malformed allowlist, missing directories)
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]
ASSETS_DIR = REPO_ROOT / "Bruin" / "assets"
ALLOWLIST_PATH = SCRIPT_DIR / "country_literal_allowlist.json"

# Full-content match only, inside single- or double-quoted SQL string
# literals. Case-insensitive so 'ke' / 'Kenya' / 'KENYA' all match.
COUNTRY_TOKENS = ("KE", "KEN", "KENYA")
LITERAL_RE = re.compile(
    r"""['"](%s)['"]""" % "|".join(COUNTRY_TOKENS),
    re.IGNORECASE,
)


def load_allowlist() -> set[str]:
    if not ALLOWLIST_PATH.exists():
        print(f"OPERATIONAL ERROR: allowlist missing at {ALLOWLIST_PATH}")
        sys.exit(2)

    try:
        entries = json.loads(ALLOWLIST_PATH.read_text())
    except json.JSONDecodeError as exc:
        print(f"OPERATIONAL ERROR: allowlist is not valid JSON: {exc}")
        sys.exit(2)

    allowed: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or not entry.get("file") or not entry.get("reason") or not entry.get("reference"):
            print(
                "OPERATIONAL ERROR: malformed allowlist entry (every entry "
                f"needs file, reason, and reference): {entry!r}"
            )
            sys.exit(2)
        allowed.add(entry["file"])
    return allowed


def find_violations(allowed: set[str]) -> list[tuple[str, int, str]]:
    if not ASSETS_DIR.is_dir():
        print(f"OPERATIONAL ERROR: assets directory missing at {ASSETS_DIR}")
        sys.exit(2)

    violations: list[tuple[str, int, str]] = []
    for sql_path in sorted(ASSETS_DIR.rglob("*.sql")):
        rel = sql_path.relative_to(ASSETS_DIR).as_posix()
        if rel in allowed:
            continue
        in_block_comment = False
        for line_number, line in enumerate(
            sql_path.read_text().splitlines(), start=1
        ):
            # Comments are documentation, not scope filters -- strip
            # them so prose like "-- live: 'KE' on all rows" can't fail
            # the check. Handles -- line comments and /* */ blocks
            # (including the @bruin header); a '--' inside a SQL string
            # literal would be a false strip, but no asset does that
            # and the failure mode is a missed hit, not a false alarm.
            code = line
            if in_block_comment:
                if "*/" in code:
                    code = code.split("*/", 1)[1]
                    in_block_comment = False
                else:
                    continue
            if "/*" in code:
                head, tail = code.split("/*", 1)
                if "*/" in tail:
                    code = head + tail.split("*/", 1)[1]
                else:
                    code = head
                    in_block_comment = True
            code = code.split("--", 1)[0]
            if LITERAL_RE.search(code):
                violations.append((rel, line_number, line.strip()))
    return violations


def main() -> int:
    allowed = load_allowlist()
    violations = find_violations(allowed)

    if not violations:
        print(
            "PASS: no undocumented country literals in SQL assets "
            f"({len(allowed)} allowlisted file(s))."
        )
        return 0

    print(
        f"FAIL: {len(violations)} hardcoded country literal(s) found. "
        "Route scope filters through {{ var.country }} / {{ var.iso2 }} "
        "(Bruin/pipeline.yml); only dim_country.sql's normalization "
        "mapping may carry raw literals (see its header note)."
    )
    for rel, line_number, line in violations:
        print(f"  Bruin/assets/{rel}:{line_number}: {line}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
