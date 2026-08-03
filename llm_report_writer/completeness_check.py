"""
completeness_check.py — LLM report-writer prototype (ADR-0010)

Per the Opus advisory that shaped ADR-0010, this is the more genuinely
novel half of the report-writer's verification design: claim_check.py
verifies that what a report SAYS is true. Nothing checks whether
something REQUIRED was silently left OUT. For civil-liberties reporting,
a dropped caveat -- a synthetic-data flag, a low-confidence classification,
CLIO's own standing "this is not predictive" guardrail -- is arguably the
higher-stakes failure mode, and it is exactly the kind of omission a
grounding checker built only to verify present claims will never catch,
by construction: an omitted sentence has no claim attached to fail.

Design: a completeness RULE has a trigger (does the set of claims a report
actually cites require a specific disclosure?) and a check (is that
disclosure actually present in the report's prose?). Rules are evaluated
against the full report -- the list of claims plus the full generated
text -- not sentence-by-sentence, since a disclosure sentence and the
claim that triggers its requirement are not necessarily adjacent.

Four rules in this version, deliberately not more (per this project's own
standing practice against introducing complexity before a concrete case
justifies it) -- a fourth was added 2026-08-02, after a Fable advisory pass
flagged a gap the first three didn't cover:

  1. Synthetic-data disclosure -- any cited fact_country_pressure_daily
     row with legal_pressure_is_synthetic=True requires the report to
     disclose that its legal/platform-pressure component is synthetic.
  2. Low-confidence disclosure -- any cited acled_pressure_regimes row
     with classification_confidence != "HIGH" requires the report to
     disclose the reduced confidence, not present it as settled fact.
  3. Not-predictive disclosure -- any report describing a CRISIS-or-above
     regime classification requires CLIO's own standing methodology
     guardrail (this is retrospective evidence fusion, not prediction --
     see TD-66) to appear somewhere in the report.
  4. Sequence-not-causation disclosure -- any cited TEMPORAL_ORDERING claim
     requires the report to explicitly disclose that the described
     transition is a chronological sequence, not an asserted cause. This
     rule exists because a TEMPORAL_ORDERING claim placed next to another
     claim in a narrative reads as implying causation through adjacency
     alone ("Protests reached SEVERE. The classification moved to CRISIS
     the same week." implies a causal link with zero causal connectives
     for causal_language_check.py's lexical scan to catch) -- narrative
     ordering itself is a causation-implying device that no per-sentence
     lexical check can see, since the implication lives between sentences,
     not inside one.

Disclosure presence is checked by substring/keyword matching against a set
of acceptable phrasings, not by semantic understanding -- same tradeoff
causal_language_check.py makes, for the same reason.

Since 2026-08-02, disclosure presence is no longer left to the model's own
phrasing at all: required_disclosures() below determines, from the exact
same trigger logic these rules already implement, which canonical
disclosure sentences a report structurally requires, and verify_report.py
appends them verbatim, in code, before this module's checks ever run. This
closes a disclosure-PROMINENCE gap the original design had: a model could
previously satisfy a rule with a real but buried or undermined caveat
("although some inputs are synthetic, the trend is unmistakable" contains
the word "synthetic" and would have passed). Code-inserted, fixed-text
disclosures cannot be buried or diluted, because the model never writes
them. check_report_completeness() still runs against the final,
disclosure-augmented text -- not as the primary guarantee any more, but as
a defense-in-depth confirmation that the assembler's trigger logic and
these rules' trigger logic haven't drifted apart from each other.
"""

from __future__ import annotations

from dataclasses import dataclass

SYNTHETIC_DISCLOSURE_PHRASES = ["synthetic", "not yet a production-quality source", "placeholder legal-pressure"]
LOW_CONFIDENCE_DISCLOSURE_PHRASES = ["lower confidence", "reduced confidence", "insufficient_data", "insufficient data", "medium confidence", "low confidence"]
NOT_PREDICTIVE_DISCLOSURE_PHRASES = ["not predictive", "not a prediction", "retrospective", "does not forecast", "not a leading indicator"]
SEQUENCE_DISCLOSURE_PHRASES = ["sequence only", "not causation", "no causal", "not asserted as causal", "chronological order, not"]

# Canonical, fixed-text disclosures -- exactly what verify_report.py appends
# to a report's narrative text for every rule that triggers. Each one is
# written to deliberately contain at least one of its own rule's accepted
# phrases above, so a correctly-assembled report always re-passes
# check_report_completeness (see module docstring). These are the ONLY
# disclosure text this design trusts -- never the model's own phrasing.
CANONICAL_DISCLOSURES = {
    "synthetic_data_disclosure": (
        "Note: the legal/platform-pressure figures cited above are currently "
        "synthetic placeholder legal-pressure data, not yet a "
        "production-quality source."
    ),
    "low_confidence_disclosure": (
        "Note: at least one classification cited above carries reduced "
        "confidence and should not be read as a high-certainty, settled finding."
    ),
    "not_predictive_disclosure": (
        "Note: CLIO's regime classifications are retrospective evidence "
        "fusion; they are not predictive and do not forecast future events."
    ),
    "sequence_disclosure": (
        "Note: transitions described above are reported in chronological "
        "sequence only; no causal relationship between events is asserted "
        "or verified."
    ),
}


@dataclass
class CompletenessResult:
    rule_name: str
    triggered: bool
    satisfied: bool  # only meaningful if triggered=True
    reason: str


def _any_phrase_present(report_text: str, phrases: list[str]) -> bool:
    lowered = report_text.lower()
    return any(p in lowered for p in phrases)


def check_synthetic_disclosure(claims: list[dict], report_text: str, ctx) -> CompletenessResult:
    # Bug-hunt pass, 2026-08-03: this used to also list "COUNT" here, but a
    # COUNT claim's schema (claim_type, country, regime_order_min,
    # week_start, week_end, claimed_count -- see claim_check.py) has neither
    # a top-level "date" nor a "left" ref for the fallback below to find, so
    # this branch could never actually trigger for a COUNT claim -- COUNT
    # claims summarize intelligence.acled_pressure_regimes only, which has
    # no synthetic-data column at all. Not a functional bug (no COUNT claim
    # was ever wrongly accepted or rejected because of this), but leaving a
    # claim_type listed as triggerable when it structurally never can be is
    # misleading to a future reader -- removed for clarity, behavior
    # unchanged.
    triggered = False
    for claim in claims:
        if claim.get("claim_type") in ("MAGNITUDE_BAND", "COMPARISON"):
            country = claim.get("country")
            date = claim.get("date") or (claim.get("left") or {}).get("date")
            if country and date:
                row = ctx.lookup_daily(country, date)
                if row and row.get("legal_pressure_is_synthetic"):
                    triggered = True
                    break

    if not triggered:
        return CompletenessResult(
            "synthetic_data_disclosure", False, True,
            "No claim cited synthetic-flagged data -- rule does not apply to this report.",
        )

    satisfied = _any_phrase_present(report_text, SYNTHETIC_DISCLOSURE_PHRASES)
    return CompletenessResult(
        "synthetic_data_disclosure",
        True,
        satisfied,
        "Report cites data with legal_pressure_is_synthetic=True and "
        + ("does disclose this." if satisfied else "does NOT disclose this -- a required caveat was silently omitted."),
    )


def check_low_confidence_disclosure(claims: list[dict], report_text: str, ctx) -> CompletenessResult:
    triggered = False
    triggering_confidence = None
    for claim in claims:
        if claim.get("claim_type") in ("CLASSIFICATION", "TEMPORAL_ORDERING"):
            country = claim.get("country")
            week = claim.get("week_start_date") or (claim.get("before") or {}).get("week_start_date")
            if country and week:
                row = ctx.lookup_regime(country, week)
                if row and row.get("classification_confidence") != "HIGH":
                    triggered = True
                    triggering_confidence = row.get("classification_confidence")
                    break
            # TEMPORAL_ORDERING claims can also trigger via the 'after' state
            after_week = (claim.get("after") or {}).get("week_start_date")
            if country and after_week:
                row = ctx.lookup_regime(country, after_week)
                if row and row.get("classification_confidence") != "HIGH":
                    triggered = True
                    triggering_confidence = row.get("classification_confidence")
                    break

    if not triggered:
        return CompletenessResult(
            "low_confidence_disclosure", False, True,
            "No claim cited a below-HIGH-confidence classification -- rule does not apply.",
        )

    satisfied = _any_phrase_present(report_text, LOW_CONFIDENCE_DISCLOSURE_PHRASES)
    return CompletenessResult(
        "low_confidence_disclosure",
        True,
        satisfied,
        f"Report cites a classification with confidence={triggering_confidence!r} and "
        + ("does disclose the reduced confidence." if satisfied else "does NOT disclose it -- presents a lower-confidence finding as settled fact."),
    )


def check_not_predictive_disclosure(claims: list[dict], report_text: str, ctx) -> CompletenessResult:
    crisis_or_above = {"CRISIS", "CONFLICT"}
    triggered = any(
        (claim.get("claim_type") in ("CLASSIFICATION", "TEMPORAL_ORDERING"))
        and (
            claim.get("claimed_value") in crisis_or_above
            or (claim.get("after") or {}).get("regime_label") in crisis_or_above
        )
        for claim in claims
    )

    if not triggered:
        return CompletenessResult(
            "not_predictive_disclosure", False, True,
            "Report does not describe a CRISIS-or-above classification -- rule does not apply.",
        )

    satisfied = _any_phrase_present(report_text, NOT_PREDICTIVE_DISCLOSURE_PHRASES)
    return CompletenessResult(
        "not_predictive_disclosure",
        True,
        satisfied,
        "Report describes a CRISIS-or-above finding and "
        + ("does carry the standing not-predictive disclosure." if satisfied else "does NOT carry it -- a CRISIS-level finding without this guardrail risks being read as a forecast, which CLIO's own methodology (TD-66) explicitly disclaims."),
    )


def check_sequence_disclosure(claims: list[dict], report_text: str, ctx) -> CompletenessResult:
    triggered = any(claim.get("claim_type") == "TEMPORAL_ORDERING" for claim in claims)

    if not triggered:
        return CompletenessResult(
            "sequence_disclosure", False, True,
            "No TEMPORAL_ORDERING claim cited -- rule does not apply to this report.",
        )

    satisfied = _any_phrase_present(report_text, SEQUENCE_DISCLOSURE_PHRASES)
    return CompletenessResult(
        "sequence_disclosure",
        True,
        satisfied,
        "Report cites a TEMPORAL_ORDERING (state-transition) claim and "
        + ("does disclose that this is sequence only, not causation."
           if satisfied else
           "does NOT disclose this -- a transition narrated next to other "
           "claims can imply causation through adjacency alone, with no "
           "causal connective word for causal_language_check.py to catch."),
    )


ALL_RULES = [
    check_synthetic_disclosure,
    check_low_confidence_disclosure,
    check_not_predictive_disclosure,
    check_sequence_disclosure,
]


def check_report_completeness(claims: list[dict], report_text: str, ctx) -> list[CompletenessResult]:
    """Runs every completeness rule against a full report. A report is
    only 'complete' if every triggered rule is also satisfied -- a rule
    that never triggered is not evidence of completeness, just evidence
    it wasn't relevant to this particular report."""
    return [rule(claims, report_text, ctx) for rule in ALL_RULES]


def report_passes_completeness(results: list[CompletenessResult]) -> bool:
    return all(r.satisfied for r in results if r.triggered)


def required_disclosures(claims: list[dict], ctx) -> list[tuple[str, str]]:
    """Determines which canonical disclosures a report structurally
    requires, reusing each rule's own trigger logic (called with
    report_text="" so only `triggered`, never `satisfied`, is meaningful --
    an empty string can never accidentally contain any disclosure phrase).
    Returns [(rule_name, canonical_text), ...] for every rule that
    triggered. verify_report.py calls this and appends the returned text to
    the assembled report BEFORE any completeness check runs, so presence is
    guaranteed by construction rather than hoped for from the model's own
    phrasing -- added 2026-08-02 after a Fable advisory pass named
    disclosure prominence (not just presence) as a real gap."""
    results = [rule(claims, "", ctx) for rule in ALL_RULES]
    return [(r.rule_name, CANONICAL_DISCLOSURES[r.rule_name]) for r in results if r.triggered]
