"""
ci_check_no_merge.py — OTF-04 LLM extraction prototype, non-merge CI guard

Enforces the governance contract's "Disclosure and non-merge" rule (see
ADR-0009 and docs/07-governance/ai-output-governance.md, requirement 2):
OTF-04's LLM-derived output must never be joined into any existing CLIO
Bruin asset without a future ADR explicitly superseding ADR-0009.

Declaring llm_extraction/ outside Bruin's DAG (see setup_bigquery.py's
docstring) is necessary but not sufficient -- nothing stops a future
contributor from adding a Bruin SQL asset that references
`llm_derived.article_extractions` directly, bypassing the DAG-placement
argument entirely (this project's own TD-42 already found declared Bruin
lineage and actual asset behavior can diverge). This script makes the rule
a tested, permanent CI constraint instead of a one-time review that can
silently erode.

Scope is deliberately narrow: only Bruin/assets/**/*.sql. Grepping the
whole repo would self-trigger on this file, ADR-0009, decision-log.md, and
llm_extraction's own README -- all of which legitimately mention
`llm_derived` while documenting the boundary this script exists to
enforce.

Exit 0 if clean, exit 1 with every offending file:line printed if not.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BRUIN_ASSETS_DIR = REPO_ROOT / "Bruin" / "assets"
FORBIDDEN_STRING = "llm_derived"


def check() -> int:
    if not BRUIN_ASSETS_DIR.is_dir():
        print(f"FATAL: expected Bruin assets directory not found at {BRUIN_ASSETS_DIR}", file=sys.stderr)
        return 1

    sql_files = sorted(BRUIN_ASSETS_DIR.rglob("*.sql"))
    if not sql_files:
        print(f"FATAL: no .sql files found under {BRUIN_ASSETS_DIR} -- glob path may be wrong.", file=sys.stderr)
        return 1

    violations: list[str] = []
    for sql_file in sql_files:
        text = sql_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            if FORBIDDEN_STRING in line:
                rel = sql_file.relative_to(REPO_ROOT)
                violations.append(f"{rel}:{lineno}: {line.strip()}")

    if violations:
        print(
            "NON-MERGE GUARD FAILED: found references to "
            f"'{FORBIDDEN_STRING}' in Bruin SQL assets. Per ADR-0009, "
            "OTF-04's LLM-derived output may never be joined into any "
            "existing CLIO Bruin asset without a future ADR explicitly "
            "superseding ADR-0009.\n"
        )
        for v in violations:
            print(f"  {v}")
        return 1

    print(f"[ok] non-merge guard clean: {len(sql_files)} Bruin SQL assets checked, no '{FORBIDDEN_STRING}' references found.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
