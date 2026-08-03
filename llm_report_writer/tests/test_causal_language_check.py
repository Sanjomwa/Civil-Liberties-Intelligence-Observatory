"""
tests/test_causal_language_check.py — LLM report-writer prototype (ADR-0010)

Proves the lexical causal-language guard catches sentences that imply
mechanism or unsupported magnitude, independent of whether the sentence's
attached claim (checked separately by claim_check.py) is itself honest.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from causal_language_check import check_sentence_language  # noqa: E402


def test_clean_sentence_passes():
    sentence = "Kenya's regime classification was CRISIS for the week of June 22, 2024."
    result = check_sentence_language(sentence)
    assert result.clean is True, result.reason


def test_causal_connective_flagged():
    sentence = "Pressure increased because of the tax announcement."
    result = check_sentence_language(sentence)
    assert result.clean is False
    assert any("causal connective" in f for f in result.flagged_phrases)


def test_led_to_flagged():
    sentence = "The bill's tabling led to a MOBILISATION classification."
    result = check_sentence_language(sentence)
    assert result.clean is False


def test_triggered_flagged():
    sentence = "The protest was triggered by the finance bill."
    result = check_sentence_language(sentence)
    assert result.clean is False


def test_unsupported_superlative_flagged():
    sentence = "Pressure spiked dramatically, an unprecedented escalation."
    result = check_sentence_language(sentence)
    assert result.clean is False
    assert any("superlative" in f for f in result.flagged_phrases)


def test_sharply_flagged():
    sentence = "The composite pressure score rose sharply on June 25."
    result = check_sentence_language(sentence)
    assert result.clean is False


def test_pure_temporal_following_the_is_flagged_conservatively():
    # "following the" is treated as causal-leaning even in a fairly neutral
    # sentence -- a deliberate conservative default (false positives are
    # cheap, false negatives are the real risk here).
    sentence = "Following the announcement, the regime classification changed to MOBILISATION."
    result = check_sentence_language(sentence)
    assert result.clean is False


def test_neutral_temporal_sequencing_passes():
    sentence = "The classification changed from ESCALATION on June 15 to CRISIS on June 22."
    result = check_sentence_language(sentence)
    assert result.clean is True, result.reason


def test_case_insensitivity():
    sentence = "This was CAUSED BY the tax bill."
    result = check_sentence_language(sentence)
    assert result.clean is False


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
