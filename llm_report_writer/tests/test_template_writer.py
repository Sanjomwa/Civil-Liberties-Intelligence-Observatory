"""
tests/test_template_writer.py — LLM report-writer prototype (ADR-0010)

Proves the template baseline (a) renders every claim type without error,
(b) always passes the full verify_report.py pipeline (it should, by
construction -- see template_writer.py's docstring), and (c) produces
output shaped identically enough to report_writer_openai.py's output that
both can be verified through the same code path unchanged. This last point
is what makes the LLM-vs-template comparison apples-to-apples rather than
a comparison of two different pipelines.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from claim_check import DataContext  # noqa: E402
from deterministic_analysis import analyze_window  # noqa: E402
from fixtures.finance_bill_2024_fixture import (  # noqa: E402
    count_weeks_at_or_above,
    lookup_daily,
    lookup_regime,
)
from template_writer import generate_report_sentences_template  # noqa: E402
from verify_report import verify_report  # noqa: E402

CTX = DataContext(
    lookup_regime=lookup_regime,
    lookup_daily=lookup_daily,
    count_weeks_at_or_above=count_weeks_at_or_above,
)

CLAIMS = analyze_window("Kenya", "2024-06-15", "2024-07-13")


def test_renders_one_sentence_per_claim_no_errors():
    result = generate_report_sentences_template(CLAIMS)
    assert len(result["sentences"]) == len(CLAIMS)


def test_every_sentence_claim_index_matches_its_position():
    result = generate_report_sentences_template(CLAIMS)
    for i, s in enumerate(result["sentences"]):
        assert s["claim_index"] == i


def test_output_shape_matches_llm_path_metadata_keys():
    result = generate_report_sentences_template(CLAIMS)
    assert set(result.keys()) == {"sentences", "extraction_model", "prompt_version_hash", "generated_timestamp_utc", "llm_derived"}
    assert result["llm_derived"] is False


def test_template_report_always_passes_full_verification():
    result = generate_report_sentences_template(CLAIMS)
    verification = verify_report(CLAIMS, result["sentences"], CTX)
    assert verification.verified is True, verification.rejection_reasons


def test_template_output_contains_no_causal_or_superlative_language():
    from causal_language_check import check_report_language
    result = generate_report_sentences_template(CLAIMS)
    texts = [s["text"] for s in result["sentences"]]
    checks = check_report_language(texts)
    unclean = [(t, r) for t, r in checks if not r.clean]
    assert unclean == [], unclean


def test_unrecognized_claim_type_raises_loudly_not_silently():
    bad_claims = [{"claim_type": "NOT_A_REAL_TYPE"}]
    try:
        generate_report_sentences_template(bad_claims)
        assert False, "Expected ValueError for an unrecognized claim_type"
    except ValueError:
        pass


if __name__ == "__main__":
    import inspect
    failures = 0
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
