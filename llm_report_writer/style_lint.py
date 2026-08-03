"""
style_lint.py — LLM report-writer prototype (ADR-0010)

A non-blocking companion to causal_language_check.py. That module gates
publication -- causal framing and unsupported superlatives are a
trustworthiness problem, and a report that fails that check is rejected,
full stop. This module is different on purpose: it flags common AI-
writing tics and filler/hype language for a human to glance at, but does
NOT block verification or publication. Style is a quality concern, not a
safety one, and treating it as a hard gate would conflate two different
kinds of problems this project has been careful to keep separate
throughout (see ADR-0010's own distinction between claim_check.py's
truth-checking and completeness_check.py's omission-checking -- this adds
a third, deliberately softer category: readability).

Why this exists at all: prompting can meaningfully shift a model's default
phrasing toward something plainer and more direct, but no prompt
guarantees compliance on every generation. A cheap, deterministic lint
pass catches drift (a stray "it's important to note that" creeping back
in) without requiring a human to read every single sentence looking for
it -- the same reasoning that justified causal_language_check.py's
existence, applied to a lower-stakes category.

Categories, each a curated, extensible list -- not exhaustive, not meant
to be. Grows from real cases found in future runs, same policy
causal_language_check.py states for itself.
"""

from __future__ import annotations

from dataclasses import dataclass

FILLER_OPENERS = [
    "it's important to note that",
    "it is important to note that",
    "it's worth noting that",
    "it is worth noting that",
    "in today's",
    "in the ever-evolving",
    "needless to say",
    "at the end of the day",
]

HYPE_WORDS = [
    "game-changing",
    "game changer",
    "revolutionary",
    "cutting-edge",
    "state-of-the-art",
    "seamless",
    "seamlessly",
    "unlock",
    "supercharge",
    "elevate",
    "robust solution",
    "powerful tool",
    "groundbreaking",
    "unparalleled",
]

HEDGE_PADDING = [
    "arguably one of the",
    "in many ways",
    "to some extent",
    "it could be said that",
    "some might argue",
]

CORPORATE_CLICHES = [
    "moving forward",
    "at this juncture",
    "leverage synergies",
    "circle back",
    "low-hanging fruit",
    "best-in-class",
]

ALL_CATEGORIES = {
    "filler_opener": FILLER_OPENERS,
    "hype_word": HYPE_WORDS,
    "hedge_padding": HEDGE_PADDING,
    "corporate_cliche": CORPORATE_CLICHES,
}


@dataclass
class StyleLintResult:
    clean: bool
    flags: list[str]  # e.g. ["hype_word: 'seamless'"]


def lint_sentence(sentence: str) -> StyleLintResult:
    lowered = sentence.lower()
    flags = []
    for category, phrases in ALL_CATEGORIES.items():
        for phrase in phrases:
            if phrase in lowered:
                flags.append(f"{category}: {phrase!r}")
    return StyleLintResult(clean=not flags, flags=flags)


def lint_report(sentences: list[str]) -> list[tuple[str, StyleLintResult]]:
    """Non-blocking: returns findings for a human to skim, never used to
    reject a report the way causal_language_check.py's result is."""
    return [(s, lint_sentence(s)) for s in sentences]
