"""
extract_openai.py — OTF-04 LLM extraction prototype

Calls OpenAI's gpt-5.4-mini with structured outputs (a strict JSON schema
via response_format) to extract discrete, location-specific protest events
from a source article's body text.

Structured outputs guarantee *shape*, not *truth* -- the model can still
produce a well-formed JSON object whose verbatim_quote field is fabricated
or paraphrased. grounding_check.py is the actual control on that; this
module's only job is to get a clean, schema-valid extraction out of the
model and stamp it with enough provenance metadata that a downstream
consumer never has to guess what produced a given record.

Design notes (each load-bearing, not incidental):
  - `OPENAI_API_KEY` is read from the environment via python-dotenv,
    matching this repo's existing convention (see streamlit/core/config.py,
    `load_dotenv(REPO_ROOT / ".env")`). Missing key -> loud failure,
    nonzero exit, not a silent no-op.
  - gpt-5.4-mini rejects the `max_tokens` parameter (confirmed live against
    the real API before this file was written, per this project's own
    "verify before acting" discipline) -- `max_completion_tokens` is used
    instead, set generously so a real extraction never silently truncates.
  - `finish_reason == "length"` is treated as a hard failure (truncated
    JSON), not a partial success -- raised, never swallowed.
  - `message.refusal` is checked explicitly before the response is treated
    as usable JSON. Protest/violence subject matter is exactly the kind of
    content where a safety refusal is more likely to fire than on typical
    business text.
  - `response.model` (the real snapshot the API actually ran, e.g.
    "gpt-5.4-mini-2026-03-17", confirmed live -- not just the requested
    alias "gpt-5.4-mini") is recorded on every record, since aliases can
    silently repoint to a different underlying snapshot over time.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(REPO_ROOT / ".env")

MODEL = "gpt-5.4-mini"
# Generous on purpose: the live probe that shaped this file used a 3-sentence
# sample, but the real seed articles run 20-30+ extractable events each, at
# roughly 100-150 JSON tokens per event (description + a long verbatim_quote).
# If gpt-5.4-mini has any reasoning-token overhead, that also counts against
# this budget before visible output starts. A too-low value here fails
# silently from run_extraction.py's perspective (ExtractionError is caught
# per-article, not fatal) -- a truncated article just drops to zero records
# while the run still exits 0. Set high enough that truncation should not
# happen for either seed article; if it still does, that is a real signal
# to investigate, not to raise this value again reflexively.
MAX_COMPLETION_TOKENS = 16000

EVENT_FIELDS = [
    "event_date",
    "location_text",
    "approx_participants",
    "event_type",
    "description",
    "verbatim_quote",
]

SYSTEM_PROMPT = """You are a careful evidence-extraction assistant. You will be given the \
full body text of one real news article about protest activity in Kenya.

Extract every discrete, location-specific event described in the article. \
An "event" is a single concrete happening tied to a specific place: a protest \
march, a building or office stormed or looted, a person shot, a road blocked, \
an act of arson, a teargassing incident, a clash with police, and similar. \
Do not merge multiple distinct happenings into one record, and do not invent \
an event the text does not actually describe.

For every event you extract, you MUST include a `verbatim_quote` field that is \
an EXACT, character-for-character excerpt copied from the article text -- not \
a paraphrase, not a summary, not a reconstruction from memory. If you cannot \
find an exact sentence or clause in the article that supports the event you \
are about to record, DO NOT invent one -- omit that event entirely rather than \
fabricate a quote for it.

For `approx_participants`, copy the article's own wording for scale if it gives \
one (e.g. "hundreds", "thousands", "a crowd") verbatim. Do not compute, infer, \
or estimate a number yourself. If the article gives no participant-scale \
wording for this event, use null.

For `event_date`, use the article's own stated or implied date for this specific \
event if the text supports one; otherwise use null. Do not invent a date.

`location_text` should be the specific place name the article associates with \
this event (a town, a named building, a specific road or district) -- not just \
the country.

`event_type` should be a short label (e.g. "protest march", "arson", \
"teargassing", "building stormed", "person shot", "road blocked").

`description` is a one-to-two sentence factual description of the event, in \
your own words, grounded in the verbatim_quote.

Extract only what the article actually states. This is a grounding-and-\
disclosure prototype: every claim here is checked programmatically against \
the source text after you return it, and any verbatim_quote that cannot be \
found in the source will be flagged NOT_FOUND or FUZZY and never counted as \
verified."""

PROMPT_VERSION_HASH = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]

_EVENT_SCHEMA = {
    "type": "object",
    "properties": {
        "event_date": {"type": ["string", "null"]},
        "location_text": {"type": "string"},
        "approx_participants": {"type": ["string", "null"]},
        "event_type": {"type": "string"},
        "description": {"type": "string"},
        "verbatim_quote": {"type": "string"},
    },
    "required": EVENT_FIELDS,
    "additionalProperties": False,
}

_TOP_LEVEL_SCHEMA = {
    "type": "object",
    "properties": {
        "events": {"type": "array", "items": _EVENT_SCHEMA},
    },
    "required": ["events"],
    "additionalProperties": False,
}


class ExtractionError(RuntimeError):
    """Raised for any condition that means the extraction cannot be trusted:
    a safety refusal, a truncated response, or malformed JSON."""


def _get_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print(
            "FATAL: OPENAI_API_KEY is not set. Add it to this repo's .env "
            "(gitignored) as OPENAI_API_KEY=sk-... and re-run. This script "
            "will not silently skip the live extraction step.",
            file=sys.stderr,
        )
        sys.exit(1)

    from openai import OpenAI

    return OpenAI(api_key=api_key)


def extract_events_from_article(source_article_id: str, article_body_text: str) -> list[dict]:
    """Calls gpt-5.4-mini once on the given article body text and returns a
    list of stamped, schema-valid (but not yet grounding-checked) event
    records. Raises ExtractionError on refusal or truncation."""
    client = _get_client()

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": article_body_text},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "protest_event_extraction",
                "strict": True,
                "schema": _TOP_LEVEL_SCHEMA,
            },
        },
        max_completion_tokens=MAX_COMPLETION_TOKENS,
    )

    choice = response.choices[0]
    message = choice.message

    refusal = getattr(message, "refusal", None)
    if refusal:
        raise ExtractionError(
            f"OpenAI declined this article ({source_article_id}) with an "
            f"explicit safety refusal, not a parse failure: {refusal!r}"
        )

    if choice.finish_reason == "length":
        raise ExtractionError(
            f"Response for {source_article_id} was truncated (finish_reason="
            f"'length') before completing valid JSON -- increase "
            f"MAX_COMPLETION_TOKENS rather than treating this as a partial "
            f"success."
        )

    if choice.finish_reason != "stop":
        raise ExtractionError(
            f"Unexpected finish_reason={choice.finish_reason!r} for "
            f"{source_article_id}; refusing to treat as a trusted extraction."
        )

    payload = json.loads(message.content)
    events = payload.get("events", [])

    real_model = response.model  # the actual snapshot the API ran, e.g. gpt-5.4-mini-2026-03-17
    now_iso = datetime.now(timezone.utc).isoformat()

    stamped = []
    for event in events:
        record = {field: event.get(field) for field in EVENT_FIELDS}
        record.update(
            {
                "source_article_id": source_article_id,
                "extraction_model": real_model,
                "extraction_timestamp_utc": now_iso,
                "llm_derived": True,
                "prompt_version_hash": PROMPT_VERSION_HASH,
            }
        )
        stamped.append(record)

    return stamped
