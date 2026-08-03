"""
tests/test_style_lint.py — LLM report-writer prototype (ADR-0010)

Proves style_lint.py catches the phrasing categories it claims to, and
confirms plain, direct sentences pass clean. Non-blocking by design -- this
test suite proves detection works, not that it gates anything (it doesn't;
see verify_report.py, which never calls this module).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from style_lint import lint_sentence  # noqa: E402


def test_plain_sentence_is_clean():
    result = lint_sentence("Kenya's regime classification for the week of June 22, 2024 was CRISIS.")
    assert result.clean is True, result.flags


def test_filler_opener_flagged():
    result = lint_sentence("It's important to note that Kenya's classification was CRISIS.")
    assert result.clean is False
    assert any("filler_opener" in f for f in result.flags)


def test_hype_word_flagged():
    result = lint_sentence("CLIO's pipeline offers a seamless view of civil-liberties pressure.")
    assert result.clean is False
    assert any("hype_word" in f for f in result.flags)


def test_hedge_padding_flagged():
    result = lint_sentence("This is arguably one of the most significant weeks in the dataset.")
    assert result.clean is False
    assert any("hedge_padding" in f for f in result.flags)


def test_corporate_cliche_flagged():
    result = lint_sentence("Moving forward, the classification remained CRISIS.")
    assert result.clean is False
    assert any("corporate_cliche" in f for f in result.flags)


def test_case_insensitive():
    result = lint_sentence("This is REVOLUTIONARY data.")
    assert result.clean is False


def test_multiple_flags_all_reported():
    result = lint_sentence("It's important to note that this seamless, game-changing tool leverages synergies.")
    assert result.clean is False
    assert len(result.flags) >= 3


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
