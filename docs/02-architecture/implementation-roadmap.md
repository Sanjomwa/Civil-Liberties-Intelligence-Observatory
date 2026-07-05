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

- **RESOLVED (2026-07-05, commit `69233b4`).** Added a real, per-row `is_synthetic` flag at `stg.lumen_requests`, propagated through every downstream consumer (both the live-reporting branch and the currently-unconsumed dead-end branch, for consistency), surfacing as a visible warning on every Streamlit page a Lumen-derived number reaches, plus a permanent limitations section on the Methodology page. Verified end to end against materialized tables and by rendering all affected pages. Surfaced a related, separately-tracked DAG-wiring finding (TD-42, not fixed as part of this).
- **RESOLVED (2026-07-05, commit `eb6993e`).** Fixed the `CROSS JOIN` in `get_finance_bill_incident()` (TD-02) — not by adding a join key (there was none to add: `asn_behavior_profile_mart` has no date grain at all) but by splitting into two independent, unjoined dataframes at their real respective grains. Verified against live data: undistorted row counts (124 correlation rows, 3 ASN rows, vs. the old fabricated 372) and a rendered-page screenshot confirming page 7's charts now show the real, non-tripled numbers.
- Add a runtime guard to `intelligence.acled_pressure_regimes` refusing execution on precondition violation (TD-04), regardless of what Step 0's verification finds — this fixes a silent-corruption risk independent of whether the asset turns out to be wired into reporting.
- Stop swallowing secret-parsing exceptions silently in `bq.py` (TD-19) and stop surfacing raw stack traces to end users (TD-20).

## Step 3 — Methodology unification (2–4 weeks, Step 0 now confirmed)

- Resolve the confidence-scheme duplication per ADR-0001 (`docs/02-architecture/adr/0001-unify-confidence-scoring.md`, TD-05) — migrate `int.ooni_experiment_results.sql`'s inline literals to the governed dimension-table scheme.
- **COMPLETE (2026-07-04, ADR-0002).** Wired `intelligence.acled_pressure_regimes` (path A) into the reporting layer. All five steps done: (a) confirmed actual backfill state, surfacing and resolving TD-13 and TD-36 along the way; (b) completed Kenya's historical backfill (1,523/1,523 weeks, 0 errors), producing the first real evidence for this ADR — clean detections of the Jan 2008 post-election violence, the Aug 2022 election, and the Finance Bill 2024 protests; (c) added and applied the TD-04 runtime precondition guard; (d) landed TD-08's golden-file tests (Layer B); (e) **design corrected mid-implementation, based on direct investigation**: the original "replace path B" framing assumed a clean swap, but path B's daily continuous composite score and path A's weekly categorical regime classification turned out to be different kinds of things entirely — so the actual change shipped **additively**: `fact_country_pressure_daily` gained a `regime_*`-prefixed `LEFT JOIN` to path A (Saturday-week-anchored, verified empirically, not assumed), both reporting marts pass those columns through unchanged, and the dashboard gained a new, separate regime-classification panel — no existing column, score, or chart touched. Path B's retirement is deliberately deferred to a future decision after an observation period. This work also surfaced **TD-40**, a separate and still-open critical bug (`fact_country_pressure_daily`'s `acled` CTE groups by an always-`NULL` `event_date`, meaning the *next* materialization for any reason would silently zero the composite score) — deliberately left unfixed, verified around instead via a non-materializing query, and now the single most urgent open item. See ADR-0002 for full detail. Real evidence from the Finance Bill 2024 comparison also sharply raises the urgency of TD-01 and TD-02 below: path B's peak reading for that entire window never exceeded `ELEVATED`, even the week Parliament was stormed, partly propped up by TD-01's synthetic Lumen data.
- Add golden-file regression tests tied to the Finance Bill 2024 incident and at least one other known case, covering both the OONI and ACLED classification/regime logic (TD-08, per `testing-strategy.md` Priority 1). This is what would have caught the `upgraded_assets` regression (TD-30) before it had a chance to be merged.

## Step 3b — OONI app-identity and protocol-layer attribution (tiered, following the 2026-07-05 diagnostic)

A diagnostic investigation (TD-47 through TD-52, `technical-debt-inventory.md`) traced whether OONI's app identity (`test_name`) and protocol-layer cause detail survive CLIO's pipeline from raw ingestion to the dashboard, triggered by a direct question about attributing findings to a specific app (Telegram, WhatsApp, Signal) and a specific protocol layer (DNS/TCP/TLS/HTTP). None of the six findings are fixed yet. They are sequenced below by cost and payoff, not by discovery order, since they range from a one-line predicate fix to a genuine data-scope decision — do not treat this as one unit of work.

**Tier 1 — cheap, self-contained, no design decision required:**
- Fix TD-52's live predicate bug in `fact_platform_blocking_summary.sql:92-95` (`blocking_detail = 'dns'` never matches a real value; needs a prefix match such as `STARTS_WITH(blocking_detail, 'dns.')`).
- Wire TD-51's already-populated `fact_platform_blocking_summary` (full, uncoarsened `test_name`/`protocol` breakdown at monthly grain, currently zero consumers) into a new Streamlit panel — the cheapest real path to per-app/per-protocol-layer visibility, since the data already survives this far and no new ingestion or schema work is needed.
- Recover TD-47's `dnscheck` `bootstrap` subset only — a corrected/additional fixed JSONPath (`$.bootstrap.queries`), structurally compatible with the existing `dns_bogon_events`/`dns_nxdomain_events` classification logic, recovering one real system-resolver DNS result per `dnscheck` measurement without any new schema.
- Fix TD-43's stale doc comment (`int.acled_event_classification.sql:267`) — bundled here because it is equally cheap, not because it is otherwise related to the OONI findings above.

**Tier 2 — requires a real but bounded decision, not new infrastructure:**
- Decide whether app-family attribution should survive past `features.protocol_daily_signals` (TD-48) and, separately, whether it should survive into the reporting layer (TD-49) — two related but distinctly-scoped collapses, one step apart in the chain.
- Resolve TD-45's `composite_pressure_score` naming collision between `fact_country_pressure_daily` and `political_stress_windows_mart`.
- Re-derive TD-44's `pressure_level` thresholds against the post-ADR-0004 score distribution.
- Reconcile TD-42's `lumen_requests_to_gcs` declared-vs-actual dependency mismatch.

**Tier 3 — genuine new infrastructure or scope decisions; do not start without a separate design pass:**
- TD-50 — carrying cause-level protocol detail (DNS NXDOMAIN vs. bogon, TCP reset vs. timeout, TLS handshake failure, HTTP 451 vs. other errors) into the intelligence/reporting layers. A wider-grain change to an intelligence-layer asset, not a reporting mart's `GROUP BY` fix like TD-49.
- TD-47's `dnscheck` `lookups` subset (per-resolver DNS censorship-resistance detail — arguably the test's actual point) and `tor` subset (circumvention-infrastructure reachability) — both require new ingestion-time JSON flattening for dynamic-keyed objects, and `tor` additionally requires a deliberate decision about whether "is the circumvention tool itself reachable" belongs in CLIO's app-blocking evidence model at all, rather than defaulting to inclusion.
- TD-39 — the Layer A test-isolation infrastructure gap (a dedicated BigQuery test dataset/project, WIF credentials wired into `tests.yml`), included here because any Tier 3 schema work above should ship with real regression coverage, which is currently blocked on this same unresolved infrastructure question.

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
