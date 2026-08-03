"""
causal_language_check.py — LLM report-writer prototype (ADR-0010)

claim_check.py enforces that there is no CAUSAL claim type in the schema
-- a sentence can never carry a checkable claim that asserts one thing
caused another. But a model could still write causal-sounding PROSE around
an honestly-typed claim ("Pressure spiked sharply following the tax
announcement, which caused nationwide unrest") even though the attached
claim itself is a legitimate, verified TEMPORAL_ORDERING or MAGNITUDE_BAND
claim. This module is the second half of that guard: a lexical scan of the
generated sentence text itself, independent of whatever claim is attached
to it.

This is deliberately a blunt instrument, not an NLP causality detector.
Per this project's own standing practice (do not introduce complexity a
concrete case hasn't justified yet), a fixed, readable, extensible
blocklist plus substring matching is the right level of engineering for a
first version -- a probabilistic classifier would itself need grounding
and evaluation this project isn't set up to do yet, and would ADD a
component this design otherwise doesn't need. False positives here are
cheap (a flagged sentence goes to human review, it isn't silently
dropped); false negatives are the real risk, so the list should grow
based on real cases found in future report-writer runs, not be treated as
complete on day one.
"""

from __future__ import annotations

from dataclasses import dataclass

# Explicit causal connectives -- words/phrases whose ordinary use asserts
# or strongly implies a causal mechanism, not just a sequence in time.
# "following" and "after" are deliberately included even though they can
# be used purely temporally ("the week following June 22") -- a false
# positive there just means a harmless sentence gets flagged for human
# review, which is the correct conservative default for this checker.
CAUSAL_CONNECTIVES = [
    "because of",
    "due to",
    "as a result of",
    "as a consequence of",
    "led to",
    "leading to",
    "resulted in",
    "resulting in",
    "caused by",
    "caused",
    "triggered by",
    "triggered",
    "sparked by",
    "sparked",
    "in response to",
    "prompted by",
    "prompted",
    "driven by",
    "following the",  # narrower than bare "following" to cut obvious false positives
    "after the announcement",
]

# Unsupported magnitude/superlative language -- claims about intensity or
# uniqueness that CLIO's own confidence-qualified data structurally cannot
# license unless a MAGNITUDE_BAND claim explicitly backs the specific word
# used (and even then, "unprecedented"/"worst since" require a historical
# comparison CLIO's marts may not actually support at the window this
# report covers).
UNSUPPORTED_SUPERLATIVES = [
    "unprecedented",
    "worst since",
    "worst in",
    "never before",
    "dramatically",
    "sharply",
    "explosively",
    "unlike anything",
    "historic escalation",
]


@dataclass
class LanguageCheckResult:
    clean: bool
    flagged_phrases: list[str]
    reason: str


def check_sentence_language(sentence: str) -> LanguageCheckResult:
    """Scans one generated sentence for causal-connective or unsupported-
    superlative language. Case-insensitive substring match on purpose --
    simple, auditable, and easy for a human reviewer to verify by eye,
    which matters more here than recall against clever phrasing a model
    might use to evade a smarter filter."""
    lowered = sentence.lower()
    flagged = []

    for phrase in CAUSAL_CONNECTIVES:
        if phrase in lowered:
            flagged.append(f"causal connective: {phrase!r}")

    for phrase in UNSUPPORTED_SUPERLATIVES:
        if phrase in lowered:
            flagged.append(f"unsupported superlative: {phrase!r}")

    if flagged:
        return LanguageCheckResult(
            clean=False,
            flagged_phrases=flagged,
            reason=(
                "Sentence contains language implying causation or unsupported "
                "magnitude/uniqueness that CLIO's claim schema cannot license, "
                "regardless of whether its attached claim independently "
                "verifies. Route to human review, do not auto-reject or "
                "auto-accept."
            ),
        )

    return LanguageCheckResult(clean=True, flagged_phrases=[], reason="No causal or unsupported-superlative language detected.")


def check_report_language(sentences: list[str]) -> list[tuple[str, LanguageCheckResult]]:
    """Convenience wrapper: checks every sentence in a report and returns
    the (sentence, result) pairs, in order, for a caller to filter on."""
    return [(s, check_sentence_language(s)) for s in sentences]
