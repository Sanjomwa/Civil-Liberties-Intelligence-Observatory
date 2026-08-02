"""
grounding_check.py — OTF-04 LLM extraction prototype

Programmatic verbatim-quote grounding checker. This is the mechanism the
whole prototype exists to prove: every fact an LLM claims to extract from a
source article must be checked, in code, against the actual article text —
not trusted because the model sounds confident.

Per docs/07-governance/ai-output-governance.md (requirement 2, Disclosure
and non-merge): "mandatory verbatim-quote grounding checked programmatically
against the source text." This module is that check.

Design: three-tier result, not a binary pass/fail.
  MATCHED       - the claimed quote appears in the source text, exactly or
                  after light, defensible normalization (whitespace
                  collapsing, smart-quote/dash normalization, case-fold).
                  This is the only tier a downstream consumer should treat
                  as verified.
  FUZZY         - the claimed quote does not appear verbatim, but a high
                  similarity match exists nearby (paraphrase, minor
                  transcription drift, or truncation). Flagged for human
                  review, never auto-accepted.
  NOT_FOUND     - no defensible match found anywhere in the source text.
                  Treated as a fabrication or misattribution until a human
                  says otherwise.

No network calls, no API key required — this module is pure text
processing and is fully unit-testable offline (see tests/test_grounding_check.py).

Revised 2026-08-02 after a Fable-5 advisory pass (per this project's model-
routing policy): the original tier-2 (0.995-similarity) MATCHED threshold
had a real hole — a long quote with a single digit altered (e.g. a casualty
count changed from 5 to 45) scores ~0.995 on SequenceMatcher and would have
passed as MATCHED even though the specific fact claimed is fabricated.
Fixed by requiring every digit token in the quote to appear, unchanged, in
the matched source window before tier 2 can return MATCHED — otherwise it
is demoted to FUZZY regardless of overall similarity. `autojunk=False` was
already set on both SequenceMatcher calls in the original version (checked
directly, not assumed, per this project's own verification discipline).
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from enum import Enum

CHECKER_VERSION = "1.1.0"  # bump whenever grounding logic changes; stamped onto every output record


class GroundingStatus(str, Enum):
    MATCHED = "MATCHED"
    FUZZY = "FUZZY"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class GroundingResult:
    status: GroundingStatus
    similarity: float  # 0.0-1.0, best match ratio found
    matched_span: str | None  # the actual source text the quote best aligns to, if any


# Similarity thresholds. Conservative on purpose: FUZZY is a review queue,
# not a pass. Anything below FUZZY_THRESHOLD is NOT_FOUND, full stop.
FUZZY_THRESHOLD = 0.80
EXACT_AFTER_NORMALIZATION_THRESHOLD = 0.995


def _normalize(text: str) -> str:
    """Light, defensible normalization only. Never rewrites meaning."""
    text = unicodedata.normalize("NFKC", text)
    # Normalize smart quotes/dashes to plain ASCII equivalents.
    text = (
        text.replace("‘", "'").replace("’", "'")
        .replace("“", '"').replace("”", '"')
        .replace("–", "-").replace("—", "-")
    )
    # Collapse all whitespace runs (including newlines) to a single space.
    text = re.sub(r"\s+", " ", text)
    return text.strip().casefold()


def _best_substring_ratio(needle: str, haystack: str) -> tuple[float, str | None]:
    """
    Find the best-aligning window in haystack for needle using
    difflib's SequenceMatcher, restricted to a window search so this stays
    fast on article-length text. Returns (ratio, matched_source_span).
    """
    if not needle:
        return 0.0, None

    matcher = difflib.SequenceMatcher(None, haystack, needle, autojunk=False)
    match = matcher.find_longest_match(0, len(haystack), 0, len(needle))

    if match.size == 0:
        return 0.0, None

    # Expand a window around the longest common block, sized to the quote,
    # then score the whole quote against that window with SequenceMatcher.
    window_len = max(len(needle) * 2, match.size + 40)
    center = match.a + match.size // 2
    start = max(0, center - window_len // 2)
    end = min(len(haystack), start + window_len)
    window = haystack[start:end]

    ratio = difflib.SequenceMatcher(None, window, needle, autojunk=False).ratio()
    return ratio, window


def _digit_tokens(text: str) -> list[str]:
    """Extract runs of digits (e.g. casualty counts, dates, ages) as tokens."""
    return re.findall(r"\d+", text)


def _digits_match(quote: str, matched_span: str | None) -> bool:
    """
    All digit tokens present in the quote must appear, unchanged, somewhere
    in the matched source window. Catches the case a Fable-5 advisory pass
    flagged directly: a long, mostly-real quote with one number silently
    altered (a casualty count, a participant estimate, a date) scores very
    high on overall similarity but claims a fact the source never stated.
    An empty digit list (no numbers in the quote at all) trivially passes —
    this check only constrains claims that actually contain a number.
    """
    quote_digits = _digit_tokens(quote)
    if not quote_digits:
        return True
    if matched_span is None:
        return False
    span_digits = set(_digit_tokens(matched_span))
    return all(d in span_digits for d in quote_digits)


def check_quote_grounding(quote: str, source_text: str) -> GroundingResult:
    """
    Check whether `quote` (an LLM's claimed verbatim excerpt) is actually
    present in `source_text` (the real article body).

    Returns a GroundingResult. Callers should treat only MATCHED as
    verified; FUZZY must be routed to human review; NOT_FOUND should be
    treated as a failed extraction, not silently dropped.
    """
    if not quote or not quote.strip():
        return GroundingResult(GroundingStatus.NOT_FOUND, 0.0, None)

    norm_quote = _normalize(quote)
    norm_source = _normalize(source_text)

    # Tier 1: exact substring after normalization only (the strongest,
    # most defensible check — no fuzziness at all). A literal substring
    # match trivially preserves every digit, so no separate digit check
    # is needed on this path.
    if norm_quote in norm_source:
        return GroundingResult(GroundingStatus.MATCHED, 1.0, quote)

    # Tier 2: best-effort alignment score for near-matches (OCR-ish noise,
    # a dropped word, minor punctuation drift the model introduced while
    # "quoting"). Still requires a high bar, AND every digit the quote
    # claims must independently verify against the matched window — high
    # textual similarity alone is not sufficient once numbers are involved.
    ratio, window = _best_substring_ratio(norm_quote, norm_source)

    if ratio >= EXACT_AFTER_NORMALIZATION_THRESHOLD:
        if _digits_match(norm_quote, window):
            return GroundingResult(GroundingStatus.MATCHED, ratio, window)
        return GroundingResult(GroundingStatus.FUZZY, ratio, window)
    if ratio >= FUZZY_THRESHOLD:
        return GroundingResult(GroundingStatus.FUZZY, ratio, window)

    return GroundingResult(GroundingStatus.NOT_FOUND, ratio, window)


def check_extraction_record(record: dict, source_text: str) -> GroundingResult:
    """Convenience wrapper: grounds a single extraction record's
    'verbatim_quote' field against source_text."""
    quote = record.get("verbatim_quote", "")
    return check_quote_grounding(quote, source_text)
