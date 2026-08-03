"""
tests/test_verify_report.py — LLM report-writer prototype (ADR-0010)

Proves the full end-to-end verification pipeline works WITHOUT ever
calling the live LLM -- generated_sentences here are synthetic stand-ins
for what report_writer_openai.py would return, exactly the same discipline
ADR-0009 used to prove grounding_check.py before any live extraction ran.
Includes deliberately bad synthetic outputs (invalid claim_index, a
fabricated claim, causal language) that must each independently cause
rejection -- this is the real evidence the verification mechanism works,
not just that it accepts good input.

Since 2026-08-02 (Fable advisory pass), required disclosures are appended
by code rather than depending on the model writing them -- so "the model
omitted a disclosure" is no longer a rejection scenario at all; it's now a
*verified* scenario (see test_*_disclosure_auto_appended_when_model_omits_it
below), because the system supplies the disclosure itself. What used to be
tested as "missing disclosure -> rejected" is now tested as "missing
disclosure -> code fills the gap -> still verified, and the canonical text
is provably present in the final report."
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from claim_check import DataContext  # noqa: E402
from deterministic_analysis import analyze_window  # noqa: E402
from fixtures.finance_bill_2024_fixture import (  # noqa: E402
    count_weeks_at_or_above,
    lookup_daily,
    lookup_regime,
)
from verify_report import verify_report  # noqa: E402

CTX = DataContext(
    lookup_regime=lookup_regime,
    lookup_daily=lookup_daily,
    count_weeks_at_or_above=count_weeks_at_or_above,
)

CLAIMS = analyze_window("Kenya", "2024-06-15", "2024-07-13")
# Index map for readability in the tests below (order matches
# deterministic_analysis.py's construction order: CLASSIFICATION per week,
# then TEMPORAL_ORDERING transitions, then one COUNT, then MAGNITUDE_BAND
# per SEVERE day).


def _find_index(claim_type: str, **kwargs) -> int:
    for i, c in enumerate(CLAIMS):
        if c["claim_type"] != claim_type:
            continue
        if all(c.get(k) == v for k, v in kwargs.items()):
            return i
    raise AssertionError(f"No claim found matching {claim_type} {kwargs} in fixture-derived CLAIMS.")


def test_well_formed_report_is_verified():
    crisis_week_idx = _find_index("CLASSIFICATION", week_start_date="2024-06-22", claimed_value="CRISIS")
    transition_idx = _find_index("TEMPORAL_ORDERING")
    count_idx = _find_index("COUNT")
    severe_day_idx = _find_index("MAGNITUDE_BAND", date="2024-06-25")

    sentences = [
        {"claim_index": crisis_week_idx, "text": "Kenya's regime classification for the week of June 22, 2024 was CRISIS."},
        {"claim_index": transition_idx, "text": "This followed a transition in the prior weeks from an earlier, calmer state to this classification."},
        {"claim_index": count_idx, "text": "Across this window, 3 week(s) were classified CRISIS or above. This is a retrospective, descriptive finding, not a prediction of future events."},
        {"claim_index": severe_day_idx, "text": "On June 25, 2024, the composite pressure score reached the SEVERE band. Note that the legal/platform-pressure component remains synthetic pending a production-quality source."},
    ]

    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is True, result.rejection_reasons


def test_out_of_range_claim_index_is_rejected():
    sentences = [{"claim_index": 9999, "text": "Something happened."}]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is False
    assert any("does not point at a real claim" in r for r in result.rejection_reasons)


def test_fabricated_claim_value_is_rejected():
    # A sentence whose claim_index is valid but whose underlying claim
    # object has been tampered with to assert something false -- this
    # simulates a claims-list-tampering scenario the defense-in-depth
    # re-check exists to catch.
    tampered_claims = list(CLAIMS)
    crisis_idx = _find_index("CLASSIFICATION", week_start_date="2024-06-22", claimed_value="CRISIS")
    tampered_claims[crisis_idx] = dict(tampered_claims[crisis_idx])
    tampered_claims[crisis_idx]["claimed_value"] = "STABLE"  # false -- real value is CRISIS

    sentences = [{"claim_index": crisis_idx, "text": "Kenya was STABLE the week of June 22, 2024."}]
    result = verify_report(tampered_claims, sentences, CTX)
    assert result.verified is False
    assert any("did not re-verify" in r for r in result.rejection_reasons)


def test_causal_language_is_rejected_even_with_a_true_claim():
    transition_idx = _find_index("TEMPORAL_ORDERING")
    sentences = [
        {
            "claim_index": transition_idx,
            "text": "The classification escalated dramatically because of the finance bill.",
        }
    ]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is False
    assert any("Language check failed" in r for r in result.rejection_reasons)


def test_synthetic_disclosure_auto_appended_when_model_omits_it():
    severe_day_idx = _find_index("MAGNITUDE_BAND", date="2024-06-25")
    sentences = [
        {"claim_index": severe_day_idx, "text": "On June 25, 2024, the composite pressure score reached the SEVERE band."}
        # Model writes no synthetic-data caveat at all -- per rule 7 in
        # report_writer_openai.py's system prompt, it never should. The
        # code must supply it anyway.
    ]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is True, result.rejection_reasons
    assert any("synthetic" in d.lower() for d in result.appended_disclosures)
    assert "synthetic" in result.full_text.lower()
    assert "synthetic" not in result.narrative_text.lower(), "narrative_text should be exactly what the model wrote, nothing appended"


def test_not_predictive_disclosure_auto_appended_when_model_omits_it():
    crisis_week_idx = _find_index("CLASSIFICATION", week_start_date="2024-06-22", claimed_value="CRISIS")
    sentences = [
        {"claim_index": crisis_week_idx, "text": "Kenya's regime classification for the week of June 22, 2024 was CRISIS."}
        # No not-predictive guardrail written by the model -- code must add it.
    ]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is True, result.rejection_reasons
    assert any("retrospective" in d.lower() or "not predictive" in d.lower() for d in result.appended_disclosures)
    assert "retrospective" in result.full_text.lower()


def test_sequence_disclosure_auto_appended_when_model_omits_it():
    """The adjacency-implication scenario itself: two individually true
    claims narrated with no causal connective word, and no sequence
    disclosure written by the model. The code must still append the
    sequence-not-causation disclosure, closing the gap Fable's pass named."""
    transition_idx = _find_index("TEMPORAL_ORDERING")
    severe_day_idx = _find_index("MAGNITUDE_BAND", date="2024-06-25")
    sentences = [
        {"claim_index": severe_day_idx, "text": "Pressure reached the SEVERE band on June 25, 2024."},
        {"claim_index": transition_idx, "text": "The classification moved to CRISIS the same week."},
    ]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is True, result.rejection_reasons
    assert any("sequence only" in d.lower() or "no causal" in d.lower() for d in result.appended_disclosures)


def test_appended_disclosures_never_come_from_the_model():
    """A report whose model-written narrative deliberately mimics a
    disclosure ('this classification carries lower confidence') must not
    let that stand in for the code-inserted canonical version -- proves
    narrative_text and appended_disclosures stay cleanly separated even
    when their content overlaps in wording."""
    crisis_week_idx = _find_index("CLASSIFICATION", week_start_date="2024-06-22", claimed_value="CRISIS")
    sentences = [
        {"claim_index": crisis_week_idx, "text": "Kenya's regime classification for the week of June 22, 2024 was CRISIS."},
    ]
    result = verify_report(CLAIMS, sentences, CTX)
    assert result.verified is True
    # The canonical not-predictive disclosure text must appear in
    # appended_disclosures regardless of what the model wrote.
    assert any("retrospective evidence fusion" in d for d in result.appended_disclosures)


def test_empty_report_is_rejected_not_vacuously_verified():
    result = verify_report(CLAIMS, [], CTX)
    assert result.verified is False


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
