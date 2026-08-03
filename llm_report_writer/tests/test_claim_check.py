"""
tests/test_claim_check.py — LLM report-writer prototype (ADR-0010)

Proves claim_check.py works offline, no API key or network needed --
same discipline as ADR-0009's grounding_check.py tests. Fixtures are the
mock Finance Bill 2024 tables in fixtures/finance_bill_2024_fixture.py,
reconstructed from this project's own documented, already-verified real
history (ADR-0002's Finance Bill 2024 backfill findings).

Run with:
    python3 tests/test_claim_check.py
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from claim_check import ClaimStatus, DataContext, check_claim  # noqa: E402
from fixtures.finance_bill_2024_fixture import (  # noqa: E402
    count_weeks_at_or_above,
    lookup_daily,
    lookup_regime,
)

CTX = DataContext(
    lookup_regime=lookup_regime,
    lookup_daily=lookup_daily,
    count_weeks_at_or_above=count_weeks_at_or_above,
)


# --- CLASSIFICATION ---

def test_classification_verified():
    claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2024-06-22",
        "source_column": "regime_label",
        "claimed_value": "CRISIS",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_classification_failed_wrong_value():
    # The real week of 2024-06-22 is CRISIS, not STABLE -- a fabricated claim.
    claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2024-06-22",
        "source_column": "regime_label",
        "claimed_value": "STABLE",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_classification_failed_no_such_week():
    claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2099-01-01",
        "source_column": "regime_label",
        "claimed_value": "STABLE",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_classification_malformed_wrong_column():
    claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2024-06-22",
        "source_column": "some_column_not_supported",
        "claimed_value": "CRISIS",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.MALFORMED, result.reason


# --- COUNT ---

def test_count_verified():
    # Real fixture: 2024-06-22, 06-29, 07-06 are all CRISIS -> 3 weeks at
    # or above CRISIS in that 3-week window.
    claim = {
        "claim_type": "COUNT",
        "country": "Kenya",
        "regime_order_min": "CRISIS",
        "week_start": "2024-06-22",
        "week_end": "2024-07-06",
        "claimed_count": 3,
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_count_failed_wrong_number():
    claim = {
        "claim_type": "COUNT",
        "country": "Kenya",
        "regime_order_min": "CRISIS",
        "week_start": "2024-06-22",
        "week_end": "2024-07-06",
        "claimed_count": 5,  # real answer is 3
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_count_verified_mobilisation_threshold():
    # MOBILISATION-or-above across the whole window 2024-05-04..2024-07-20:
    # 05-11,05-18,05-25,06-01,06-08 (MOBILISATION) + 06-15 (ESCALATION) +
    # 06-22,06-29,07-06 (CRISIS) = 9 weeks.
    claim = {
        "claim_type": "COUNT",
        "country": "Kenya",
        "regime_order_min": "MOBILISATION",
        "week_start": "2024-05-04",
        "week_end": "2024-07-20",
        "claimed_count": 9,
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_count_malformed_bad_regime_name():
    claim = {
        "claim_type": "COUNT",
        "country": "Kenya",
        "regime_order_min": "APOCALYPSE",  # not a real CLIO regime label
        "week_start": "2024-06-22",
        "week_end": "2024-07-06",
        "claimed_count": 3,
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.MALFORMED, result.reason


# --- COMPARISON ---

def test_comparison_verified_gt():
    # Real: 2024-06-25 score 7.80 > 2024-06-20 score 4.90
    claim = {
        "claim_type": "COMPARISON",
        "left": {"country": "Kenya", "date": "2024-06-25", "source_column": "composite_pressure_score"},
        "operator": "gt",
        "right": {"country": "Kenya", "date": "2024-06-20", "source_column": "composite_pressure_score"},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_comparison_failed_reversed():
    claim = {
        "claim_type": "COMPARISON",
        "left": {"country": "Kenya", "date": "2024-06-20", "source_column": "composite_pressure_score"},
        "operator": "gt",
        "right": {"country": "Kenya", "date": "2024-06-25", "source_column": "composite_pressure_score"},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_comparison_verified_against_literal():
    claim = {
        "claim_type": "COMPARISON",
        "left": {"country": "Kenya", "date": "2024-06-25", "source_column": "composite_pressure_score"},
        "operator": "gte",
        "right": {"literal": 7.0},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


# --- TEMPORAL_ORDERING ---

def test_temporal_ordering_verified():
    claim = {
        "claim_type": "TEMPORAL_ORDERING",
        "country": "Kenya",
        "before": {"week_start_date": "2024-06-15", "regime_label": "ESCALATION"},
        "after": {"week_start_date": "2024-06-22", "regime_label": "CRISIS"},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_temporal_ordering_failed_wrong_before_label():
    claim = {
        "claim_type": "TEMPORAL_ORDERING",
        "country": "Kenya",
        "before": {"week_start_date": "2024-06-15", "regime_label": "STABLE"},  # actually ESCALATION
        "after": {"week_start_date": "2024-06-22", "regime_label": "CRISIS"},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_temporal_ordering_failed_dates_reversed():
    claim = {
        "claim_type": "TEMPORAL_ORDERING",
        "country": "Kenya",
        "before": {"week_start_date": "2024-06-22", "regime_label": "CRISIS"},
        "after": {"week_start_date": "2024-06-15", "regime_label": "ESCALATION"},
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


# --- MAGNITUDE_BAND ---

def test_magnitude_band_verified_severe():
    claim = {
        "claim_type": "MAGNITUDE_BAND",
        "country": "Kenya",
        "date": "2024-06-25",
        "claimed_band": "SEVERE",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.VERIFIED, result.reason


def test_magnitude_band_failed_wrong_band():
    claim = {
        "claim_type": "MAGNITUDE_BAND",
        "country": "Kenya",
        "date": "2024-06-25",  # real band is SEVERE
        "claimed_band": "LOW",
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.FAILED, result.reason


def test_magnitude_band_malformed_unknown_band():
    claim = {
        "claim_type": "MAGNITUDE_BAND",
        "country": "Kenya",
        "date": "2024-06-25",
        "claimed_band": "CATASTROPHIC",  # not a CLIO-defined band
    }
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.MALFORMED, result.reason


# --- dispatch / unknown type ---

def test_unknown_claim_type_is_malformed():
    claim = {"claim_type": "CAUSAL", "country": "Kenya"}  # deliberately not a real type
    result = check_claim(claim, CTX)
    assert result.status == ClaimStatus.MALFORMED, result.reason


if __name__ == "__main__":
    import inspect
    failures = 0
    tests = [(n, f) for n, f in list(globals().items()) if n.startswith("test_") and inspect.isfunction(f)]
    for name, fn in tests:
        try:
            fn()
            print(f"PASS  {name}")
        except AssertionError as e:
            failures += 1
            print(f"FAIL  {name}: {e}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    sys.exit(1 if failures else 0)
