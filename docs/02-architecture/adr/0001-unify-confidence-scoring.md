# ADR-0001: Unify the two confidence-scoring schemes

Status: Proposed
Date: 2026-07-03

## Context

Two confidence-scoring implementations currently coexist in the codebase. The first is a governed scheme built on reference dimension tables (`dim_censorship_confidence`, `dim_measurement_quality`, `dim_blocking_signals`), which turns "what does HIGH confidence mean" into queryable, versioned data. The second is a set of hardcoded confidence literals inline in `int.ooni_experiment_results.sql`. A report citing "confidence: HIGH" may mean two different things depending on which code path produced it (Technical Debt Inventory item TD-05).

This matters more than an ordinary inconsistency because the product strategy already plans to sell confidence-qualified findings to journalists, NGOs, and legal teams. An unresolved ambiguity here is a claim made to a court or a newsroom, not just a code-quality issue.

## Decision

Not yet made — this ADR is Proposed, not Accepted, because the decision requires an engineering judgment call (which scheme to keep, and what the inline literals were actually trying to express that the dimension tables might not yet cover) that should be made deliberately rather than defaulted.

The recommended default, absent a reason to prefer the alternative: retain the governed dimension-table scheme as canonical, since it is already the more inspectable, versioned, and consistent-with-the-rest-of-the-codebase design (the same pattern OONI's staging layer and ACLED path A's confidence/risk split both use). Migrate `int.ooni_experiment_results.sql`'s inline literals to reference the dimension tables, preserving any distinction the inline literals currently make that the dimension tables do not yet capture — if such a distinction exists, it should become a new column or row in the governed scheme, not a reason to keep two schemes.

## Consequences

If accepted: every confidence value in the system traces to one governed, versioned source, closing Technical Debt Inventory item TD-05 and removing a real legal-exposure risk before any AI narrative layer is built on top of confidence figures. Any historical report already generated using the inline-literal path should be reviewed once the migration is complete, in case its confidence labels would change under the unified scheme.

If not accepted, or deferred: the ambiguity persists, and every additional feature built on top of either scheme (in particular, any AI-generated narrative describing a "confidence: HIGH" finding) inherits and amplifies it invisibly, since fluent prose does not surface which code path produced the number the way a visible SQL discrepancy does.
