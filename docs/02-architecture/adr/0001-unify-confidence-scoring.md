# ADR-0001: Unify the two confidence-scoring schemes

Status: Accepted
Date: 2026-07-03 (proposed), 2026-07-05 (corrected diagnosis, accepted, implemented)

## Context

This ADR was originally opened on the belief that two confidence-scoring implementations coexisted: a governed scheme built on reference dimension tables (`dim_censorship_confidence`, `dim_measurement_quality`, `dim_blocking_signals`), and a set of hardcoded confidence literals inline in `int.ooni_experiment_results.sql`. The original recommended decision was to migrate the inline literals into the dimension-table scheme.

**That framing was wrong**, discovered the same way TD-02's "add a join key" framing was wrong: by reading the actual SQL bodies and their consumer chains directly, not by trusting the names of the tables involved.

What is actually true, confirmed 2026-07-05:

1. `int.ooni_experiment_results.sql` has 6 distinct raw `confidence_score` literals (0.90, 0.80, 0.75, 0.70, 0.45, 0.40), assigned per protocol × branch condition (DNS bogon/valid/failure, TCP reset/success/other, TLS handshake failure/success/other, HTTP 451/2xx-3xx/other). These are **continuous statistical inputs**, not categorical labels, and they flow unbucketed into `fact_network_blocking_daily`'s weighted average, then into `protocol_daily_signals`, `protocol_signal_regimes`, ASN `behavioral_priority_score`, and the pressure-correlation mart. Collapsing these into a 4-value categorical scale would silently change real numbers throughout the intelligence/reporting layers — this is not a safe dedup, and was never actually the source of the TD-05 ambiguity.
2. `dim_censorship_confidence` (4 rows: NONE/LOW/MEDIUM/HIGH → `probability_weight` 0.00/0.25/0.60/0.90) was, before this fix, dead code — referenced by nothing in the live pipeline. `dim_blocking_signals` is unrelated to OONI confidence entirely (a fixed severity/weight lookup used elsewhere).
3. The actual risk was three independent, hardcoded, **disagreeing** re-bucketing sites that turn `confidence_score` into HIGH/MEDIUM/LOW/NONE labels, none of which referenced `dim_censorship_confidence`:
   - `int.ooni_signals.sql` — dead code (nothing read its `blocking_confidence` output; only its unrelated `country` column was read by `dim_country.sql`). Thresholds: HIGH≥0.80, MEDIUM≥0.60.
   - `features.protocol_daily_signals.sql` — live, agreed with the dead file's thresholds.
   - `marts.fact_platform_blocking_summary` (declared name `marts.fact_protocol_blocking_summary`, see TD-21) — live, **disagreed**: HIGH≥0.90, MEDIUM≥0.70.

This is entirely separate from ACLED path A's `classification_confidence`/`methodology_risk_level` fields, which happen to share the word "confidence" but are a different subsystem (see the real-world ACLED-backfill anecdote recorded under TD-05 in the technical debt inventory — that investigation is not resolved by this ADR and should not be conflated with it).

The product-strategy stakes described in the original ADR still hold: CLIO plans to sell confidence-qualified findings to journalists, NGOs, and legal teams, so an unreconciled "what does HIGH mean" question is a claim made to a court or newsroom, not just a code-quality issue.

## Decision

**Option 1 (adopted): leave the 6 raw per-branch continuous literals in `int.ooni_experiment_results.sql` untouched.** Fix only the categorical re-bucketing layer, by making both live sites reference one governed source of thresholds instead of hardcoding their own.

Rejected: migrating the raw literals into `dim_censorship_confidence` (the original plan). That would have required either flattening 6 meaningfully-distinct continuous evidence-strength values down to 4 categorical weights (losing real signal — e.g. TCP reset at 0.80 and TLS handshake failure at 0.75 are different evidentiary strengths, not the same thing), or expanding the dimension table into something considerably more complex than 4 rows to preserve them — introducing exactly the kind of abstraction this project's engineering principles say not to add before at least two concrete cases justify it. There was only one real, already-colocated CASE block per protocol; it didn't need a governed table, it needed to be left alone.

Implementation, 2026-07-05:

1. Added a `min_score FLOAT64` column to `dim_censorship_confidence` (inclusive lower bound per tier; NULL for NONE, the fallback). Values: LOW=0.00, MEDIUM=0.60, HIGH=0.80.
2. **Canonicalized on HIGH≥0.80/MEDIUM≥0.60** (the `protocol_daily_signals.sql`/dead-`int.ooni_signals.sql` scheme), not the `fact_platform_blocking_summary` scheme (HIGH≥0.90/MEDIUM≥0.70). Basis: git history shows `fact_platform_blocking_summary.sql`'s thresholds date to the file's first commit (`32a9aaf`, 2026-04-12), an early, iteratively-patched marts asset (commit messages include "needs fixing", multiple ad hoc "Refactor..." passes). `protocol_daily_signals.sql`'s thresholds were set over a month later (`4a3f7c5`/`237fda5`, 2026-05-11/13), explicitly building the newer features layer "with clear separation of concerns and schema validators," with one commit message directly calling out a deliberate confidence-calculation fix. It was also already the majority position — 2 of 3 sites (including the dead file) already agreed on it. `fact_platform_blocking_summary` is the one that changed.
3. `features.protocol_daily_signals.sql` and `marts.fact_platform_blocking_summary` both now derive `confidence_level` via a `LEFT JOIN` to `dim_censorship_confidence` on `confidence_score >= min_score`, resolved with `QUALIFY ROW_NUMBER() OVER (PARTITION BY <row's natural unique key> ORDER BY ordinal_rank DESC) = 1` (a correlated-subquery form was tried first and rejected — BigQuery's validator rejects correlated subqueries against other tables; the JOIN+QUALIFY form is the de-correlated equivalent). Both assets' `depends:` lists now declare `marts.dim_censorship_confidence`.
4. `int.ooni_signals.sql`'s redundant `blocking_confidence` CASE block and column were deleted outright — clean surgical removal, confirmed safe by repo-wide grep showing its only consumer (`dim_country.sql`) reads solely the unrelated `country` column. The rest of the file, and the asset itself, is untouched.

Verification: `bruin validate` (56/56 clean) and real `bruin run` materialization of all four changed/dependent assets (`dim_censorship_confidence`, `int.ooni_signals`, `dim_country`, `features.protocol_daily_signals`, `marts.fact_protocol_blocking_summary`), followed by a live BigQuery query confirming both sites now assign identical `confidence_level` labels for identical `confidence_score` values (e.g. both report exactly 50,236 HIGH-confidence events). See TD-05 in the technical debt inventory for the full verification trail.

## Consequences

Every OONI confidence *category* now traces to one governed, versioned source (`dim_censorship_confidence.min_score`), closing this part of TD-05. The raw continuous evidence-strength literals remain intentionally un-unified, since collapsing them was never the right fix.

**No currently-materialized report actually changes as a result of this fix.** The disputed threshold band (`[0.60, 0.70)` and `[0.80, 0.90)`, where the old two schemes disagreed) turns out to contain zero real rows in the current Kenya OONI dataset — the TCP-reset (0.80) and TLS-handshake-failure (0.75) literals exist in the code but were never observed in the live data materialized today. The fix closes a **latent** correctness risk (the next TCP reset or TLS failure OONI actually observes would previously have been labeled differently depending on which of the two live assets produced the report), not a currently-visible data error.

A minor, separate, out-of-scope drift was surfaced and logged as TD-43, not fixed here: a doc comment in `int.acled_event_classification.sql` (line 267) references `int.ooni_signals.sql`'s HIGH/MEDIUM/LOW scheme by name for analogy; that scheme's implementation has now moved to `dim_censorship_confidence`, so the comment is stale (not incorrect about ACLED's own logic, just pointing at a description that no longer lives where it says).

If a future change alters `dim_censorship_confidence`'s thresholds, both `features.protocol_daily_signals` and `marts.fact_platform_blocking_summary` will move together automatically — this was the actual point of the fix.
