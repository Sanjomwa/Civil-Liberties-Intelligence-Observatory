"""
template_writer.py — LLM report-writer prototype (ADR-0010), baseline comparison

Added 2026-08-02 after a Fable advisory pass asked the question this
prototype had not yet answered: given how narrow report_writer_openai.py's
job already is (phrase ~5 fixed claim types, one claim per sentence, no
causal language, no invented facts), does an LLM actually beat a trivial
rule-based template narrator for this v1 scope? That's an empirical
question, not one to assume the answer to either way -- so this module
exists to make the comparison possible, not to settle it. Sam runs both
paths against the same claims and reads the output side by side.

This module takes EXACTLY the same input as report_writer_openai.py
(deterministic_analysis.py's claim list) and returns EXACTLY the same
output shape ({"sentences": [...], ...metadata}), so it can be run through
the identical verify_report.py pipeline -- an apples-to-apples comparison
of generation mechanism, holding claims, verification, and disclosure
assembly fixed.

Zero API calls, zero network access, zero variance run to run -- unlike
the LLM path, the exact same claims always produce the exact same text.
That determinism is itself one data point in the comparison: a template
narrator can never fail claim_check.py's re-verification (each template
is built to phrase its claim's own fields, nothing else) and can never
trip causal_language_check.py (the fixed strings below contain no
causal connectives or superlatives) -- so template output should always
verify. Whether it reads as well as the LLM path is the open question this
module can't answer by itself; that's the human judgment call the
comparison run is for.

One template function per claim_type, deliberately matching
claim_check.py's five schemas field-for-field -- if a claim's schema ever
changes there, this file needs the same edit, same as
deterministic_analysis.py and report_writer_openai.py's user-message
builder already require.
"""

from __future__ import annotations

from datetime import datetime, timezone

MODEL_NAME = "template-writer-v1"


def _render_classification(claim: dict) -> str:
    return (
        f"{claim['country']}'s regime classification for the week of "
        f"{claim['week_start_date']} was {claim['claimed_value']}."
    )


def _render_count(claim: dict) -> str:
    return (
        f"Across {claim['week_start']} through {claim['week_end']}, "
        f"{claim['claimed_count']} week(s) in {claim['country']} were "
        f"classified {claim['regime_order_min']} or above."
    )


def _render_ref(ref: dict) -> str:
    if "literal" in ref:
        return str(ref["literal"])
    return f"{ref.get('source_column', 'value')} on {ref.get('date')}"


_OPERATOR_WORDS = {
    "gt": "was greater than",
    "gte": "was at least",
    "lt": "was less than",
    "lte": "was at most",
    "eq": "was equal to",
}


def _render_comparison(claim: dict) -> str:
    left = _render_ref(claim.get("left", {}))
    right = _render_ref(claim.get("right", {}))
    op_word = _OPERATOR_WORDS.get(claim.get("operator"), "was compared to")
    return f"{left} {op_word} {right}."


def _render_temporal_ordering(claim: dict) -> str:
    before = claim["before"]
    after = claim["after"]
    return (
        f"{claim['country']}'s classification was {before['regime_label']} "
        f"for the week of {before['week_start_date']}, then {after['regime_label']} "
        f"for the week of {after['week_start_date']}."
    )


def _render_magnitude_band(claim: dict) -> str:
    return (
        f"On {claim['date']}, {claim['country']}'s composite pressure score "
        f"reached the {claim['claimed_band']} band."
    )


_RENDERERS = {
    "CLASSIFICATION": _render_classification,
    "COUNT": _render_count,
    "COMPARISON": _render_comparison,
    "TEMPORAL_ORDERING": _render_temporal_ordering,
    "MAGNITUDE_BAND": _render_magnitude_band,
}


def generate_report_sentences_template(claims: list[dict]) -> dict:
    """Same return shape as report_writer_openai.generate_report_sentences()
    -- {"sentences": [{claim_index, text}, ...], ...metadata} -- so both
    paths can be handed to verify_report.verify_report() unchanged. Every
    claim in the input list gets exactly one sentence, in claim list order
    (no reordering -- avoids the adjacency-implication risk entirely by
    construction, since nothing here ever varies sentence order based on
    anything but the deterministic claims list order)."""
    sentences = []
    for i, claim in enumerate(claims):
        renderer = _RENDERERS.get(claim.get("claim_type"))
        if renderer is None:
            # No template for an unrecognized claim_type -- fail loud, not
            # silently skip, so a schema drift is caught immediately rather
            # than producing a report that quietly omits a claim.
            raise ValueError(f"template_writer.py has no renderer for claim_type {claim.get('claim_type')!r}")
        sentences.append({"claim_index": i, "text": renderer(claim)})

    return {
        "sentences": sentences,
        "extraction_model": MODEL_NAME,
        "prompt_version_hash": "n/a-template",
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "llm_derived": False,
    }
