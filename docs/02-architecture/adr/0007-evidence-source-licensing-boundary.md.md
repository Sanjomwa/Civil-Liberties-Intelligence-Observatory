# ADR-0007: Evidence Source Licensing Boundary and Commercial-Use Firewall

Status: Accepted
Date: 2026-07-11

## Context

The 2026-07-11 licensing and compliance review (`docs/07-governance/licensing-compliance-register.md`) found that OONI (CC BY-NC-SA 4.0) and ACLED (contractual, non-commercial-default, with a functional-substitute and AI/ML-training prohibition applying "regardless of whether such use is commercial, academic, or experimental") are both commercially restricted, while STOP/Access Now (CC BY 4.0) is commercially clear, Google Transparency Report's reuse terms are undetermined, and CPJ (CC BY-NC-ND 4.0) is blocked pending direct resolution. ADR-0003 adopted OONI and ACLED as CLIO's foundation datasets on methodological grounds alone and never evaluated their licensing terms — this ADR closes that gap. It does not revise ADR-0003's methodological conclusion.

An advisory consultation obtained specifically for this decision (recorded in the compliance register, Part 3) concluded that CLIO's "never redistribute third-party datasets, only transform into attributed intelligence" architectural instinct is good practice but does not, by itself, resolve either restriction — both attach to the use of the evidence, not only to its redistribution.

A subsequent strategic review (`docs/01-product/2026-07-11-commercialization-architecture-discussion.md`, `-stress-test-commercial-identity.md`, `-research-flagship-vs-commercial-spinoff.md`) converged on a working position: CLIO is the flagship research and methodology observatory, not the commercial product itself; grants are the primary funding mechanism for its first stage; the Finance Bill 2024 report will not be sold; and the durable commercial opportunity, if pursued later, comes from the methodology and engineering discipline, not from reselling OONI- or ACLED-derived outputs.

## Decision

**CLIO's OONI- and ACLED-derived intelligence layer is treated as non-commercial and grant/public-interest-funded for the foreseeable term, not as a product for direct sale.** This is not presented as a permanent legal conclusion — it is the correct default under a genuinely unresolved legal question (see Consequences), adopted because it is the safer posture, because grants are the chosen funding mechanism for this stage regardless of the licensing question, and because it matches CLIO's own stated identity as a research flagship rather than a commercial product.

**STOP/Access Now-derived findings are not subject to this restriction** and may be used commercially once STOP is actually ingested, per ADR-0003's existing recommendation.

**A single, small, disclosed, non-recurring engagement — as distinct from a scaled or subscription-style commercial product — is treated as a genuinely open question, not a concluded prohibition.** The register found the evidence base should be non-commercial "unless and until" resolved; it did not find that one attributed, properly-cited, cost-recovery engagement is definitely a violation. This ADR does not authorize such an engagement; it records that the question has not been closed by legal counsel and should not be treated as closed in future planning.

**The long-term commercial opportunity is scoped to what is licensing-independent**: the classification and attribution methodology, the confidence-scoring framework, the Evidence Source Acceptance Framework, and the AI-layer discipline (Intelligence Translation Layer, Prompt Contract Layer, hard prohibitions) — see `docs/01-product/2026-07-11-execution-roadmap-grant-and-flagship.md`, Part D, for the current inventory. No implementation of any commercial spinoff is authorized by this ADR; it only records that this is the direction future commercial exploration should take if and when it resumes.

## Consequences

CLIO's roadmap priority shifts from commercialization engineering (an API, a subscription tier, scaled report production) to grant-readiness engineering (compliance verification, attribution correctness, a methodology whitepaper, a flagship-report portfolio) — see `docs/01-product/2026-07-11-execution-roadmap-grant-and-flagship.md`, Part A, for the concrete milestones this produces.

Provider outreach to ACLED and OONI (already recommended in the compliance register) remains valuable regardless of this ADR's non-commercial default — a future negotiated license would not require reversing this decision, only updating it, and the outreach itself (Part A, Milestone A4) is scheduled independently of whether it succeeds.

This ADR should be revisited if any of the following change: ACLED or OONI grant a specific commercial license or partnership; actual legal counsel resolves the "single small engagement" question either way; or STOP's ingestion (not yet built) reaches production, at which point a STOP-only commercial tier becomes possible without touching this ADR's restriction on OONI/ACLED at all.
