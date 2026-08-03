"""
deterministic_analysis.py — LLM report-writer prototype (ADR-0010)

This is "the deterministic analysis of what CLIO already outputs" Sam
asked for, in code. It decides WHAT is notable in a window of CLIO's own
data and produces the exact, already-true-by-construction claim objects
that report_writer_openai.py is later allowed to narrate. The LLM never
sees raw mart rows and never invents a claim from scratch -- it only ever
receives a list of claims this module already computed and that
claim_check.py could, in principle, re-verify independently.

This is a stronger safety property than "generate freely, then check
after the fact": it moves grounding from *detecting* a bad claim to
*structurally preventing* one from ever reaching the generation step. The
post-hoc checks in claim_check.py / causal_language_check.py /
completeness_check.py remain valuable anyway, for two reasons: (1) they
catch a bug in THIS module itself (a pre-analysis mistake is still a
mistake), and (2) they catch the model ignoring its instructions and
asserting something in prose beyond the claims it was actually given --
see report_writer_openai.py's post-generation verification step, which
checks that every sentence's claim_index really does point at one of
this module's own pre-computed claims, not a new one.

Deliberately narrow scope for this first version, per ADR-0010's smallest-
honest-v1 recommendation: one report type (a weekly/window regime-and-
pressure summary), one country, working against the same fixture data
claim_check.py's tests already use.
"""

from __future__ import annotations

from fixtures.finance_bill_2024_fixture import (
    ACLED_PRESSURE_REGIMES,
    FACT_COUNTRY_PRESSURE_DAILY,
    count_weeks_at_or_above,
)

REGIME_SEVERITY_ORDER = ["STABLE", "MOBILISATION", "ESCALATION", "CONFLICT", "CRISIS"]


def _weeks_in_window(country: str, week_start: str, week_end: str) -> list[dict]:
    return sorted(
        (r for r in ACLED_PRESSURE_REGIMES if r["country"] == country and week_start <= r["week_start_date"] <= week_end),
        key=lambda r: r["week_start_date"],
    )


def _days_in_window(country: str, date_start: str, date_end: str) -> list[dict]:
    return sorted(
        (r for r in FACT_COUNTRY_PRESSURE_DAILY if r["country"] == country and date_start <= r["date"] <= date_end),
        key=lambda r: r["date"],
    )


def analyze_window(country: str, week_start: str, week_end: str) -> list[dict]:
    """The one function that decides what's worth reporting. Returns a
    list of claim dicts, each already matching claim_check.py's exact
    schema for its claim_type -- these are handed to the LLM as fixed
    facts to narrate, not raw data to interpret."""

    claims: list[dict] = []
    weeks = _weeks_in_window(country, week_start, week_end)

    # One CLASSIFICATION claim per week in the window -- the baseline
    # facts any summary needs, regardless of whether anything notable
    # happened.
    for week in weeks:
        claims.append({
            "claim_type": "CLASSIFICATION",
            "country": country,
            "week_start_date": week["week_start_date"],
            "source_column": "regime_label",
            "claimed_value": week["regime_label"],
        })

    # A TEMPORAL_ORDERING claim for every genuine regime transition in the
    # window -- consecutive weeks where the label actually changed. This
    # is a sequence fact, never a causal one; the schema has no causal
    # type to smuggle a "because" into.
    for prev_week, next_week in zip(weeks, weeks[1:]):
        if prev_week["regime_label"] != next_week["regime_label"]:
            claims.append({
                "claim_type": "TEMPORAL_ORDERING",
                "country": country,
                "before": {"week_start_date": prev_week["week_start_date"], "regime_label": prev_week["regime_label"]},
                "after": {"week_start_date": next_week["week_start_date"], "regime_label": next_week["regime_label"]},
            })

    # A summary COUNT claim: how many weeks in this window were CRISIS or
    # above -- the kind of headline number a report typically opens with.
    crisis_count = count_weeks_at_or_above(country, "CRISIS", week_start, week_end)
    claims.append({
        "claim_type": "COUNT",
        "country": country,
        "regime_order_min": "CRISIS",
        "week_start": week_start,
        "week_end": week_end,
        "claimed_count": crisis_count,
    })

    # A MAGNITUDE_BAND claim for every day whose real pressure_level is
    # SEVERE -- the daily peaks worth naming specifically, not every day
    # in the window (a report narrating every single day would bury the
    # notable ones; deciding what counts as "notable" is this module's
    # job, not the LLM's).
    days = _days_in_window(country, week_start, week_end)
    for day in days:
        if day["pressure_level"] == "SEVERE":
            claims.append({
                "claim_type": "MAGNITUDE_BAND",
                "country": country,
                "date": day["date"],
                "claimed_band": day["pressure_level"],
            })

    return claims


def summarize_window_for_prompt(country: str, week_start: str, week_end: str, claims: list[dict]) -> str:
    """A short, human-readable framing of the window for the LLM's user
    message -- NOT a source of new facts, just orientation. The LLM must
    still only assert what's in `claims`; this text exists so the model
    understands what it's looking at, the same way a caption doesn't
    license new claims about a photo."""
    return (
        f"Window: {country}, {week_start} through {week_end}. "
        f"{len(claims)} pre-verified claim(s) about this window follow. "
        f"Write a short narrative report describing exactly these claims, "
        f"one or more sentences per claim, and nothing beyond them."
    )
