"""
run_baseline_comparison.py — LLM report-writer prototype (ADR-0010)

Added 2026-08-02 per a Fable advisory pass: before writing anything in the
OTF concept note about why an LLM is used here, generate the SAME window
through the template baseline (template_writer.py, free, deterministic, no
API key) and the LLM path (report_writer_openai.py, requires
OPENAI_API_KEY) and read them side by side. Both paths take the exact same
claims list from deterministic_analysis.py and are checked through the
exact same verify_report.py pipeline -- the only thing that varies is the
generation mechanism.

This script always runs the template path (free). It runs the LLM path
only if OPENAI_API_KEY is set; otherwise it prints the template output
alone and tells you how to add the LLM side.

Usage:
    python3 run_baseline_comparison.py                 # template only
    OPENAI_API_KEY=sk-... python3 run_baseline_comparison.py   # both, side by side
"""

from __future__ import annotations

import os

from claim_check import DataContext
from coherence_check import check_report_coherence
from deterministic_analysis import analyze_window
from fixtures.finance_bill_2024_fixture import count_weeks_at_or_above, lookup_daily, lookup_regime
from template_writer import generate_report_sentences_template
from verify_report import verify_report

COUNTRY = "Kenya"
WEEK_START = "2024-06-15"
WEEK_END = "2024-07-13"


def _print_report(label: str, sentences, claims, ctx):
    result = verify_report(claims, sentences, ctx)
    print(f"--- {label} ---")
    print(result.full_text)
    print(f"[verified={result.verified}]")
    if not result.verified:
        for r in result.rejection_reasons:
            print(f"  REJECTED: {r}")
    texts = [s["text"] for s in sentences if isinstance(s.get("text"), str)]
    coherence_flagged = [(t, r) for t, r in check_report_coherence(texts) if not r.clean]
    if coherence_flagged:
        for text, r in coherence_flagged:
            print(f"  [coherence: garbled token(s) {r.flagged_tokens}] {text!r}")
    print()
    return result


def run():
    ctx = DataContext(lookup_regime=lookup_regime, lookup_daily=lookup_daily, count_weeks_at_or_above=count_weeks_at_or_above)
    claims = analyze_window(COUNTRY, WEEK_START, WEEK_END)
    print(f"Window: {COUNTRY}, {WEEK_START}..{WEEK_END} -- {len(claims)} claim(s)\n")

    template_out = generate_report_sentences_template(claims)
    _print_report(f"TEMPLATE ({template_out['extraction_model']})", template_out["sentences"], claims, ctx)

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "No OPENAI_API_KEY set -- skipping the LLM path.\n"
            "Set OPENAI_API_KEY and re-run this script to see both outputs "
            "side by side before writing anything about this comparison in "
            "the concept note."
        )
        return

    from report_writer_openai import generate_report_sentences
    llm_gen = generate_report_sentences(COUNTRY, WEEK_START, WEEK_END, claims)
    _print_report(f"LLM ({llm_gen['extraction_model']})", llm_gen["sentences"], claims, ctx)

    print(
        "Read both reports above. Judge on: readability, whether either "
        "reads as more than a mechanical field-fill, and whether the LLM's "
        "phrasing justifies the added verification surface (causal-language "
        "scan, house-style prompt, live API dependency) the template path "
        "doesn't need at all."
    )


if __name__ == "__main__":
    run()
