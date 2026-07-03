# CLIO Implementation Roadmap — Engineering Reset

Status: Phase 3 deliverable, CLIO Engineering Reset. Evolutionary improvement, not a rewrite. Every item below references a specific finding in `architecture-assessment.md`, `technical-debt-inventory.md`, or `methodology-consistency-review.md` — nothing here is invented independently of those three documents. This roadmap is scoped to engineering health; the separate commercial/product roadmap from the Project Zero Review (`docs/01-product/roadmap.md`) is not repeated here and should be read alongside it, since a few items depend on each other across the two documents.

## Step 0 — Verification, before anything else (hours, not days)

These are investigations, not redesigns, and they change the shape of several later steps.

1. **CONFIRMED (2026-07-04).** No asset under `Bruin/assets/reporting/` references `intelligence.acled_pressure_regimes` or `intelligence.country_readiness`, in either the declared `@bruin depends:` header or the SQL body — verified by reading all four reporting assets in full, not just grepping headers. `political_stress_windows_mart.sql` and `protocol_repression_correlation_mart.sql` both source ACLED pressure from `marts.fact_country_pressure_daily`, which in turn reads directly from `stg.acled_conflict_events`, bypassing `int.acled_event_classification`, `features.acled_pressure_signals`, and `intelligence.acled_pressure_regimes` entirely. Path A is not merely unconsumed at the reporting layer — it is bypassed at the very first step after staging. The dashboard's national pressure score is built entirely from Path B. This closes the single highest-leverage open question in the reset. Step 3 below now has a confirmed starting point rather than an open question: the choice is between wiring Path A in, replacing Path B with it, or formally deprecating Path A, and that choice is no longer blocked on investigation.
2. **Confirm the full blast radius of the Lumen synthetic-data finding.** Trace every mart and page that touches `stg.lumen_requests`-derived data to know exactly what is affected before deciding how to flag or fix it (TD-01). Still open.

## Step 1 — Mechanical fixes (days)

Low-risk, low-effort, high value-per-hour. No architectural judgment required.

- Regenerate `Bruin/requirements.txt` from the same source as `uv.lock`, resolving the `duckdb` version drift (TD-06).
- Bump the devcontainer's Python base image to match `pyproject.toml`'s `>=3.12.3` requirement (TD-07).
- Delete `streamlit/services/freshness.py`, `streamlit/components/charts.py`, `streamlit/components/tables.py`, and `logs/query_log.sql` (TD-17, TD-18, TD-32) — all confirmed dead code with no callers.
- Fix the top-level `README.md`'s stale repository-structure diagram (TD-22) — the cheapest, highest-visibility documentation fix available.
- Rename `streamlit/pages/3_Protocol__Stress_Intelligence_Observatory.py` to remove the double underscore, and standardize on `use_container_width=True` across all pages (TD-26, TD-27).
- Reconcile the `fact_platform_blocking_summary.sql` filename/name mismatch (TD-21).
- Disable `DEBUG_SQL_LOG` by default in `backfill_acled_pressure_regimes.py`, making it opt-in (TD-25).

## Step 2 — Provenance and correctness fixes (1–2 weeks)

These require judgment but not architectural change.

- Add a `source_authenticity` / `is_synthetic` flag at `stg.lumen_requests`, propagated through every downstream consumer, surfaced anywhere a Lumen-derived number reaches a page or report (TD-01). This should land before Step 3's confidence-scheme unification, since it is a strictly more urgent provenance gap.
- Fix the `CROSS JOIN` in `get_finance_bill_incident()` (TD-02) — join on measurement date plus an explicit key, or aggregate ASN behavior separately before combining. This directly affects the accuracy of the Minimum Lovable Product's flagship report.
- Add a runtime guard to `intelligence.acled_pressure_regimes` refusing execution on precondition violation (TD-04), regardless of what Step 0's verification finds — this fixes a silent-corruption risk independent of whether the asset turns out to be wired into reporting.
- Stop swallowing secret-parsing exceptions silently in `bq.py` (TD-19) and stop surfacing raw stack traces to end users (TD-20).

## Step 3 — Methodology unification (2–4 weeks, Step 0 now confirmed)

- Resolve the confidence-scheme duplication per ADR-0001 (`docs/02-architecture/adr/0001-unify-confidence-scoring.md`, TD-05) — migrate `int.ooni_experiment_results.sql`'s inline literals to the governed dimension-table scheme.
- Decide what to do about the confirmed Path A / Path B split: wire `intelligence.acled_pressure_regimes` into a reporting mart, formally deprecate it with a note explaining why it exists but isn't used, or replace `marts.fact_country_pressure_daily`'s contribution to `reporting.mart_political_stress_windows` with the more rigorous path. This is now a decision, not an investigation — Step 0 already confirmed which path is live. Do not leave the choice unmade past this step.
- Add golden-file regression tests tied to the Finance Bill 2024 incident and at least one other known case, covering both the OONI and ACLED classification/regime logic (TD-08, per `testing-strategy.md` Priority 1). This is what would have caught the `upgraded_assets` regression (TD-30) before it had a chance to be merged.

## Step 4 — Portability and hygiene (parallel with Step 3, lower urgency)

- Make the local-ingestion root path configurable rather than hardcoded to a Windows path in both `scripts/local_ingest_ooni.py` and `scripts/download_ooni.ps1` (TD-11).
- Replace the manual resume-checkpoint literal in `download_ooni.ps1` with a persisted state file (TD-12).
- Migrate away from long-lived downloadable service-account keys in `infra/setup-gcp.sh` toward Workload Identity Federation (TD-13).
- Scope the IAM module's `roles/editor` grant down to specific roles (TD-14).
- Externalize hardcoded project ID and country literals across mart SQL via Bruin variables (TD-09) — this step should happen here, not earlier, because it is genuinely needed only once multi-country expansion is imminent, consistent with not introducing configuration abstraction before it is needed.

## Step 5 — Documentation reconciliation (parallel, low risk)

- Archive `docs/data-modelling.md`, `docs/civil-liberties-reporting-playbook-Kenya.md`, and `docs/readme1_1.md` into a `docs/_archive/` folder inside the repository itself once it becomes a live git project, per the disposition in `docs/00-overview/documentation-plan.md` (TD-23, TD-24, TD-31).
- Populate the Methodology Changelog and Metric Dictionary described in `documentation-standards.md` incrementally, starting with whatever changes as a direct result of Steps 2 and 3 above — do not attempt to backfill the full history at once.

## Step 6 — Entity resolution and attribution (after Steps 2–3, several weeks)

- Build the `dim_entities` canonical mapping table (TD-10), enabling the pressure-attribution work already prioritized in the Project Zero Review's commercial roadmap. This step is placed here, not earlier, because it depends on the confidence and provenance fixes above being in place first — attribution built on top of an unresolved confidence ambiguity or unflagged synthetic data would inherit both problems invisibly.

## What this roadmap deliberately does not include

No rewrite of the OONI path or ACLED path A's core logic — both are genuinely good and are the standard, not the problem. No new shared abstraction for data source integration (a base contract, a plugin system) until Google Transparency and Lumen have been brought up to a comparable methodological standard one at a time — there are not yet enough well-understood cases to generalize from safely. No multi-country parameterization before Step 4, since doing it earlier would multiply, not amortize, the hardcoding problem it is meant to fix.

## Cross-reference to the commercial roadmap

`docs/01-product/roadmap.md` (from the Project Zero Review) sequences commercial priorities — packaging the Finance Bill report, building the pressure-attribution layer, the AI narrative layer, the API. Steps 2 and 3 above (the CROSS JOIN fix and the confidence-scheme unification) are prerequisites for that roadmap's own Immediate-horizon items, since both directly affect the accuracy of the first sellable report. Read the two roadmaps together before sequencing actual work.
