# CLIO Technical Debt Inventory

Status: Phase 0 deliverable, CLIO Engineering Reset. Itemized, with severity and recommended action. No code has been changed. Severity reflects a combination of correctness risk, security exposure, and blast radius if the item causes a wrong number to reach a client — not effort to fix. See `implementation-roadmap.md` for sequencing.

## Critical

| ID | Location | Description | Recommended action |
|---|---|---|---|
| TD-01 | `stg.lumen_requests` → `int.lumen_pressure_daily` → `marts.fact_takedown_activity` / `fact_country_pressure_daily` | Lumen data is entirely synthetic (`scripts/lumen_parquet.py` fabricates 5,000 rows via `np.random.seed(42)`), with no `is_synthetic` flag anywhere downstream. Any report citing a Lumen-derived figure is currently citing fabricated data with no structural way to tell. | Add a provenance flag propagated from ingestion through every consuming table; block any client-facing report from citing Lumen-derived numbers until real data replaces the synthetic set or the flag exists and is surfaced. |
| TD-02 | `streamlit/services/marts.py`, `get_finance_bill_incident()`, lines ~406–431 | Confirmed `CROSS JOIN` between `protocol_repression_correlation_mart` and `asn_behavior_profile_mart` filtered only by date and `network_class = 'MAJOR_KENYA_PROVIDER'`, with no join key connecting ASN data to specific protocol/date rows. If more than one ASN qualifies, every protocol/date row is duplicated once per qualifying ASN, inflating page 7's KPIs and misattributing ASN columns flatly across rows. | Replace with a proper join on measurement date plus an explicit key, or aggregate ASN behavior separately before combining. |
| TD-03 | `intelligence.acled_pressure_regimes` vs. `reporting/*` | **Confirmed 2026-07-04** (Architecture Assessment Section 6): no `reporting/*` asset references the ACLED path A regime engine or `intelligence.country_readiness`, in header or SQL body. The dashboard's national pressure score is built entirely from the simpler, unguarded ACLED path B (`marts.fact_country_pressure_daily`, which itself reads straight from `stg.acled_conflict_events`). | Decide, per Step 3 of the Implementation Roadmap: wire path A into a reporting mart, replace path B with it, or formally deprecate path A. No longer an open investigation. |
| TD-04 | `intelligence.acled_pressure_regimes.sql`, documented "ARCHITECTURE FREEZE" / BLOCKER-002 | The regime engine's correctness depends on an unenforced precondition — exactly one country, one new week, per execution — enforced only by a comment and operator discipline, not by the system. A violation corrupts persisted state silently. | Add a runtime guard that refuses to execute on precondition violation, or redesign to remove the execution-order dependency. |
| TD-05 | `int.ooni_experiment_results.sql` vs. `dim_censorship_confidence` and related dimension tables | Two unreconciled confidence-scoring implementations coexist: a governed dimension-table scheme and hardcoded inline literals. A report citing "confidence: HIGH" may mean different things depending on which code path produced it. | Retire one scheme, migrate the other, record the decision as an ADR before any AI narrative layer is built on top of either. |

## High

| ID | Location | Description | Recommended action |
|---|---|---|---|
| TD-06 | `Bruin/requirements.txt` vs. `pyproject.toml` / `uv.lock` | `duckdb==0.10.0` pinned in one lockfile, `duckdb>=1.5.0` (resolving to 1.5.0) in the other. Two authoritative dependency mechanisms disagree by more than a major version. | Regenerate `Bruin/requirements.txt` from the same source as `uv.lock`, or eliminate the duplicate lockfile. |
| TD-07 | `.devcontainer/devcontainer.json` | Base image is Python 3.11; `pyproject.toml` requires `>=3.12.3`. Anyone using the documented devcontainer is on the wrong interpreter version. | Bump the devcontainer base image. |
| TD-08 | `tests/test_contracts.py` | The only test file in the repository (~70 lines, four tests), covering only the Streamlit contract-validation helper. The classification and regime logic — the code carrying the most business and legal risk — has zero behavioral test coverage. | Add golden-file regression tests tied to known historical incidents (e.g., the Finance Bill 2024 window) before the confidence-scheme and ACLED-path questions are resolved, so regressions are caught automatically going forward. |
| TD-09 | Multiple mart SQL files (e.g. `fact_country_pressure_daily.sql`, `protocol_repression_correlation_mart.sql`, `asn_behavior_profile_mart.sql`) | Hardcoded project ID (`encoded-joy-485413-k5`) and country literal (`iso2 = 'KE'` / `country = 'KE'`) scattered across mart SQL. Blocks multi-country expansion. | Externalize via `@iso2` Bruin variables and environment-driven project configuration. |
| TD-10 | ACLED, Lumen, OONI actor/requestor/ASN identifiers | No entity resolution across sources — the same real-world actor can appear under different labels in different tables. | A `dim_entities` canonical mapping table, deferred until the pressure-attribution work that needs it is underway. |
| TD-11 | `scripts/local_ingest_ooni.py` line 20, `scripts/download_ooni.ps1` line 2 | Both hardcode `C:\ooni-kenya-censorship` as the default/base local ingestion path. The local-ingestion story is Windows-only by convention, in a project that also runs in Linux Codespaces. | Make the root path environment-driven with a documented default per platform. |
| TD-12 | `scripts/download_ooni.ps1` line 5 | Manual resume checkpoint (`$ResumeFromDate = "2025-06-29"`) with an inline "CHANGE THIS to resume" comment — no persisted state file, relies on the operator remembering to edit the script before each run. | Persist the last-synced date to a small state file the script reads and updates automatically. |
| TD-13 | `infra/setup-gcp.sh` lines 10, 50–52 | Downloads a long-lived JSON service-account key to local disk (`terraform-key.json`) rather than using Workload Identity Federation or short-lived tokens. | Migrate to WIF or a short-lived credential flow before any production use. |
| TD-14 | `infra/modules/iam/main.tf` | Grants `roles/editor` (broad, not least-privilege) to a single hardcoded human admin identity at the module level. | Scope to specific roles needed, separate from the more carefully scoped `terraform-sa` service account already set up in `setup-gcp.sh`. |
| TD-15 | `Bruin/scripts/historical_initializer/backfill_acled_pressure_regimes.py` line 84 | `METHODOLOGY_VERSION = "ACLED_REGIME_ENGINE_V1"` must manually match a literal inside the SQL asset's CTE-01, with no automated check that they agree. | Centralize into the methodology governance layer already recommended elsewhere (see Architecture Assessment Section 7); until then, add a CI check comparing the two literals. |

## Medium

| ID | Location | Description | Recommended action |
|---|---|---|---|
| TD-16 | `streamlit/services/marts.py` lines 163–165 | `get_protocol_stress_intelligence()` is a trivial alias for `get_protocol_regimes()` — pages 2 and 3 render the identical underlying query with no distinct data. | Decide whether pages 2 and 3 should be merged, or whether page 3's genuinely more defensive rendering should replace page 2 outright. |
| TD-17 | `streamlit/services/freshness.py` | Entirely unused dead code (confirmed via repo-wide search — no page or service imports it). Internal header comment (`# utils/validate.py`) does not match its filename, and its schema constants reference the stale dimensional-model vocabulary, not the real reporting marts. | Delete. |
| TD-18 | `streamlit/components/charts.py`, `streamlit/components/tables.py` | Both self-documented as "aspirational, kept for future use" and confirmed unused by any page. | Delete, or move to a clearly labeled `future/` or `Archive/` location if genuinely intended for near-term use. |
| TD-19 | `streamlit/services/bq.py` lines 28–29 | `_get_streamlit_service_account_info()` swallows any secret-parsing error via a bare `except Exception: return None`, which could silently hide a misconfigured secret. | Log the specific exception even if the function still falls back to `None`. |
| TD-20 | `streamlit/services/bq.py`, `run_query()` bare-exception branch | Full stack traces are shown to end users via `st.exception(exc)` on unexpected query failure in a public-facing app — an information-disclosure smell (could reveal project IDs, dataset names, or query text). | Log the traceback server-side; show a generic message to the user. |
| TD-21 | `Bruin/assets/marts/facts/fact_platform_blocking_summary.sql` | Filename says "platform," the internal `name:` field says "protocol" — a naming inconsistency. | Reconcile filename and declared name. |
| TD-22 | Top-level `README.md`, "Repository Structure" section | Stale: lists one of eight Streamlit pages and omits several actually-used `core/`/`components/` modules. | Regenerate from the actual current tree; cheap, high-value first fix. |
| TD-23 | `docs/data-modelling.md`, `docs/civil-liberties-reporting-playbook-Kenya.md` | Both describe a Kimball/CLRI dimensional architecture inconsistent with the actual implemented reporting layer's vocabulary; `data-modelling.md` additionally contains a duplicated section header and leftover reviewer/LLM commentary left in the shipped document. | See Repository Documentation Plan for disposition — likely archive with a note, not delete, since the underlying dims/facts code is real (Architecture Assessment Section 5). |
| TD-24 | `docs/readme1_1.md` | An earlier, more elaborate README draft with more extensive ethics/responsible-use content than the current shipped README. | Reconcile the ethics section back into the current README, then archive the draft. |
| TD-25 | `Bruin/scripts/historical_initializer/backfill_acled_pressure_regimes.py` lines 95–96 | Debug SQL logging (`DEBUG_SQL_LOG`) writes every MERGE statement to disk, left enabled in the shipped script despite a comment saying to disable it once debugging is complete. | Disable by default; make opt-in via a flag. |
| TD-26 | `streamlit/pages/3_Protocol__Stress_Intelligence_Observatory.py` (filename) | Double underscore in the filename, apparently a typo. | Rename for consistency with the other page files. |
| TD-27 | `streamlit/pages/3_Protocol__Stress_Intelligence_Observatory.py` vs. all other pages | Uses `width="stretch"` where every other page uses `use_container_width=True` — an inconsistent Streamlit API convention within the same codebase. | Standardize on one convention. |
| TD-28 | `streamlit/pages/5_ASN_Behavioral_Intelligence.py` line 67 | Passes a literal string (`"Latest Profile Snapshot"`) into a trust-strip parameter that every other page fills with an actual date value — likely intentional (this mart has no date column) but undocumented as such. | Add a code comment explaining why this page's contract differs. |
| TD-29 | `upgraded_assets/features/acled_pressure_signals.sql` (unsuffixed variant) | Reverts several deliberate fixes already made in the canonical file: removes per-family baseline gating, removes the calendar spine (re-introducing the exact non-adjacent-week corruption the canonical version's own comments warn against), and reverts the `stddev_floor` to the value the canonical version explicitly rejected as invalid for ACLED data. | Must not be merged as-is. Treat as a historical/earlier draft, not an upgrade, when deciding what to do with `upgraded_assets/`. |
| TD-30 | `upgraded_assets/intermediate/int.acled_event_classification.sql` (unsuffixed variant) | Reintroduces a bug the canonical file's own comments describe fixing: computes `methodology_risk_level` using `WHEN event_type = 'UNCLASSIFIED'`, a condition that can never be true, silently defaulting every unclassified event to `LOW` risk instead of the intended `HIGH`. | Must not be merged as-is; flag clearly in any archival note so a future contributor does not reintroduce this regression. |
| TD-31 | `Bruin/assets/marts/dims/`, `marts/facts/` documentation vs. code | The code is real and load-bearing (Architecture Assessment Section 5); the documentation describing it is stale/aspirational. This is a documentation debt, not a code debt, but is listed here because it actively misleads. | See Repository Documentation Plan. |
| TD-32 | `logs/query_log.sql` | Empty (zero lines), no apparent write path. | Delete. |

## Low

| ID | Location | Description | Recommended action |
|---|---|---|---|
| TD-33 | `infra/modules/gcs/main.tf` | `force_destroy = true` on the storage bucket — fine for dev/demo, a data-loss risk if carried unmodified into a production environment. | Revisit before any production deployment. |
| TD-34 | `infra/verify-gcp.sh` | Not wired into CI; minimal exit-code handling. | Low priority; wire in once CI covers infra changes at all. |
| TD-35 | `infra/modules/iam/main.tf` vs. `infra/setup-gcp.sh` | Two overlapping but different identity-management approaches (a broadly-scoped human admin grant in Terraform, a more narrowly-scoped `terraform-sa` service account in the shell script) with no written explanation of which governs what. | Document the intended division of responsibility, or consolidate. |

## Summary by severity

| Severity | Count |
|---|---|
| Critical | 5 |
| High | 10 |
| Medium | 17 |
| Low | 3 |
| **Total** | **35** |

See `implementation-roadmap.md` for how these are sequenced. Verification items (TD-01, TD-03) come first because they change the shape of several other items.
