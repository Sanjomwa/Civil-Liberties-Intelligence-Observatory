"""
tests/test_deterministic_analysis.py — LLM report-writer prototype (ADR-0010)

The key property to prove here: every claim deterministic_analysis.py
produces must independently pass claim_check.py -- since these claims are
computed directly from the same fixture data claim_check.py checks against,
a bug in the pre-analysis step would be self-contradictory (it would
produce a claim that fails its own re-verification). This test proves that
never happens for the Finance Bill 2024 window, which is the strongest
kind of test for this module: not "does it look right," but "does its own
output survive the independent checker."
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from claim_check import ClaimStatus, DataContext, check_claim  # noqa: E402
from deterministic_analysis import analyze_window  # noqa: E402
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


def test_every_generated_claim_independently_verifies():
    claims = analyze_window("Kenya", "2024-05-04", "2024-07-20")
    assert len(claims) > 0, "Expected at least one claim for a real, populated window."
    for claim in claims:
        result = check_claim(claim, CTX)
        assert result.status == ClaimStatus.VERIFIED, (
            f"Pre-analysis produced a claim that fails its own re-verification "
            f"-- this should be structurally impossible: {claim} -> {result.reason}"
        )


def test_classification_claims_cover_every_week_in_window():
    claims = analyze_window("Kenya", "2024-05-04", "2024-07-20")
    classification_claims = [c for c in claims if c["claim_type"] == "CLASSIFICATION"]
    # 12 weeks in the fixture fall inside this window.
    assert len(classification_claims) == 12


def test_detects_the_two_real_transitions_in_window():
    claims = analyze_window("Kenya", "2024-05-04", "2024-07-20")
    transitions = [c for c in claims if c["claim_type"] == "TEMPORAL_ORDERING"]
    labels = [(t["before"]["regime_label"], t["after"]["regime_label"]) for t in transitions]
    # Real fixture transitions: STABLE->MOBILISATION (05-04->05-11),
    # MOBILISATION->ESCALATION (06-08->06-15), ESCALATION->CRISIS
    # (06-15->06-22), CRISIS->STABLE (07-06->07-13).
    assert ("STABLE", "MOBILISATION") in labels
    assert ("MOBILISATION", "ESCALATION") in labels
    assert ("ESCALATION", "CRISIS") in labels
    assert ("CRISIS", "STABLE") in labels
    assert len(transitions) == 4


def test_count_claim_matches_real_crisis_week_count():
    claims = analyze_window("Kenya", "2024-05-04", "2024-07-20")
    count_claims = [c for c in claims if c["claim_type"] == "COUNT"]
    assert len(count_claims) == 1
    assert count_claims[0]["claimed_count"] == 3  # 06-22, 06-29, 07-06


def test_magnitude_band_claims_only_for_severe_days():
    claims = analyze_window("Kenya", "2024-06-20", "2024-06-28")
    magnitude_claims = [c for c in claims if c["claim_type"] == "MAGNITUDE_BAND"]
    severe_dates = {c["date"] for c in magnitude_claims}
    # Real fixture SEVERE days in this range: 06-25, 06-26.
    assert severe_dates == {"2024-06-25", "2024-06-26"}


def test_empty_window_produces_no_weekly_claims():
    claims = analyze_window("Kenya", "2030-01-01", "2030-01-07")
    classification_claims = [c for c in claims if c["claim_type"] == "CLASSIFICATION"]
    assert classification_claims == []


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
