"""
verify_report.py — LLM report-writer prototype (ADR-0010)

Ties claim_check.py, causal_language_check.py, and completeness_check.py
together into one final verification pass over a generated report. This
module is pure, offline-testable code -- it takes generated sentences as
plain data (whether they came from a live report_writer_openai.py call or
a synthetic fixture in a test), so the verification logic itself can be
fully proven correct without ever needing a live API call. This mirrors
exactly how ADR-0009 proved grounding_check.py worked before any live
extraction ran.

Four layers of defense, run in order, each independently disqualifying:

  1. claim_index validity -- every sentence must point at a real index
     into the claims list it was given. An out-of-range or missing index
     means the model asserted something with no traceable source at all --
     this is the strongest possible rejection, since there's nothing left
     to even re-check.
  2. claim re-verification -- even though deterministic_analysis.py's
     claims are already true by construction, re-check every one anyway
     (defense in depth: catches a bug in that module, or a claims list
     that was tampered with between computation and generation).
  3. causal/superlative language -- every sentence's prose is scanned
     independently of whether its claim is honest, since causal framing
     is a property of the SENTENCE, not the claim.
  4. completeness -- the assembled full report text is checked for
     required disclosures (synthetic-data caveats, low-confidence
     caveats, the not-predictive guardrail, the sequence-not-causation
     guardrail) given everything it cited.

A report is VERIFIED only if all four layers pass for every sentence and
the full assembled text. Anything else is REJECTED -- there is no partial-
trust tier for report-level publication, unlike claim_check.py's own
FUZZY-style middle tier at the individual-claim level.

Since 2026-08-02 (after a Fable advisory pass), layer 4 no longer depends
on the model having written its own disclosure prose. Required disclosures
are computed deterministically (completeness_check.required_disclosures())
and appended to the report as fixed, canonical text BEFORE the
completeness check runs -- see the narrative_text / appended_disclosures /
full_text split below. This closes a prominence gap the original design
had: a model-phrased caveat could previously be technically present but
buried or undermined in the same sentence as the claim it was supposed to
qualify ("although some inputs are synthetic, the trend is unmistakable").
A code-inserted disclosure cannot be diluted, because the model never
writes it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from causal_language_check import check_sentence_language
from claim_check import ClaimStatus, DataContext, check_claim
from completeness_check import check_report_completeness, report_passes_completeness, required_disclosures


@dataclass
class SentenceVerification:
    claim_index: int
    text: str
    claim_index_valid: bool
    claim_verified: bool
    language_clean: bool
    reasons: list[str] = field(default_factory=list)

    @property
    def passes(self) -> bool:
        return self.claim_index_valid and self.claim_verified and self.language_clean


@dataclass
class ReportVerification:
    verified: bool
    sentence_results: list[SentenceVerification]
    completeness_results: list
    narrative_text: str          # model-generated prose only, before disclosures
    appended_disclosures: list[str]  # canonical, code-inserted disclosure sentences
    full_text: str               # narrative_text + appended_disclosures -- "the report"
    rejection_reasons: list[str]


def verify_report(claims: list[dict], generated_sentences: list[dict], ctx: DataContext) -> ReportVerification:
    """
    claims: the deterministic_analysis.py output the model was given.
    generated_sentences: [{claim_index, text}, ...] -- the model's output
    (or a synthetic stand-in for testing), NOT yet trusted.
    """
    sentence_results: list[SentenceVerification] = []
    rejection_reasons: list[str] = []

    for s in generated_sentences:
        claim_index = s.get("claim_index")
        text = s.get("text", "")
        reasons = []

        claim_index_valid = isinstance(claim_index, int) and 0 <= claim_index < len(claims)
        if not claim_index_valid:
            reasons.append(f"claim_index {claim_index!r} does not point at a real claim (list has {len(claims)} entries).")

        claim_verified = False
        if claim_index_valid:
            result = check_claim(claims[claim_index], ctx)
            claim_verified = result.status == ClaimStatus.VERIFIED
            if not claim_verified:
                reasons.append(f"Attached claim did not re-verify: {result.reason}")

        lang_result = check_sentence_language(text)
        language_clean = lang_result.clean
        if not language_clean:
            reasons.append(f"Language check failed: {lang_result.reason} ({lang_result.flagged_phrases})")

        sv = SentenceVerification(
            claim_index=claim_index if isinstance(claim_index, int) else -1,
            text=text,
            claim_index_valid=claim_index_valid,
            claim_verified=claim_verified,
            language_clean=language_clean,
            reasons=reasons,
        )
        sentence_results.append(sv)
        if not sv.passes:
            rejection_reasons.append(f"Sentence {sv.text!r}: {'; '.join(reasons)}")

    narrative_text = " ".join(s["text"] for s in generated_sentences if isinstance(s.get("text"), str))

    # Only claims that were actually, validly cited by at least one
    # sentence feed the completeness check -- an unused claim in the input
    # list shouldn't trigger a disclosure requirement for content that was
    # never actually written about.
    cited_claim_indices = {s.claim_index for s in sentence_results if s.claim_index_valid}
    cited_claims = [claims[i] for i in sorted(cited_claim_indices)]

    # Compute and append required disclosures BEFORE checking completeness
    # -- this is what makes disclosure presence structural rather than
    # hoped-for. See module docstring's 2026-08-02 note.
    disclosures = required_disclosures(cited_claims, ctx)
    appended_disclosures = [text for _, text in disclosures]
    full_text = narrative_text + ((" " + " ".join(appended_disclosures)) if appended_disclosures else "")

    completeness_results = check_report_completeness(cited_claims, full_text, ctx)
    completeness_ok = report_passes_completeness(completeness_results)
    if not completeness_ok:
        for r in completeness_results:
            if r.triggered and not r.satisfied:
                # Should only be reachable if required_disclosures()'s trigger
                # logic and this rule's trigger logic have drifted apart --
                # a bug in the assembler, not a model omission (the model's
                # own prose can no longer cause this branch on its own).
                rejection_reasons.append(f"Completeness rule {r.rule_name!r} failed: {r.reason}")

    all_sentences_pass = all(s.passes for s in sentence_results) and len(sentence_results) > 0
    verified = all_sentences_pass and completeness_ok

    return ReportVerification(
        verified=verified,
        sentence_results=sentence_results,
        completeness_results=completeness_results,
        narrative_text=narrative_text,
        appended_disclosures=appended_disclosures,
        full_text=full_text,
        rejection_reasons=rejection_reasons,
    )
