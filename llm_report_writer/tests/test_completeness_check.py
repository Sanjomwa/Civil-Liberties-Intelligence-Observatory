"""
tests/test_completeness_check.py — LLM report-writer prototype (ADR-0010)

Proves the completeness-contract checker catches OMISSION, not just
fabrication -- a report can pass every claim_check.py check (everything
it says is true) and still fail here (it left out something required).
This is the "more novel" mechanism the Opus advisory flagged.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from completeness_check import (  # noqa: E402
    CANONICAL_DISCLOSURES,
    check_low_confidence_disclosure,
    check_not_predictive_disclosure,
    check_report_completeness,
    check_sequence_disclosure,
    check_synthetic_disclosure,
    report_passes_completeness,
    required_disclosures,
)
from claim_check import DataContext  # noqa: E402
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

MAGNITUDE_CLAIM = {
    "claim_type": "MAGNITUDE_BAND",
    "country": "Kenya",
    "date": "2024-06-25",
    "claimed_band": "SEVERE",
}

HIGH_CONF_CLASSIFICATION_CLAIM = {
    "claim_type": "CLASSIFICATION",
    "country": "Kenya",
    "week_start_date": "2024-06-22",
    "source_column": "regime_label",
    "claimed_value": "CRISIS",
}

TRANSITION_CLAIM = {
    "claim_type": "TEMPORAL_ORDERING",
    "country": "Kenya",
    "before": {"week_start_date": "2024-06-15", "regime_label": "ESCALATION"},
    "after": {"week_start_date": "2024-06-22", "regime_label": "CRISIS"},
}


# --- synthetic disclosure ---

def test_synthetic_rule_not_triggered_by_classification_only():
    result = check_synthetic_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], "Some report text.", CTX)
    assert result.triggered is False


def test_synthetic_rule_triggered_and_missing():
    report_text = "On June 25, 2024, Kenya's pressure score reached SEVERE."
    result = check_synthetic_disclosure([MAGNITUDE_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is False, "Report cites synthetic-flagged data but never says so -- must fail."


def test_synthetic_rule_triggered_and_satisfied():
    report_text = (
        "On June 25, 2024, Kenya's pressure score reached SEVERE. Note: the "
        "legal/platform-pressure component of this score remains synthetic "
        "pending a production-quality source."
    )
    result = check_synthetic_disclosure([MAGNITUDE_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is True, result.reason


# --- low confidence disclosure ---

def test_low_confidence_rule_not_triggered_when_high():
    # Fixture's 2024-06-22 row has classification_confidence=HIGH
    result = check_low_confidence_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], "text", CTX)
    assert result.triggered is False


def test_low_confidence_rule_triggered_and_missing():
    # Synthetic a claim referencing a week whose confidence would need to
    # be non-HIGH to trigger -- since the fixture only has HIGH rows, patch
    # a local low-confidence row into a throwaway context instead of
    # editing the shared fixture (keeps this test self-contained).
    def lookup_regime_low_conf(country, week):
        row = lookup_regime(country, week)
        if row:
            row = dict(row)
            row["classification_confidence"] = "INSUFFICIENT_DATA"
        return row

    local_ctx = DataContext(
        lookup_regime=lookup_regime_low_conf,
        lookup_daily=lookup_daily,
        count_weeks_at_or_above=count_weeks_at_or_above,
    )
    result = check_low_confidence_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], "Kenya was in CRISIS.", local_ctx)
    assert result.triggered is True
    assert result.satisfied is False, "Low-confidence finding presented as settled fact -- must fail."


def test_low_confidence_rule_triggered_and_satisfied():
    def lookup_regime_low_conf(country, week):
        row = lookup_regime(country, week)
        if row:
            row = dict(row)
            row["classification_confidence"] = "INSUFFICIENT_DATA"
        return row

    local_ctx = DataContext(
        lookup_regime=lookup_regime_low_conf,
        lookup_daily=lookup_daily,
        count_weeks_at_or_above=count_weeks_at_or_above,
    )
    report_text = "Kenya was in CRISIS, though this classification carries lower confidence than usual."
    result = check_low_confidence_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], report_text, local_ctx)
    assert result.triggered is True
    assert result.satisfied is True, result.reason


# --- not-predictive disclosure ---

def test_not_predictive_rule_not_triggered_for_stable():
    stable_claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2024-07-13",
        "source_column": "regime_label",
        "claimed_value": "STABLE",
    }
    result = check_not_predictive_disclosure([stable_claim], "Kenya returned to STABLE.", CTX)
    assert result.triggered is False


def test_not_predictive_rule_triggered_and_missing():
    result = check_not_predictive_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], "Kenya was in CRISIS this week.", CTX)
    assert result.triggered is True
    assert result.satisfied is False, "CRISIS-level finding with no not-predictive guardrail -- must fail."


def test_not_predictive_rule_triggered_and_satisfied():
    report_text = (
        "Kenya was in CRISIS this week. This finding is retrospective, "
        "descriptive evidence fusion -- it is not predictive of future events."
    )
    result = check_not_predictive_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is True, result.reason


# --- sequence-not-causation disclosure (added 2026-08-02, Fable pass) ---

def test_sequence_rule_not_triggered_without_temporal_ordering_claim():
    result = check_sequence_disclosure([HIGH_CONF_CLASSIFICATION_CLAIM], "Some report text.", CTX)
    assert result.triggered is False


def test_sequence_rule_triggered_and_missing():
    report_text = "The classification moved from ESCALATION to CRISIS."
    result = check_sequence_disclosure([TRANSITION_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is False, "TEMPORAL_ORDERING claim cited with no sequence-not-causation disclosure -- must fail."


def test_sequence_rule_triggered_and_satisfied():
    report_text = (
        "The classification moved from ESCALATION to CRISIS. This is reported "
        "in chronological sequence only; no causal relationship is asserted."
    )
    result = check_sequence_disclosure([TRANSITION_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is True, result.reason


def test_two_adjacent_true_claims_with_no_connective_word_still_trigger_rule():
    """The exact adjacency-implication scenario Fable's pass named: two
    individually true, individually verified claims placed next to each
    other with zero causal connective words for causal_language_check.py
    to catch. This rule must still fire on claim composition alone,
    independent of any specific phrasing."""
    report_text = "Protests reached SEVERE. The classification moved to CRISIS the same week."
    result = check_sequence_disclosure([TRANSITION_CLAIM], report_text, CTX)
    assert result.triggered is True
    assert result.satisfied is False


# --- required_disclosures() (code-inserted disclosure assembly) ---

def test_required_disclosures_empty_when_nothing_triggers():
    stable_claim = {
        "claim_type": "CLASSIFICATION",
        "country": "Kenya",
        "week_start_date": "2024-07-13",
        "source_column": "regime_label",
        "claimed_value": "STABLE",
    }
    result = required_disclosures([stable_claim], CTX)
    assert result == []


def test_required_disclosures_returns_canonical_text_for_each_triggered_rule():
    claims = [MAGNITUDE_CLAIM, HIGH_CONF_CLASSIFICATION_CLAIM, TRANSITION_CLAIM]
    result = required_disclosures(claims, CTX)
    rule_names = {name for name, _ in result}
    assert rule_names == {"synthetic_data_disclosure", "not_predictive_disclosure", "sequence_disclosure"}
    for name, text in result:
        assert text == CANONICAL_DISCLOSURES[name]


def test_required_disclosures_assembled_text_always_passes_completeness():
    """Proves the assembler and the checker agree: appending exactly what
    required_disclosures() returns to an otherwise-bare report must always
    satisfy check_report_completeness(), for any combination of triggered
    rules -- this is the guarantee verify_report.py relies on."""
    claims = [MAGNITUDE_CLAIM, HIGH_CONF_CLASSIFICATION_CLAIM, TRANSITION_CLAIM]
    bare_report_text = "Kenya's pressure score was SEVERE and the regime moved to CRISIS."
    disclosures = required_disclosures(claims, CTX)
    full_text = bare_report_text + " " + " ".join(text for _, text in disclosures)
    results = check_report_completeness(claims, full_text, CTX)
    assert report_passes_completeness(results) is True, [r.reason for r in results if r.triggered and not r.satisfied]


# --- full-report integration ---

def test_full_report_fails_when_any_triggered_rule_unsatisfied():
    claims = [MAGNITUDE_CLAIM, HIGH_CONF_CLASSIFICATION_CLAIM]
    report_text = "Kenya's pressure score was SEVERE and the regime was CRISIS."  # no caveats at all
    results = check_report_completeness(claims, report_text, CTX)
    assert report_passes_completeness(results) is False


def test_full_report_passes_when_all_triggered_rules_satisfied():
    claims = [MAGNITUDE_CLAIM, HIGH_CONF_CLASSIFICATION_CLAIM]
    report_text = (
        "Kenya's pressure score was SEVERE on June 25, 2024, though its "
        "legal/platform-pressure component remains synthetic pending a "
        "production-quality source. The regime was classified CRISIS for "
        "the week of June 22 -- a retrospective, descriptive finding, not "
        "a prediction of what comes next."
    )
    results = check_report_completeness(claims, report_text, CTX)
    assert report_passes_completeness(results) is True, [r.reason for r in results if r.triggered and not r.satisfied]


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
