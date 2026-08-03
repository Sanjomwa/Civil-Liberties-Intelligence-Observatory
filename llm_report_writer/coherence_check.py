"""
coherence_check.py — LLM report-writer prototype (ADR-0010)

TD-78 (found 2026-08-03, during the first live comparison run against real
BigQuery data): one generated sentence in an otherwise-clean 11-window run
contained a stray Armenian-script token mid-sentence ("Kenya was classified
as STABLE for the week սկս starting 2024-03-23.") that still passed every
one of `verify_report.py`'s four verification layers. That's not a bug in
those layers -- they check factual truth (`claim_check.py`), causal/
superlative framing (`causal_language_check.py`), and required-disclosure
presence (`completeness_check.py`), three properties a garbled token
doesn't violate on its own. Nothing in the existing design checks whether a
sentence is actually coherent, well-formed text in the report's target
language, which is its own, fourth kind of property.

Same design posture as `style_lint.py`, and deliberately built as its own
module rather than folded into that one: this is a quality/readability
concern, not a trust boundary, so it stays non-blocking and structurally
separate from the four checks `verify_report.py` actually gates on. Unlike
`style_lint.py`'s curated phrase lists, this is a character-level check
(is every token built from characters consistent with the report's
expected script), not a substring match against known-bad phrasing --
different mechanism, same "flag for a human to skim, never auto-reject"
philosophy, and the same explicit tolerance for false positives over false
negatives that `causal_language_check.py` states for itself.
"""

from __future__ import annotations

import unicodedata
from dataclasses import dataclass

# Characters whose Unicode name starts with one of these prefixes are
# treated as legitimate in an English-language report even though they
# aren't plain ASCII -- accented Latin letters (place names, loanwords) and
# combining diacritics chief among them. Everything else non-ASCII is
# suspicious by default: this is a blunt, auditable rule, not a real
# language-identification model, on the same "simple and inspectable beats
# clever" reasoning this project has already applied to
# causal_language_check.py and style_lint.py.
_ALLOWED_NAME_PREFIXES = ("LATIN", "COMBINING")

# A short allowlist of common, legitimate non-Latin-named punctuation and
# symbols that show up in ordinary English prose about numbers/dates and
# should not be flagged. Kept short and reviewable on purpose -- grows from
# real cases, same policy every lexical list in this project follows.
_ALLOWED_CHARS = {
    "–",  # EN DASH
    "—",  # EM DASH
    "‘",  # LEFT SINGLE QUOTATION MARK
    "’",  # RIGHT SINGLE QUOTATION MARK (curly apostrophe)
    "“",  # LEFT DOUBLE QUOTATION MARK
    "”",  # RIGHT DOUBLE QUOTATION MARK
    "…",  # HORIZONTAL ELLIPSIS
    "°",  # DEGREE SIGN
    "£",  # POUND SIGN
    "€",  # EURO SIGN
}


def _char_is_suspicious(ch: str) -> bool:
    if ch.isascii():
        return False
    if ch in _ALLOWED_CHARS:
        return False
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return True  # unnamed / control / unassigned code point -- treat as suspicious
    return not name.startswith(_ALLOWED_NAME_PREFIXES)


def _token_is_suspicious(token: str) -> bool:
    return any(_char_is_suspicious(ch) for ch in token)


@dataclass
class CoherenceResult:
    clean: bool
    flagged_tokens: list[str]  # the exact tokens that tripped the check, in order


def check_sentence_coherence(sentence: str) -> CoherenceResult:
    """Splits on whitespace (deliberately simple -- this is a screen for
    garbled/foreign-script tokens, not a tokenizer) and flags any token
    containing at least one character outside the allowed set."""
    flagged = [tok for tok in sentence.split() if _token_is_suspicious(tok)]
    return CoherenceResult(clean=not flagged, flagged_tokens=flagged)


def check_report_coherence(sentences: list[str]) -> list[tuple[str, CoherenceResult]]:
    """Non-blocking, same contract as style_lint.lint_report(): returns
    findings for a human to skim, never used to reject a report the way
    verify_report.py's four gated checks are."""
    return [(s, check_sentence_coherence(s)) for s in sentences]
