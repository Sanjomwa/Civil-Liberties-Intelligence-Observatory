# ADR-0008: Evidence Source Acceptance Framework as a Formal Onboarding Gate

Status: Accepted
Date: 2026-07-11

## Context

CPJ was evaluated and classified Core in ADR-0003 on methodological grounds — provenance, grain, attribution power — before its licensing terms were checked. The licensing conflict (CC BY-NC-ND 4.0, incompatible with CLIO's derivative, potentially commercial use) was only found afterward, during a feasibility investigation, by which point real technical and evaluative effort had already gone into it. The 2026-07-11 compliance review formalized an eleven-dimension Evidence Source Acceptance Framework (`docs/07-governance/licensing-compliance-register.md`, Part 4) covering independence, provenance, methodological transparency, temporal and spatial resolution, attribution capability, confidence contribution, evidentiary value, licensing compatibility, commercial compatibility, and maintenance risk — generalizing the ad hoc evaluation ADR-0003 already performed for OONI, ACLED, STOP, CPJ, IODA, Freedom House, CIPESA, and Google Transparency Report.

## Decision

**No future evidence source proceeds past initial evaluation into feasibility or ingestion work until it has been scored against all eleven dimensions of the Evidence Source Acceptance Framework, with licensing compatibility and commercial compatibility evaluated first, before methodological or technical feasibility work begins.** This reverses the order this project actually followed for CPJ, deliberately, in response to that specific near-miss.

This applies to every future candidate named in this project's own documents as not-yet-ingested, including STOP (already scored Compliant and Core — no re-evaluation needed, this ADR only formalizes the gate for sources not yet scored), any future NGO or platform dataset, and any customer-supplied evidence considered under the "custom evidence generation" commercial direction named in `docs/01-product/2026-07-11-research-flagship-vs-commercial-spinoff.md` (not yet pursued — see that document's own caution against building this ahead of a real customer asking for it).

## Consequences

A source failing licensing or commercial compatibility is not disqualified outright — it may still be adopted for non-commercial, attributed use (as OONI and ACLED currently are, per ADR-0007) — but it is disqualified from any commercial-product plan until that specific restriction is resolved, and that disqualification must be recorded before any technical feasibility work starts, not after.

This ADR does not require new tooling to enforce — the framework is a documented evaluation checklist, not a CI check, since evidence-source onboarding is an infrequent, human-reviewed decision, not a continuous pipeline property. It should be referenced explicitly (by dimension) in any future ADR proposing a new evidence source, the same way ADR-0003's criteria are referenced in this document.
