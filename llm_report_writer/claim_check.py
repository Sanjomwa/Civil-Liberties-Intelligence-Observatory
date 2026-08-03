"""
claim_check.py — LLM report-writer prototype (ADR-0010)

The deterministic half of the report-writer's grounding mechanism. Per
ADR-0010 (superseding ADR-0009's raw-extraction framing as the AI layer's
flagship story): the LLM never asserts a new fact from outside CLIO's own
verified marts. Every sentence it writes must carry a structured, machine-
checkable CLAIM alongside it. This module re-executes each claim against
the real data it claims to describe and returns whether it actually holds.

Design principle carried directly from grounding_check.py (ADR-0009): do
not trust the model's prose. Trust only what a separate, deterministic,
fully-tested piece of code can independently re-derive from the same data
the model was given. The difference here is what gets re-derived — not a
literal quote, but a re-executed query result.

Five claim types, deliberately not more:
  CLASSIFICATION    - asserts a categorical value (e.g. a week's regime
                       label) equals a specific stated value.
  COUNT              - asserts a count of qualifying rows over a window
                       (e.g. "3 weeks were CRISIS or above").
  COMPARISON         - asserts a relative ordering between two values, or
                       a value against a literal threshold.
  TEMPORAL_ORDERING  - asserts that state A genuinely preceded state B in
                       time, and what those states actually were. This is
                       a *sequence* claim, never a *causal* one.
  MAGNITUDE_BAND     - asserts a raw value falls within one of CLIO's own
                       already-defined bands (e.g. pressure_level).

There is deliberately NO "causal" claim type. A model is never permitted
to assert that one thing caused, triggered, or resulted from another --
CLIO's data can support sequence, not mechanism. See
causal_language_check.py for the companion lexical guard that catches an
attempt to smuggle causal framing into a sentence's prose even when its
attached claim is honestly one of the five types above.

Each claim is checked against a `DataContext` -- an abstraction over
"however the real values get looked up." In this offline prototype that's
the fixtures/ mock tables; in a live build it is a real BigQuery query.
The checking logic itself is identical either way -- only the lookup
implementation changes. This mirrors exactly how grounding_check.py's
logic never needed to change when OTF-04 moved from a planning-environment
prototype to a live Bruin-adjacent script.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Callable

# Severity order for CLIO's own regime vocabulary (ADR-0002). Fixed here,
# not inferred, so a claim can never assert an ordering CLIO itself
# doesn't recognize.
REGIME_SEVERITY_ORDER = ["STABLE", "MOBILISATION", "ESCALATION", "CONFLICT", "CRISIS"]

# CLIO's own pressure_level bands (TD-44 notes these haven't been
# empirically re-derived, but they are the real, currently-live thresholds
# -- a claim checker must check against what CLIO actually uses today, not
# an idealized version).
PRESSURE_LEVEL_BANDS = {
    "LOW": (float("-inf"), 3.0),
    "MODERATE": (3.0, 5.0),
    "ELEVATED": (5.0, 7.0),
    "SEVERE": (7.0, float("inf")),
}


class ClaimType(str, Enum):
    CLASSIFICATION = "CLASSIFICATION"
    COUNT = "COUNT"
    COMPARISON = "COMPARISON"
    TEMPORAL_ORDERING = "TEMPORAL_ORDERING"
    MAGNITUDE_BAND = "MAGNITUDE_BAND"


class ClaimStatus(str, Enum):
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    MALFORMED = "MALFORMED"  # the claim itself is not well-formed enough to check


@dataclass
class ClaimResult:
    status: ClaimStatus
    reason: str  # human-readable explanation, always populated, for both pass and fail


@dataclass
class DataContext:
    """Wraps whatever the real lookup mechanism is (mock fixture functions
    in this prototype; a real BigQuery client in a live build) behind a
    fixed interface claim_check.py depends on. Swapping the live build in
    means implementing these three callables against real queries --
    nothing in check_claim() below needs to change."""

    lookup_regime: Callable[[str, str], dict | None]
    lookup_daily: Callable[[str, str], dict | None]
    count_weeks_at_or_above: Callable[[str, str, str, str], int]


def check_claim(claim: dict, ctx: DataContext) -> ClaimResult:
    """Dispatches to the right checker for claim['claim_type']. `claim` is
    a plain dict matching the schema documented per claim type below --
    this is deliberately the same shape the LLM's structured-output schema
    will require it to emit, so what the model returns and what gets
    checked are structurally identical, not translated between formats."""

    claim_type = claim.get("claim_type")

    if claim_type == ClaimType.CLASSIFICATION.value:
        return _check_classification(claim, ctx)
    if claim_type == ClaimType.COUNT.value:
        return _check_count(claim, ctx)
    if claim_type == ClaimType.COMPARISON.value:
        return _check_comparison(claim, ctx)
    if claim_type == ClaimType.TEMPORAL_ORDERING.value:
        return _check_temporal_ordering(claim, ctx)
    if claim_type == ClaimType.MAGNITUDE_BAND.value:
        return _check_magnitude_band(claim, ctx)

    return ClaimResult(
        ClaimStatus.MALFORMED,
        f"Unknown or missing claim_type {claim_type!r}. Valid types: "
        f"{[t.value for t in ClaimType]}. A claim with no recognized type "
        f"can never be VERIFIED -- there is no 'benefit of the doubt' tier.",
    )


def _check_classification(claim: dict, ctx: DataContext) -> ClaimResult:
    """Schema: {claim_type, country, week_start_date, source_column,
    claimed_value}. source_column is currently only 'regime_label' --
    listed explicitly rather than accepting any column name, so a claim
    can't quietly point at a column this checker was never designed to
    validate."""
    country = claim.get("country")
    week_start_date = claim.get("week_start_date")
    source_column = claim.get("source_column")
    claimed_value = claim.get("claimed_value")

    if source_column != "regime_label":
        return ClaimResult(
            ClaimStatus.MALFORMED,
            f"CLASSIFICATION claims may only target 'regime_label' in this "
            f"prototype, got {source_column!r}.",
        )

    row = ctx.lookup_regime(country, week_start_date)
    if row is None:
        return ClaimResult(
            ClaimStatus.FAILED,
            f"No regime row found for {country}, week {week_start_date} -- "
            f"cannot verify a claim about data that doesn't exist.",
        )

    actual = row["regime_label"]
    if actual == claimed_value:
        return ClaimResult(
            ClaimStatus.VERIFIED,
            f"{country} week {week_start_date}: regime_label is indeed {actual!r}.",
        )
    return ClaimResult(
        ClaimStatus.FAILED,
        f"Claimed regime_label {claimed_value!r} for {country} week "
        f"{week_start_date}, but the actual recorded value is {actual!r}.",
    )


def _check_count(claim: dict, ctx: DataContext) -> ClaimResult:
    """Schema: {claim_type, country, regime_order_min, week_start,
    week_end, claimed_count}."""
    country = claim.get("country")
    regime_order_min = claim.get("regime_order_min")
    week_start = claim.get("week_start")
    week_end = claim.get("week_end")
    claimed_count = claim.get("claimed_count")

    if regime_order_min not in REGIME_SEVERITY_ORDER:
        return ClaimResult(
            ClaimStatus.MALFORMED,
            f"regime_order_min {regime_order_min!r} is not one of CLIO's "
            f"own recognized regime labels {REGIME_SEVERITY_ORDER}.",
        )
    if not isinstance(claimed_count, int):
        return ClaimResult(
            ClaimStatus.MALFORMED,
            f"claimed_count must be an integer, got {claimed_count!r}.",
        )

    actual_count = ctx.count_weeks_at_or_above(country, regime_order_min, week_start, week_end)
    if actual_count == claimed_count:
        return ClaimResult(
            ClaimStatus.VERIFIED,
            f"{country} had exactly {actual_count} week(s) at or above "
            f"{regime_order_min} between {week_start} and {week_end}, "
            f"matching the claim.",
        )
    return ClaimResult(
        ClaimStatus.FAILED,
        f"Claimed {claimed_count} week(s) at or above {regime_order_min} "
        f"for {country} between {week_start} and {week_end}, but the "
        f"actual re-executed count is {actual_count}.",
    )


def _resolve_value(ref: dict, ctx: DataContext) -> float | None:
    """Resolves either a {country, date, source_column} reference to a real
    fact_country_pressure_daily value, or a bare {"literal": <number>}."""
    if "literal" in ref:
        return float(ref["literal"])

    country = ref.get("country")
    date = ref.get("date")
    source_column = ref.get("source_column")
    if source_column != "composite_pressure_score":
        return None

    row = ctx.lookup_daily(country, date)
    if row is None:
        return None
    return float(row["composite_pressure_score"])


def _check_comparison(claim: dict, ctx: DataContext) -> ClaimResult:
    """Schema: {claim_type, left, operator, right}, where left/right are
    each either {country, date, source_column} or {"literal": number}.
    operator in {gt, gte, lt, lte, eq}."""
    left_ref = claim.get("left")
    right_ref = claim.get("right")
    operator = claim.get("operator")

    if operator not in ("gt", "gte", "lt", "lte", "eq"):
        return ClaimResult(ClaimStatus.MALFORMED, f"Unknown comparison operator {operator!r}.")

    left_val = _resolve_value(left_ref, ctx) if left_ref else None
    right_val = _resolve_value(right_ref, ctx) if right_ref else None

    if left_val is None or right_val is None:
        return ClaimResult(
            ClaimStatus.FAILED,
            f"Could not resolve one or both sides of the comparison "
            f"(left={left_ref}, right={right_ref}) against real data.",
        )

    ops = {
        "gt": left_val > right_val,
        "gte": left_val >= right_val,
        "lt": left_val < right_val,
        "lte": left_val <= right_val,
        "eq": left_val == right_val,
    }
    holds = ops[operator]

    if holds:
        return ClaimResult(
            ClaimStatus.VERIFIED,
            f"Comparison holds: {left_val} {operator} {right_val}.",
        )
    return ClaimResult(
        ClaimStatus.FAILED,
        f"Comparison does not hold: claimed {left_val} {operator} {right_val}, "
        f"but that relationship is false against real data.",
    )


def _check_temporal_ordering(claim: dict, ctx: DataContext) -> ClaimResult:
    """Schema: {claim_type, country, before, after}, where before/after are
    each {week_start_date, regime_label}. Verifies ONLY that (a) both
    states are real and correctly labeled, and (b) before's date genuinely
    precedes after's date. Explicitly does not, and structurally cannot,
    assert *why* the transition happened -- that would require a causal
    claim type, which does not exist in this schema on purpose."""
    country = claim.get("country")
    before = claim.get("before", {})
    after = claim.get("after", {})

    before_row = ctx.lookup_regime(country, before.get("week_start_date"))
    after_row = ctx.lookup_regime(country, after.get("week_start_date"))

    if before_row is None or after_row is None:
        return ClaimResult(
            ClaimStatus.FAILED,
            f"Could not find real regime rows for both the 'before' and "
            f"'after' states claimed for {country}.",
        )

    if before_row["regime_label"] != before.get("regime_label"):
        return ClaimResult(
            ClaimStatus.FAILED,
            f"Claimed 'before' state regime_label {before.get('regime_label')!r} "
            f"does not match the actual recorded value {before_row['regime_label']!r}.",
        )
    if after_row["regime_label"] != after.get("regime_label"):
        return ClaimResult(
            ClaimStatus.FAILED,
            f"Claimed 'after' state regime_label {after.get('regime_label')!r} "
            f"does not match the actual recorded value {after_row['regime_label']!r}.",
        )
    if before.get("week_start_date") >= after.get("week_start_date"):
        return ClaimResult(
            ClaimStatus.FAILED,
            f"'before' date {before.get('week_start_date')} does not actually "
            f"precede 'after' date {after.get('week_start_date')} -- not a "
            f"real temporal sequence.",
        )

    return ClaimResult(
        ClaimStatus.VERIFIED,
        f"{country} genuinely transitioned from {before_row['regime_label']} "
        f"(week {before['week_start_date']}) to {after_row['regime_label']} "
        f"(week {after['week_start_date']}). No causal mechanism is asserted "
        f"or checked -- sequence only.",
    )


def _check_magnitude_band(claim: dict, ctx: DataContext) -> ClaimResult:
    """Schema: {claim_type, country, date, claimed_band}. Checks the real
    composite_pressure_score against CLIO's own already-defined
    PRESSURE_LEVEL_BANDS -- the model is never allowed to invent its own
    notion of what counts as "elevated"."""
    country = claim.get("country")
    date = claim.get("date")
    claimed_band = claim.get("claimed_band")

    if claimed_band not in PRESSURE_LEVEL_BANDS:
        return ClaimResult(
            ClaimStatus.MALFORMED,
            f"claimed_band {claimed_band!r} is not one of CLIO's own defined "
            f"bands {list(PRESSURE_LEVEL_BANDS)}.",
        )

    row = ctx.lookup_daily(country, date)
    if row is None:
        return ClaimResult(ClaimStatus.FAILED, f"No daily pressure row found for {country}, {date}.")

    actual_score = row["composite_pressure_score"]
    actual_band = row.get("pressure_level")

    if actual_band == claimed_band:
        return ClaimResult(
            ClaimStatus.VERIFIED,
            f"{country} {date}: composite_pressure_score {actual_score} is "
            f"correctly banded as {claimed_band}.",
        )
    return ClaimResult(
        ClaimStatus.FAILED,
        f"Claimed band {claimed_band!r} for {country} {date}, but the real "
        f"score {actual_score} is actually banded {actual_band!r}.",
    )
