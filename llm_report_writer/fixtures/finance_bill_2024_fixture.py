"""
fixtures/finance_bill_2024_fixture.py — LLM report-writer prototype

A small, realistic MOCK of CLIO's real mart schema, for the Finance Bill
2024 window, used to test claim_check.py and completeness_check.py
offline, with no BigQuery access required. Values here are reconstructed
from this project's own documented history (decision-log.md, ADR-0002) —
they represent the *shape* and *approximate real pattern* of CLIO's actual
materialized data, not a live query result. When this design moves to a
live build, `lookup()` below is replaced by a real BigQuery query against
the same tables; the claim-checking logic itself does not change.

Two tables mocked, matching real CLIO mart names:
  - intelligence.acled_pressure_regimes (weekly, Path A regime classifier)
  - marts.fact_country_pressure_daily (daily, composite score + regime passthrough)
"""

from __future__ import annotations

# --- intelligence.acled_pressure_regimes ---
# One row per country per week. regime_label in
# {STABLE, ESCALATION, CONFLICT, CRISIS, MOBILISATION}, per this project's
# own documented vocabulary (ADR-0002).
ACLED_PRESSURE_REGIMES = [
    {"country": "Kenya", "week_start_date": "2024-05-04", "regime_label": "STABLE", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-05-11", "regime_label": "MOBILISATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-05-18", "regime_label": "MOBILISATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-05-25", "regime_label": "MOBILISATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-06-01", "regime_label": "MOBILISATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-06-08", "regime_label": "MOBILISATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-06-15", "regime_label": "ESCALATION", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-06-22", "regime_label": "CRISIS", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-06-29", "regime_label": "CRISIS", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-07-06", "regime_label": "CRISIS", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-07-13", "regime_label": "STABLE", "classification_confidence": "HIGH"},
    {"country": "Kenya", "week_start_date": "2024-07-20", "regime_label": "STABLE", "classification_confidence": "HIGH"},
]

# --- marts.fact_country_pressure_daily ---
# One row per country per day. composite_pressure_score is the Option-B
# reweighted value (conflict 0.75 / platform 0.25, per this project's own
# 2026-07-05 decision). pressure_level bands per this project's own
# (not-yet-re-derived, per TD-44) thresholds: LOW <3, MODERATE 3-5,
# ELEVATED 5-7, SEVERE >=7. legal_pressure_is_synthetic is TRUE for every
# row today (Lumen is fully synthetic pending a real source, per ADR-0004/TD-01).
FACT_COUNTRY_PRESSURE_DAILY = [
    {"country": "Kenya", "date": "2024-06-20", "composite_pressure_score": 4.90, "pressure_level": "MODERATE", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-21", "composite_pressure_score": 5.40, "pressure_level": "ELEVATED", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-24", "composite_pressure_score": 6.10, "pressure_level": "ELEVATED", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-25", "composite_pressure_score": 7.80, "pressure_level": "SEVERE", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-26", "composite_pressure_score": 7.20, "pressure_level": "SEVERE", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-27", "composite_pressure_score": 6.50, "pressure_level": "ELEVATED", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-06-28", "composite_pressure_score": 6.00, "pressure_level": "ELEVATED", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-07-10", "composite_pressure_score": 3.10, "pressure_level": "MODERATE", "legal_pressure_is_synthetic": True},
    {"country": "Kenya", "date": "2024-07-14", "composite_pressure_score": 2.20, "pressure_level": "LOW", "legal_pressure_is_synthetic": True},
]


def lookup_regime(country: str, week_start_date: str) -> dict | None:
    for row in ACLED_PRESSURE_REGIMES:
        if row["country"] == country and row["week_start_date"] == week_start_date:
            return row
    return None


def lookup_daily(country: str, date: str) -> dict | None:
    for row in FACT_COUNTRY_PRESSURE_DAILY:
        if row["country"] == country and row["date"] == date:
            return row
    return None


def count_weeks_at_or_above(country: str, regime_order_min: str, week_start: str, week_end: str) -> int:
    """Mocks the SQL a COUNT claim would re-execute: how many weeks in
    [week_start, week_end] had a regime_label at or above a given severity
    rank. Severity order matches this project's own documented vocabulary."""
    order = ["STABLE", "MOBILISATION", "ESCALATION", "CONFLICT", "CRISIS"]
    min_rank = order.index(regime_order_min)
    return sum(
        1
        for row in ACLED_PRESSURE_REGIMES
        if row["country"] == country
        and week_start <= row["week_start_date"] <= week_end
        and order.index(row["regime_label"]) >= min_rank
    )
