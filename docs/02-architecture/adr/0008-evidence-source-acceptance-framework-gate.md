ADR-0008: Evidence Source Acceptance Framework as a Formal Onboarding Gate
Status: Accepted
Date: 2026-07-11
Context
CPJ was evaluated and classified Core in ADR-0003 on methodological grounds — provenance, grain, attribution power — before its licensing terms were checked. The licensing conflict (CC BY-NC-ND 4.0, incompatible with CLIO's derivative, potentially commercial use) was only found afterward, during a feasibility investigation, by which point real technical and evaluative effort had already gone into it. A 2026-07-11 internal compliance review formalized an eleven-dimension Evidence Source Acceptance Framework, generalizing the ad hoc evaluation ADR-0003 already performed for OONI, ACLED, STOP, CPJ, IODA, Freedom House, CIPESA, and Google Transparency Report. The eleven dimensions, recorded here in full so this ADR is self-contained rather than pointing at an internal-only document:
Independence — is the source's reporting independent of the parties whose conduct it measures?
Provenance — is the collection method published, repeatable, and traceable to specific observations?
Methodological transparency — does the source publish its methodology, not just its outputs?
Temporal resolution — does the source's true update cadence and event-dating precision honestly match the decision cycle it would be used for?
Spatial resolution — country-level, sub-national, or point-level?
Attribution capability — does the source say who and why, not just that something happened?
Confidence contribution — does incorporating it improve or degrade the honesty of CLIO's existing confidence scoring?
Evidentiary value — chain-strengthening (improves confidence in existing findings) or vector-opening (answers a question nothing else asks), and is that value genuinely non-substitutable?
Licensing compatibility — what is the source's license, and is it compatible with the intended use at the intended commercial/non-commercial tier? (The dimension ADR-0003 omitted for OONI and ACLED, and the one that caught CPJ's conflict — after the fact, which is exactly what this ADR corrects.)
Commercial compatibility — independent of general licensing, does the source specifically permit, or allow separately licensing, use in a commercial product?
Maintenance risk — is access via an official, documented, stable channel, or an undocumented one that could change or be revoked without notice?
Decision
No future evidence source proceeds past initial evaluation into feasibility or ingestion work until it has been scored against all eleven dimensions above, with licensing compatibility (9) and commercial compatibility (10) evaluated first, before methodological or technical feasibility work begins. This reverses the order this project actually followed for CPJ, deliberately, in response to that specific near-miss.
This applies to every future candidate named in this project's own documents as not-yet-ingested, including STOP (already scored Compliant and Core — no re-evaluation needed, this ADR only formalizes the gate for sources not yet scored), any future NGO or platform dataset, and any customer-supplied evidence considered under a future "custom evidence generation" commercial direction (not yet pursued, and not to be built ahead of a real customer asking for it).
Consequences
A source failing licensing or commercial compatibility is not disqualified outright — it may still be adopted for non-commercial, attributed use (as OONI and ACLED currently are, per ADR-0007) — but it is disqualified from any commercial-product plan until that specific restriction is resolved, and that disqualification must be recorded before any technical feasibility work starts, not after.
This ADR does not require new tooling to enforce — the framework is a documented evaluation checklist, not a CI check, since evidence-source onboarding is an infrequent, human-reviewed decision, not a continuous pipeline property. It should be referenced explicitly (by dimension) in any future ADR proposing a new evidence source, the same way ADR-0003's criteria are referenced in this document.