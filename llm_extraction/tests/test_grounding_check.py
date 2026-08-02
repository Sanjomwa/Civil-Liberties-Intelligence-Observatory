"""
tests/test_grounding_check.py — OTF-04 LLM extraction prototype

Proves the grounding checker itself works, without needing any LLM API
call or API key. Fixtures are: (a) real sentences copied verbatim from the
two real source articles in source_articles_cache/, which must MATCH; (b)
quotes that are close paraphrases of real sentences, which must land as
FUZZY, not MATCHED; (c) quotes with no basis in either article at all,
which must be NOT_FOUND; (d) a case with a single digit silently altered
in an otherwise-real quote, which must NOT be MATCHED (the Fable-review
fix). This is the offline evidence that the grounding mechanism itself is
sound, independent of whether a live extraction has been run yet.

Run with:
    pip install pytest --break-system-packages
    pytest llm_extraction/tests/test_grounding_check.py -v
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from grounding_check import GroundingStatus, check_quote_grounding  # noqa: E402

SOURCE_DIR = os.path.join(os.path.dirname(__file__), "..", "source_articles_cache")


def _load(article_id: str) -> str:
    path = os.path.join(SOURCE_DIR, f"{article_id}.txt")
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()
    return raw.split("===BODY===", 1)[1].strip()


STAR_TEXT = _load("article_001_the-star")
NATION_TEXT = _load("article_002_daily-nation")


def test_exact_quote_matches_star():
    quote = "Crowds had gathered as early as 7 am around the Kenya National Archives."
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.MATCHED
    assert result.similarity == 1.0


def test_exact_quote_matches_star_kericho():
    quote = (
        "On Tuesday some of the residents could be seen protesting at a petrol "
        "station within the county where they pulled down a UDA wheelbarrow "
        "erected next to the petrol station."
    )
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.MATCHED


def test_exact_quote_matches_nation_tana_river():
    quote = "In Tana River County, protesters marched towards the Office of Galole Member of Parliament Said Hiribae in Hola town."
    result = check_quote_grounding(quote, NATION_TEXT)
    assert result.status == GroundingStatus.MATCHED


def test_exact_quote_with_smart_quotes_still_matches():
    quote = "tension escalated outside the country’s legislature."
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.MATCHED


def test_exact_quote_across_whitespace_reflow():
    quote = "The   county court and enforcement offices\nin Eldoret were on Tuesday torched"
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.MATCHED


def test_paraphrase_is_not_matched():
    quote = "Large crowds of young demonstrators flooded Mombasa's downtown area."
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status != GroundingStatus.MATCHED


def test_paraphrase_lands_fuzzy_or_not_found():
    quote = "Governor Mutahi Kahiga urged young people in Nyeri to keep protesting."
    result = check_quote_grounding(quote, NATION_TEXT)
    assert result.status in (GroundingStatus.FUZZY, GroundingStatus.NOT_FOUND)


def test_fabricated_quote_not_found_in_star():
    quote = "Protesters in Kericho set fire to the county governor's residence overnight."
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.NOT_FOUND


def test_fabricated_quote_not_found_in_nation():
    quote = "President Ruto personally addressed the crowd in Meru and apologized for the Finance Bill."
    result = check_quote_grounding(quote, NATION_TEXT)
    assert result.status == GroundingStatus.NOT_FOUND


def test_fabricated_number_not_found():
    quote = "At least 14 protesters were confirmed dead in Nakuru by evening."
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.NOT_FOUND


def test_empty_quote_is_not_found():
    result = check_quote_grounding("", STAR_TEXT)
    assert result.status == GroundingStatus.NOT_FOUND


def test_altered_digit_in_otherwise_real_quote_is_not_matched():
    tampered = "At least 13 protesters were reportedly shot outside Parliament Buildings as a mob battled police."
    result = check_quote_grounding(tampered, STAR_TEXT)
    assert result.status != GroundingStatus.MATCHED


def test_unaltered_digit_quote_still_matches():
    quote = "Sh13.4 billion which had been proposed in the Bill"
    result = check_quote_grounding(quote, NATION_TEXT)
    assert result.status == GroundingStatus.MATCHED


def test_quote_from_wrong_article_is_not_found():
    quote = "In Kirinyaga, Junior Secondary School teachers joined the demonstration"
    result = check_quote_grounding(quote, STAR_TEXT)
    assert result.status == GroundingStatus.NOT_FOUND


if __name__ == "__main__":
    import inspect
    failures = 0
    tests = [
        (name, fn) for name, fn in list(globals().items())
        if name.startswith("test_") and inspect.isfunction(fn)
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
