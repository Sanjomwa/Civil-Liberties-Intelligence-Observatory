"""
run_live_windows.py — LLM report-writer prototype (ADR-0010), live comparison run

Extends run_baseline_comparison.py's single-hardcoded-window pattern to a
list of real windows, all sourced from a live query against
intelligence.acled_pressure_regimes (Kenya, 2023-06-01 through 2025-06-01 --
the range marts.fact_country_pressure_daily has real, non-null
composite_pressure_score for every day, confirmed via BigQuery before this
list was chosen).

For every window: analyze_window_live() computes the claims, then BOTH the
template path (free, deterministic) and the LLM path (gpt-5.4-mini, one
attempt, one retry on verification failure, then left rejected) are run
through the identical verify_report.py pipeline. Results are written to
run_live_windows_results.json for the calling session to read and record
in reports.md -- this script does not touch reports.md itself.

Usage:
    python3 run_live_windows.py
"""

from __future__ import annotations

import json
import sys

from bigquery_lookup import (
    analyze_window_live,
    count_weeks_at_or_above,
    lookup_daily,
    lookup_regime,
)
from claim_check import DataContext
from report_writer_openai import ReportGenerationError, generate_report_sentences
from style_lint import lint_report
from template_writer import generate_report_sentences_template
from verify_report import verify_report

COUNTRY = "Kenya"

# All 11 windows fall entirely inside 2023-06-01..2025-06-01 (the range
# marts.fact_country_pressure_daily has real data for every day, confirmed
# live). 5 "something happened" spike windows (drawn from real
# non-STABLE stretches in intelligence.acled_pressure_regimes, queried
# live) + 6 "nothing happened" STABLE-only windows (every week manually
# confirmed STABLE from the same live query), leaning toward quiet, per
# the relay prompt's own reasoning: hallucination/omission pressure is
# highest with no real story to tell.
WINDOWS = [
    {"label": "Finance Bill 2024 (flagship)", "week_start": "2024-05-11", "week_end": "2024-07-13"},
    {"label": "2023-06 conflict spike", "week_start": "2023-06-03", "week_end": "2023-06-24"},
    {"label": "2023-07 crisis spike", "week_start": "2023-07-08", "week_end": "2023-08-05"},
    {"label": "2023-10 escalation spike", "week_start": "2023-10-07", "week_end": "2023-11-04"},
    {"label": "2025-03 escalation spike", "week_start": "2025-03-08", "week_end": "2025-04-05"},
    {"label": "STABLE: 2023-08/09", "week_start": "2023-08-12", "week_end": "2023-09-09"},
    {"label": "STABLE: 2023-12/2024-01", "week_start": "2023-12-09", "week_end": "2024-01-06"},
    {"label": "STABLE: 2024-03/04", "week_start": "2024-03-23", "week_end": "2024-04-20"},
    {"label": "STABLE: 2024-10/11", "week_start": "2024-10-05", "week_end": "2024-11-02"},
    {"label": "STABLE: 2024-12/2025-01", "week_start": "2024-12-07", "week_end": "2025-01-04"},
    {"label": "STABLE: 2025-01/02", "week_start": "2025-01-18", "week_end": "2025-02-15"},
]


def _verification_summary(v):
    return {
        "verified": v.verified,
        "rejection_reasons": v.rejection_reasons,
        "narrative_text": v.narrative_text,
        "appended_disclosures": v.appended_disclosures,
        "full_text": v.full_text,
    }


def run_llm_path(country, week_start, week_end, claims, ctx):
    """One attempt, then one retry on verification failure (not on
    exception -- an exception means the call itself failed, which is a
    different and more severe condition, recorded separately)."""
    attempts = []
    try:
        gen = generate_report_sentences(country, week_start, week_end, claims)
    except ReportGenerationError as e:
        return {"attempts": [{"error": str(e)}], "final": None, "retried": False, "extraction_model": None}

    v1 = verify_report(claims, gen["sentences"], ctx)
    attempts.append({"generated": gen, "verification": _verification_summary(v1)})
    if v1.verified:
        return {"attempts": attempts, "final": v1, "retried": False, "extraction_model": gen["extraction_model"]}

    try:
        gen2 = generate_report_sentences(country, week_start, week_end, claims)
    except ReportGenerationError as e:
        attempts.append({"error": str(e)})
        return {"attempts": attempts, "final": v1, "retried": True, "extraction_model": gen["extraction_model"]}

    v2 = verify_report(claims, gen2["sentences"], ctx)
    attempts.append({"generated": gen2, "verification": _verification_summary(v2)})
    final = v2 if v2.verified else v2  # report the second attempt's result either way
    return {"attempts": attempts, "final": final, "retried": True, "extraction_model": gen2["extraction_model"]}


def run():
    ctx = DataContext(lookup_regime=lookup_regime, lookup_daily=lookup_daily, count_weeks_at_or_above=count_weeks_at_or_above)
    results = []

    for w in WINDOWS:
        label, week_start, week_end = w["label"], w["week_start"], w["week_end"]
        print(f"=== {label}: {COUNTRY} {week_start}..{week_end} ===", file=sys.stderr)

        claims = analyze_window_live(COUNTRY, week_start, week_end)
        print(f"  {len(claims)} claim(s)", file=sys.stderr)

        template_out = generate_report_sentences_template(claims)
        template_verify = verify_report(claims, template_out["sentences"], ctx)
        print(f"  template verified={template_verify.verified}", file=sys.stderr)

        llm_out = run_llm_path(COUNTRY, week_start, week_end, claims, ctx)
        first_verified = llm_out["attempts"][0].get("verification", {}).get("verified") if llm_out["attempts"] and "verification" in llm_out["attempts"][0] else False
        print(f"  llm first-attempt verified={first_verified}, retried={llm_out['retried']}", file=sys.stderr)

        llm_narrative = llm_out["final"].narrative_text if llm_out["final"] else ""
        style_findings = lint_report(llm_narrative.split(". ")) if llm_narrative else []
        style_flagged = [(s, r.flags) for s, r in style_findings if r.flags]

        results.append({
            "label": label,
            "country": COUNTRY,
            "week_start": week_start,
            "week_end": week_end,
            "num_claims": len(claims),
            "template": {
                "verified": template_verify.verified,
                "rejection_reasons": template_verify.rejection_reasons,
                "full_text": template_verify.full_text,
            },
            "llm": {
                "first_attempt_verified": first_verified,
                "retried": llm_out["retried"],
                "attempts": [
                    {
                        "error": a.get("error"),
                        "verification": a.get("verification"),
                    }
                    for a in llm_out["attempts"]
                ],
                "final_verified": llm_out["final"].verified if llm_out["final"] else False,
                "extraction_model": llm_out["extraction_model"],
            },
            "style_lint_flags": style_flagged,
        })

    with open("run_live_windows_results.json", "w") as f:
        json.dump(results, f, indent=2)

    print(f"\nWrote {len(results)} window results to run_live_windows_results.json", file=sys.stderr)


if __name__ == "__main__":
    run()
