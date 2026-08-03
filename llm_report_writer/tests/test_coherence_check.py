"""
tests/test_coherence_check.py — LLM report-writer prototype (ADR-0010)

Proves coherence_check.py catches the exact TD-78 failure mode (a garbled
non-Latin-script token embedded in an otherwise-clean English sentence) and
correctly leaves clean prose -- including legitimate accented Latin text
and common punctuation -- untouched. Non-blocking by design, same as
style_lint.py: this test suite proves detection works, not that it gates
anything (it doesn't; verify_report.py never calls this module).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from coherence_check import check_sentence_coherence  # noqa: E402


def test_plain_english_sentence_is_clean():
    result = check_sentence_coherence("Kenya's regime classification for the week of June 22, 2024 was CRISIS.")
    assert result.clean is True, result.flagged_tokens


def test_the_actual_td78_sentence_is_flagged():
    """The real sentence that surfaced this gap during the 2026-08-03 live
    comparison run, verbatim."""
    result = check_sentence_coherence("Kenya was classified as STABLE for the week սկս starting 2024-03-23.")
    assert result.clean is False
    assert "սկս" in result.flagged_tokens


def test_isolated_garbled_token_is_flagged():
    result = check_sentence_coherence("The classification моved to CRISIS.")
    assert result.clean is False
    assert len(result.flagged_tokens) == 1


def test_accented_latin_place_names_pass_clean():
    # Legitimate English-language report text can contain accented Latin
    # characters (place names, loanwords) -- these must not be flagged.
    result = check_sentence_coherence("The delegation visited Nairobi and later Zürich and São Paulo.")
    assert result.clean is True, result.flagged_tokens


def test_common_punctuation_and_symbols_pass_clean():
    result = check_sentence_coherence("Pressure rose 12–15% — a genuine spike — reaching 7.8°.")
    assert result.clean is True, result.flagged_tokens


def test_numbers_and_dates_pass_clean():
    result = check_sentence_coherence("Kenya had 3 weeks at CRISIS or above from 2024-05-11 through 2024-07-13.")
    assert result.clean is True, result.flagged_tokens


def test_multiple_garbled_tokens_all_reported():
    result = check_sentence_coherence("Kenya был classified as escalации this week.")
    assert result.clean is False
    assert len(result.flagged_tokens) == 2


def test_empty_sentence_is_clean():
    result = check_sentence_coherence("")
    assert result.clean is True
    assert result.flagged_tokens == []


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
