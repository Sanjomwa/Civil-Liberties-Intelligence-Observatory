"""
run_report.py — LLM report-writer prototype (ADR-0010), end-to-end runner

The live entry point: runs the full pipeline for one window --
deterministic analysis -> LLM narration -> four-layer verification --
against real OpenAI API, requires OPENAI_API_KEY. Everything this script
calls has already been proven correct offline (51/51 tests passing across
claim_check.py, causal_language_check.py, completeness_check.py,
deterministic_analysis.py, and verify_report.py) before this script ever
makes a live call -- the same discipline ADR-0009's run_extraction.py
followed.

Usage:
    export OPENAI_API_KEY=sk-...
    python3 run_report.py
"""

from __future__ import annotations

import json

from claim_check import DataContext
from deterministic_analysis import analyze_window, summarize_window_for_prompt
from fixtures.finance_bill_2024_fixture import count_weeks_at_or_above, lookup_daily, lookup_regime
from report_writer_openai import generate_report_sentences
from style_lint import lint_report
from verify_report import verify_report

COUNTRY = "Kenya"
WEEK_START = "2024-06-15"
WEEK_END = "2024-07-13"


def run():
    ctx = DataContext(lookup_regime=lookup_regime, lookup_daily=lookup_daily, count_weeks_at_or_above=count_weeks_at_or_above)

    claims = analyze_window(COUNTRY, WEEK_START, WEEK_END)
    print(f"Deterministic analysis produced {len(claims)} pre-verified claim(s) for {COUNTRY}, {WEEK_START}..{WEEK_END}.")
    print(summarize_window_for_prompt(COUNTRY, WEEK_START, WEEK_END, claims))
    print()

    generation = generate_report_sentences(COUNTRY, WEEK_START, WEEK_END, claims)
    sentences = generation["sentences"]
    print(f"Model ({generation['extraction_model']}) returned {len(sentences)} sentence(s).\n")

    result = verify_report(claims, sentences, ctx)

    print("=== Generated narrative (model output only) ===")
    print(result.narrative_text)
    print()

    if result.appended_disclosures:
        print("=== Appended disclosures (code-inserted, not model-phrased) ===")
        for d in result.appended_disclosures:
            print(f"  {d}")
        print()

    print("=== Full report text (narrative + appended disclosures) ===")
    print(result.full_text)
    print()

    print("=== Verification (blocking -- gates whether this report is trusted) ===")
    print(f"Overall verified: {result.verified}")
    if not result.verified:
        print("Rejection reasons:")
        for r in result.rejection_reasons:
            print(f"  - {r}")

    print("\n=== Style lint (advisory only -- never blocks verification) ===")
    style_findings = lint_report([s["text"] for s in sentences if isinstance(s.get("text"), str)])
    flagged = [(text, r) for text, r in style_findings if not r.clean]
    if flagged:
        for text, r in flagged:
            print(f"  [{', '.join(r.flags)}] {text!r}")
    else:
        print("  No style issues flagged.")

    output = {
        "country": COUNTRY,
        "week_start": WEEK_START,
        "week_end": WEEK_END,
        "claims": claims,
        "generation_metadata": {k: v for k, v in generation.items() if k != "sentences"},
        "sentences": sentences,
        "narrative_text": result.narrative_text,
        "appended_disclosures": result.appended_disclosures,
        "full_text": result.full_text,
        "verified": result.verified,
        "rejection_reasons": result.rejection_reasons,
        "style_lint_flags": [{"text": t, "flags": r.flags} for t, r in flagged],
    }
    with open("output_report.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print("\nWrote output_report.json")


if __name__ == "__main__":
    run()
