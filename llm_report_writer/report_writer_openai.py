"""
report_writer_openai.py — LLM report-writer prototype (ADR-0010)

The one component in this prototype that makes a live LLM call. Everything
else (deterministic_analysis.py, claim_check.py, causal_language_check.py,
completeness_check.py) is pure, offline-testable code, and stays that way
-- this file's whole job is narrow: given a fixed list of already-computed,
already-true claims, ask the model to phrase them as readable prose, one
or more sentences per claim, each sentence tagged with exactly which claim
it's narrating. The model is never shown raw mart data and never invents a
claim -- see deterministic_analysis.py's docstring for why that ordering
(compute first, narrate second) is a stronger safety property than
generate-then-check.

Same operating constraint as ADR-0009's extract.py/extract_openai.py:
this assistant does not hold and will never accept an API key. Sam runs
this file himself, with his own OPENAI_API_KEY in this repo's .env, the
same as the extraction layer.

Design notes, carried directly from the lessons already learned building
and shipping ADR-0009's extract_openai.py:
  - OPENAI_API_KEY read via python-dotenv, matching this repo's existing
    convention.
  - gpt-5.4-mini requires `max_completion_tokens`, not `max_tokens`
    (confirmed live against the real API during ADR-0009's build).
  - `finish_reason == "length"` is a hard failure, never a silent partial
    success.
  - `message.refusal` is checked explicitly before treating a response as
    usable JSON.
  - `response.model` (the real resolved snapshot) is recorded, not just
    the requested alias.
  - The system prompt is hashed into `prompt_version_hash`, exactly as
    ADR-0009 did, so future prompt edits stay distinguishable from past
    ones in any stored output.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

MODEL = "gpt-5.4-mini"
MAX_COMPLETION_TOKENS = 4000  # generous for a single-window report; a real
# multi-claim window in this prototype's fixture tops out around 20 claims

SYSTEM_PROMPT = """You are a report-writing assistant with a narrow, strictly bounded job. \
You will be given a fixed list of pre-verified claims about a civil-liberties pressure \
monitoring window. Each claim is already true -- it was computed and checked by \
deterministic code before you ever saw it.

Your ONLY job: write one or more short, clear, factual sentences narrating EACH claim \
in the list, in a natural reading order. For every sentence you write, you MUST specify \
which claim index (0-based, into the list you were given) that sentence narrates.

Strict rules:
1. Do not write any sentence that isn't narrating one of the given claims. If you think \
something else is worth saying, don't say it -- you have no source for it beyond this list.
2. Do not invent a claim_index that isn't in the given list. Every claim_index you use \
must be a valid index into the claims you were given.
3. Never use causal language -- no "because", "due to", "led to", "triggered by", "caused", \
"resulted in", "in response to", or similar. The claims you were given describe WHAT \
happened and WHEN, never WHY. If a claim is a TEMPORAL_ORDERING claim, describe it as a \
sequence ("X was Y, then later became Z") -- never imply the first event caused the second.
4. Never use unsupported superlatives or intensifiers not present in the claim itself -- \
no "dramatically", "sharply", "unprecedented", "worst since", unless the claim's own \
claimed_band or claimed_value is literally that word.
5. Write plainly and factually. This is a monitoring report, not a narrative feature story.
6. You may write multiple sentences for the same claim_index if needed for clarity, but \
every sentence must map to exactly one claim_index -- never combine two claims into one \
sentence that could be misread as connecting them causally.
7. Do NOT write any disclosure, caveat, or qualification about data quality, confidence, \
synthetic data, or predictiveness yourself -- for example, never write anything like "this \
data is synthetic," "this classification carries lower confidence," or "this is not a \
prediction." A separate system step appends the exact required disclosures automatically \
after you finish. If you attempt your own version of a required disclosure, it risks \
burying or diluting the fixed one the system adds -- simply state each claim plainly and \
let the system handle every disclosure.

House style, followed exactly:
- Write in plain, direct sentences. State findings, don't announce them -- never open a \
sentence with "It's important to note that," "It's worth noting," or similar throat-clearing.
- Never use hype or marketing language: no "seamless," "cutting-edge," "game-changing," \
"robust," "powerful," "unparalleled," or similar. This is a monitoring report, not a pitch.
- Never pad a sentence with vague hedging like "arguably one of the," "in many ways," or \
"to some extent." If a claim's confidence is genuinely reduced, say so specifically (e.g. \
"this classification carries lower confidence") rather than hedging vaguely.
- Avoid corporate cliches ("moving forward," "at this juncture," "leverage").
- Prefer specific numbers and dates over vague summary language. Say what the data says, \
not an impression of what the data says.
- Keep sentences short. One claim per sentence, stated once, clearly.

Output ONLY a JSON object matching the required schema. No prose, no markdown fences, no \
commentary outside the schema."""

PROMPT_VERSION_HASH = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]

_SENTENCE_SCHEMA = {
    "type": "object",
    "properties": {
        "claim_index": {"type": "integer"},
        "text": {"type": "string"},
    },
    "required": ["claim_index", "text"],
    "additionalProperties": False,
}

_TOP_LEVEL_SCHEMA = {
    "type": "object",
    "properties": {
        "sentences": {"type": "array", "items": _SENTENCE_SCHEMA},
    },
    "required": ["sentences"],
    "additionalProperties": False,
}


class ReportGenerationError(RuntimeError):
    """Raised for any condition that means the generated report cannot be
    trusted before even reaching claim/language/completeness verification:
    a safety refusal, a truncated response, or malformed JSON."""


def _build_user_message(country: str, week_start: str, week_end: str, claims: list[dict]) -> str:
    numbered = "\n".join(f"[{i}] {json.dumps(c)}" for i, c in enumerate(claims))
    return (
        f"Window: {country}, {week_start} through {week_end}.\n\n"
        f"Claims (narrate each one, tagged by its index):\n{numbered}"
    )


def _repo_root() -> Path:
    """Pure, side-effect-free, and independently testable on purpose --
    TD-79 (2026-08-03) was a bug buried inside _get_client() that no offline
    test caught, because the whole function was untestable without either a
    real API key or extensive mocking. Pulling just the path computation out
    means the fix itself can be unit-tested without touching the network or
    process exit code.

    This used to resolve to llm_report_writer/ itself
    (Path(__file__).resolve().parent), not the actual repo root where .env
    really lives -- found live during the report-writer's first live-build
    session, masked there only because OPENAI_API_KEY was already exported
    directly in that Codespace's shell. .parent.parent is llm_report_writer/'s
    own parent directory -- the actual repo root, where .env really lives."""
    return Path(__file__).resolve().parent.parent


def _get_client():
    repo_root = _repo_root()
    try:
        from dotenv import load_dotenv
        load_dotenv(repo_root / ".env")
    except ImportError:
        pass  # fine in this planning-environment prototype; the live build mirrors extract_openai.py's real convention

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "FATAL: OPENAI_API_KEY is not set. This script makes a real, billed "
            "API call and must be run with your own key -- see README.md.\n"
            "    export OPENAI_API_KEY=sk-...\n"
            "    python3 report_writer_openai.py",
            file=sys.stderr,
        )
        sys.exit(1)

    from openai import OpenAI
    return OpenAI(api_key=api_key)


def generate_report_sentences(country: str, week_start: str, week_end: str, claims: list[dict]) -> dict:
    """Calls gpt-5.4-mini once, returns a dict with 'sentences' (list of
    {claim_index, text}) plus provenance metadata. Raises
    ReportGenerationError on refusal, truncation, or invalid JSON. Does
    NOT run claim/language/completeness verification -- that's
    verify_report.py's job, kept separate so the generation step and the
    verification step can each be tested and reasoned about independently."""
    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": _build_user_message(country, week_start, week_end, claims)},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "report_sentences", "strict": True, "schema": _TOP_LEVEL_SCHEMA},
        },
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )

    choice = response.choices[0]
    message = choice.message

    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ReportGenerationError(f"OpenAI declined this report request with an explicit safety refusal: {refusal!r}")

    if choice.finish_reason == "length":
        raise ReportGenerationError("Response was truncated (finish_reason='length') -- raise MAX_COMPLETION_TOKENS.")
    if choice.finish_reason != "stop":
        raise ReportGenerationError(f"Unexpected finish_reason={choice.finish_reason!r}; refusing to trust this output.")

    payload = json.loads(message.content)

    return {
        "sentences": payload.get("sentences", []),
        "extraction_model": response.model,
        "prompt_version_hash": PROMPT_VERSION_HASH,
        "generated_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "llm_derived": True,
    }
