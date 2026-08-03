# LLM report-writer prototype (ADR-0010)

Status: **offline design complete and fully tested (73/73), live LLM call not yet run.** This supersedes OTF-04's original raw-article-extraction framing (`llm_extraction/`, ADR-0009) as CLIO's flagship AI-layer story. **As of 2026-08-02, `llm_extraction/`'s live-repo code has been deleted at Sam's direction** to clear the way for this design's live build — the decision record and reasoning (what was built, why it worked as a mechanism, why its coverage-gap premise didn't hold up) remain in ADR-0009 (including its Amendment section) and `decision-log.md`; only the code is gone. See ADR-0010 for the full pivot reasoning.

**2026-08-02 update, after a Fable advisory pass:** three changes landed the same day the pass came back. (1) A new completeness rule closes an implied-causation-by-adjacency gap Fable named — two individually true claims narrated next to each other can imply causation with zero causal connective words for `causal_language_check.py` to catch. (2) Required disclosures (synthetic-data, low-confidence, not-predictive, and the new sequence-not-causation rule) are now code-inserted, verbatim, canonical text — never model-phrased — closing a disclosure-prominence gap where a real caveat could previously be buried or diluted in the same sentence as the claim it qualified. (3) `template_writer.py` and `run_baseline_comparison.py` were added so the open question Fable raised — does an LLM actually beat a trivial rule-based narrator for this constrained a task — can be tested empirically instead of assumed. See `decision-log.md`'s 2026-08-02 entry for the full advisory and Sam's response.

## What this is

An automated "analyst" that writes short narrative reports directly from CLIO's own already-computed, verified pipeline data (regime classifications, composite pressure scores) — never from raw external text. Built after finding that raw-article extraction couldn't scale to the local/subnational sourcing a real coverage-gap test would need, and that Sam's original intent for the LLM layer was always this: save an analyst's time writing up what CLIO already knows, not discover new facts.

## The core design idea: compute first, narrate second

Unlike ADR-0009's extraction layer (generate freely, then check the output), this design **structurally prevents** a fabricated claim from ever reaching the model in the first place:

1. `deterministic_analysis.py` — pure code, no LLM — decides what's notable in a window of CLIO's real data and produces a list of already-true claim objects (a week's regime classification, a genuine transition between weeks, a summary count, a notable daily pressure spike).
2. `report_writer_openai.py` — the one component that calls an LLM — is given ONLY that claims list. Its job is narrow: write readable prose narrating each claim, tagging every sentence with which claim index it's describing. It cannot introduce a new claim; there's nothing for it to invent from.
3. `verify_report.py` — four independent layers of defense-in-depth, run even though the claims were already true by construction (catches a bug in step 1, a tampered list, or the model ignoring its instructions):
   - every sentence's claim_index must point at a real claim
   - that claim is independently re-verified against the real data (`claim_check.py`)
   - the sentence's own language is scanned for causal or unsupported-superlative framing (`causal_language_check.py`) — **there is no causal claim type in the schema at all**
   - the full assembled report is checked for required disclosures it must not have silently omitted (`completeness_check.py`) — synthetic-data caveats, low-confidence caveats, CLIO's own standing "this is not predictive" guardrail (TD-66), and (added 2026-08-02) a sequence-not-causation disclosure whenever a state-transition claim is cited

   **Since 2026-08-02, layer 4's disclosures are code-inserted, not model-written.** `completeness_check.required_disclosures()` computes, from each rule's own trigger condition, exactly which canonical disclosure sentences a report requires, and `verify_report.py` appends them verbatim before any completeness check runs. The model is explicitly instructed (system-prompt rule 7) never to write its own version of a disclosure. This makes disclosure *presence and prominence* structural rather than dependent on the model choosing to write one, and it closes the case Fable's advisory pass named: a real but buried caveat ("although some inputs are synthetic, the trend is unmistakable") used to technically satisfy the old keyword check while still misleading a reader in the same sentence. `ReportVerification` now exposes `narrative_text` (model output only), `appended_disclosures` (the code-inserted list), and `full_text` (both, concatenated — this is "the report").

   **The sequence-not-causation rule exists for a gap no per-sentence language scan can see.** `causal_language_check.py` catches causal *connective words* ("because", "triggered by"). It cannot catch two individually true, individually verified claims placed next to each other in a narrative — "Protests reached SEVERE. The classification moved to CRISIS the same week." implies a causal link through adjacency alone, with nothing for a lexical scanner to flag. Whenever a `TEMPORAL_ORDERING` claim is cited, the report now always carries an explicit "reported in chronological sequence only, no causal relationship asserted" disclosure — code-inserted, same mechanism as the other three.

A fifth, separate module, `style_lint.py`, is deliberately **not** part of this gate. It flags common AI-writing tics (filler openers, hype words, hedge-padding, corporate cliches) for a human to skim, but never blocks verification — style is a quality concern, not a safety one, and the two are kept structurally separate rather than conflated. The system prompt in `report_writer_openai.py` includes an explicit house-style section (plain sentences, no hype language, no vague hedging, specific numbers over vague summary) as the actual mechanism for improving output quality — `style_lint.py` exists to catch drift from that instruction, not to enforce it after the fact.

A report is only trusted if all four layers pass. There's no partial-trust tier for publication.

## Why the completeness checker matters as much as the claim checker

Per the Opus advisory that shaped ADR-0010: checking whether what's said is true catches fabrication. It does nothing about omission — a report that quietly drops a synthetic-data caveat or presents a low-confidence finding as settled fact is arguably more dangerous for civil-liberties reporting than a wrong number would be, and no claim-checker built only to verify present claims can ever catch a sentence that was never written. `completeness_check.py` is the mechanism built specifically to catch that.

## Is an LLM even needed here? The template baseline

Fable's advisory pass asked the obvious question this design hadn't yet answered: given how constrained `report_writer_openai.py`'s job already is (~5 fixed claim types, one claim per sentence, no invented facts, no causal language), could a trivial rule-based template narrator produce equivalent output with zero fabrication risk and none of the verification machinery? That's an empirical question CLIO didn't have evidence for either way.

`template_writer.py` answers the "does it verify" half for free: it renders every claim type with a fixed string template, takes the exact same claims list as the LLM path, and produces the exact same output shape, so it runs through the identical `verify_report.py` pipeline. It always passes verification by construction (its templates can't fabricate or use causal language). Run `python3 run_baseline_comparison.py` to see it — no API key needed for the template half; set `OPENAI_API_KEY` to also generate the LLM side and read both outputs side by side before writing anything in the concept note about why an LLM is used here.

What the template baseline does NOT answer: whether the LLM's prose reads better to an actual reader across varied windows, including boring ones. That's a live-call judgment call, still pending — see "What this is not yet" below.

## What's proven, and how

73/73 offline tests pass, with no API key or network call needed for any of them:

| File | Tests | What it proves |
|---|---|---|
| `tests/test_claim_check.py` | 18 | Each of the 5 claim types correctly verifies true claims and rejects false/malformed ones |
| `tests/test_causal_language_check.py` | 9 | Causal connectives and unsupported superlatives are caught, clean sentences pass |
| `tests/test_completeness_check.py` | 18 | Each of the 4 disclosure rules (including the 2026-08-02 sequence rule) triggers correctly, and `required_disclosures()` correctly assembles code-inserted, canonical disclosure text that always re-passes the check |
| `tests/test_deterministic_analysis.py` | 6 | Every claim the pre-analysis step produces independently re-verifies — proves step 1 can't produce a claim step 2 would reject |
| `tests/test_verify_report.py` | 9 | The full pipeline, with synthetic stand-ins for LLM output — including bad cases (out-of-range index, tampered claim, causal language) that must independently be rejected, and cases proving a model that omits a disclosure entirely still ends up with a verified, disclosure-complete report because the code supplies it |
| `tests/test_style_lint.py` | 7 | The non-blocking style lint correctly flags filler/hype/hedge/cliche phrasing and passes plain sentences clean |
| `tests/test_template_writer.py` | 6 | The template baseline renders every claim type, always passes full verification, and produces output shaped identically to the LLM path for a fair side-by-side comparison |

Fixture data (`fixtures/finance_bill_2024_fixture.py`) is a small mock of CLIO's real mart schema for the Finance Bill 2024 window, reconstructed from this project's own documented, already-verified history (ADR-0002's backfill findings) — not live-queried, but shaped exactly like the real tables so the live build only has to swap the lookup implementation, not the checking logic.

## How to run it

```bash
pip install -r requirements.txt

# Offline verification first (no key needed, proves the mechanism):
for f in tests/test_*.py; do python3 "$f"; done

# Then the live report generation (requires your own key):
export OPENAI_API_KEY=sk-...
python3 run_report.py
```

`run_report.py` runs the full pipeline against the Finance Bill 2024 window fixture, prints the generated report and its verification result, and writes `output_report.json`.

## Governance

Same rules ADR-0009 established, carried forward: every generated report is disclosed as `llm_derived: true`; every claim is independently re-verifiable against the exact data it cites; `prompt_version_hash` distinguishes output from different prompt versions; reports remain human-reviewed before publication (per ADR-0010's Consequences). This prototype only reads from CLIO's own already-computed data — it makes no external calls except to the LLM API itself, and writes no output back into any CLIO mart.

## What this is not yet

Not wired into the live Bruin repo (that's the next step, mirroring ADR-0009's build path: offline design and test here, advisory review, then a Claude Code relay prompt for the live build). Not run live even once — `run_report.py` and `run_baseline_comparison.py` are ready but need Sam's own `OPENAI_API_KEY`, same constraint as the extraction layer. Scoped to one report type and one window family, deliberately, per ADR-0010's smallest-honest-v1 recommendation — no multi-country, no interactive UI, no auto-publishing.

**Next concrete step, per the 2026-08-02 Fable advisory pass:** before writing the concept note, spend 1-2 days making live calls across 8-12 test windows (including deliberately boring, non-crisis ones, not just Finance Bill 2024) and record the honest numbers this design doesn't have yet — first-pass verification rate, retry count, and the template-vs-LLM readability comparison `run_baseline_comparison.py` now makes possible. "We designed a verification suite" is a plan; "N% of live generations pass all four gates unmodified across N windows" is evidence, and it's cheap enough to gather that there's no good reason to submit the concept note without it.
