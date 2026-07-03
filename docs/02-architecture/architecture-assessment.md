# CLIO Architecture Assessment

Status: Phase 0 deliverable, CLIO Engineering Reset. Read-only assessment — no code was changed to produce this document.
Sources: direct reading of the repository (`Civil-Liberties-and-Censorship-Analysis-with-Bruin-main`), the prior CLIO Project Zero Review, and a targeted gap-fill pass covering every previously-unread file (Streamlit pages 1/2/3/5/6, all services, all scripts, all infra modules, and a byte-level comparison of `upgraded_assets/` against the canonical repository).

## 1. System Architecture Overview

CLIO is a batch-oriented, SQL-first analytical pipeline orchestrated by Bruin against BigQuery, with a read-only Streamlit exploration layer on top. The pipeline follows a layered ELT shape:

```
ingest (Python)        raw JSONL/CSV -> parquet, written to raw.* tables
load (Python)          raw.* parquet -> GCS -> BigQuery external table refresh
staging (SQL)          source-specific structural normalization (stg.*)
intermediate (SQL)     cross-source prep, classification, confidence assignment (int.*)
features (SQL)         statistical baselines, guardrails, anomaly detection
intelligence (SQL/py)  regime and relationship inference (stateful and stateless)
marts/dims+facts (SQL) conformed dimensional model (a second, partially-realized branch)
reporting (SQL)        dashboard-facing marts, the layer Streamlit actually queries
Streamlit (Python)     core/ + components/ + services/ + 8 pages
```

Five source pipelines run through this shape in parallel: OONI (network measurement), ACLED (conflict events), Google Transparency Report (platform takedown requests), Lumen Database (legal takedown requests — **see Section 4, this is currently synthetic data**), and a set of governed confidence/measurement-quality reference dimensions that sit outside any single source.

## 2. Module Boundaries

| Module | Responsibility | Language |
|---|---|---|
| `Bruin/assets/ingest/` | Pull raw source data (OONI JSONL, ACLED CSV, Google Transparency CSV, Lumen CSV) into `raw.*` tables | Python |
| `Bruin/assets/load/` | Publish raw parquet to GCS and refresh BigQuery external tables | Python |
| `Bruin/assets/staging/` | Structural normalization per source, one `stg.*` table per source/sub-signal | SQL |
| `Bruin/assets/intermediate/` | Cross-source preparation: OONI experiment aggregation, ACLED event classification with confidence assignment | SQL |
| `Bruin/assets/features/` | Statistical feature engineering with explicit guardrails (sparse-window, zero-variance, low-sample flags) | SQL + one Python contract validator |
| `Bruin/assets/intelligence/` | Regime and relationship inference — both stateless (protocol signal regimes) and stateful (ACLED pressure regimes, with a dedicated backfill orchestrator) | SQL + Python |
| `Bruin/assets/marts/dims/`, `marts/facts/` | A conformed dimensional model (Kimball-style dims and facts) — a genuine second consumption path, not dead code (see Section 5) | SQL |
| `Bruin/assets/reporting/` | Dashboard-facing marts — the layer `streamlit/services/marts.py` actually queries | SQL |
| `streamlit/core/` | Config, constants, contracts (schema validation), filters, state, theme, layout | Python |
| `streamlit/components/` | Reusable UI fragments (trust strip, status, KPIs); two files (`charts.py`, `tables.py`) are dead code | Python |
| `streamlit/services/` | BigQuery client + six cached query functions bridging reporting marts to pages; one file (`freshness.py`) is dead code | Python |
| `streamlit/pages/` | Eight dashboard pages | Python |
| `infra/` | Terraform (GCS, BigQuery, IAM modules) plus two shell scripts for setup/verification | Terraform + Bash |
| `scripts/` | Local ingestion helpers — one real OONI downloader/ETL, one synthetic Lumen data generator, one PowerShell OONI sync script | Python + PowerShell |
| `tests/` | A single test file covering the Streamlit contract-validation helper only | Python (pytest) |

## 3. Dependency Graph

Dependencies below are drawn from each Bruin asset's declared `@bruin` `depends:` header. This is a declared graph, not a verified one — Section 6 identifies at least one place where declared dependencies and actual SQL references appear to diverge, which matters enough to call out before treating this graph as ground truth.

**OONI path (single, coherent):**
`load.ooni_to_gcs` → `stg.ooni_measurements` → `{stg.ooni_dns_observations, stg.ooni_tcp_observations, stg.ooni_tls_observations, stg.ooni_http_observations}` → `int.ooni_experiment_results` → `int.ooni_signals` → (via `marts.fact_ooni_censorship_signals`) → `features.protocol_daily_signals` → `intelligence.protocol_signal_regimes` + `intelligence.protocol_lag_relationships` → `intelligence.protocol_relationships` → `reporting.mart_protocol_interference_trends`, `reporting.protocol_repression_correlation_mart`, `reporting.asn_behavior_profile_mart`.

**ACLED path A — the sophisticated, stateful path:**
`load.acled_conflict_events` → `stg.acled_conflict_events` → `int.acled_event_classification` (assigns both `classification_confidence` and, separately, `methodology_risk_level`) → `features.acled_pressure_signals` (per-family baseline gating, calendar spine, statistical guardrails) → `intelligence.acled_pressure_regimes` (1,768-line stateful regime engine, orchestrated week-by-week by `Bruin/scripts/historical_initializer/backfill_acled_pressure_regimes.py`, gated by `intelligence.country_initialization_status` and exposed cleanly via `intelligence.country_readiness`).

**ACLED path B — the legacy, simple path:**
`stg.acled_conflict_events` → `marts.fact_country_pressure_daily` → `reporting.mart_political_stress_windows` (this mart also pulls in Google Transparency and Lumen pressure via `int.google_pressure_periodized` and `stg.lumen_requests`).

**Google Transparency path:** `stg.google_transparency_requests` + `stg.google_transparency_detailed` → `int.google_pressure_periodized` → `marts.fact_country_pressure_daily` and `marts.fact_takedown_activity` → `marts.fact_takedown_pressure_daily`.

**Lumen path:** `stg.lumen_requests` → `int.lumen_pressure_daily` → `marts.fact_takedown_activity`. The data entering at `stg.lumen_requests` is currently synthetic — see Section 4.

**Dashboard consumption:** `streamlit/services/marts.py` queries exactly four reporting marts — `reporting.mart_political_stress_windows`, `reporting.mart_protocol_interference_trends`, `reporting.protocol_repression_correlation_mart`, `reporting.asn_behavior_profile_mart` — plus a direct `CROSS JOIN`-based query for the Finance Bill incident report (Section 6).

## 4. Evidence Flow and the Lumen Provenance Gap

The intended evidence flow, realized well in the OONI path and in ACLED path A, is: raw observation → labeled/classified with an explicit confidence value → statistically guarded feature → inferred regime or state. This shape is not universal across the codebase (Section 6 returns to this).

The most serious finding in this assessment concerns Lumen: `scripts/lumen_parquet.py` does not ingest real Lumen Database exports. It generates 5,000 synthetic rows (`np.random.seed(42)`, IDs of the form `LUMEN-00000`, fabricated countries weighted 75% Kenya, fabricated senders/recipients/reasons/counts) and this synthetic data flows, unflagged, through `stg.lumen_requests` → `int.lumen_pressure_daily` → `marts.fact_takedown_activity` and into `marts.fact_country_pressure_daily`, which feeds the dashboard's national pressure score. There is no `is_synthetic` or `data_source_authenticity` column anywhere in this chain. Nothing downstream — including a report generated six months from now — can structurally distinguish a real evidentiary finding from a placeholder one. This is treated at greater length, with severity ranking, in the Methodology Consistency Review.

## 5. The Marts/Dims + Facts Branch Is Real, Not Dead Code

An open question worth resolving explicitly: `marts/dims/` and `marts/facts/` looks, on first inspection, like a legacy or abandoned dimensional-model exercise sitting alongside the "real" reporting layer. It is not. Reading `reporting/political_stress_windows_mart.sql` directly confirms `marts.fact_country_pressure_daily` (filtered to `iso2 = 'KE'`) is joined into the dashboard's composite national pressure score. This is a live, load-bearing dependency, not dead weight — but the two accompanying documents that describe this dimensional model in prose (`docs/data-modelling.md`, `docs/civil-liberties-reporting-playbook-Kenya.md`) describe a different, more elaborate, unimplemented version of it (a full Kimball star schema with a "Civil Liberties Risk Index" formula that does not exist anywhere in the actual SQL). Treat the code as real and the two documents describing it as aspirational drafts — see the Repository Documentation Plan for the recommended disposition of those files.

## 6. Resolved: Only One ACLED Path Is Actually Wired to the Product (confirmed 2026-07-04)

This was flagged as an open question in the original assessment and has since been verified by direct inspection of every reporting asset's SQL body, not just declared `depends:` headers. Confirmed: no `reporting/*` asset references `intelligence.acled_pressure_regimes` or `intelligence.country_readiness`, in header or body. `political_stress_windows_mart.sql` and `protocol_repression_correlation_mart.sql` both source ACLED pressure from `marts.fact_country_pressure_daily`, which was traced one level further and reads directly from `stg.acled_conflict_events` — bypassing `int.acled_event_classification`, `features.acled_pressure_signals`, and `intelligence.acled_pressure_regimes` entirely. The system's single most sophisticated piece of engineering — a stateful, persistence-aware, backfill-orchestrated regime classifier with dedicated country-readiness gating — is confirmed not to be the thing the dashboard's pressure score is built from. The dashboard's national pressure score comes entirely from ACLED path B: a direct aggregation with none of path A's confidence split, statistical guardrails, or regime persistence.

This was Step 0 of the Implementation Roadmap for exactly the reason stated originally: it changed the shape of everything downstream, and now that it is closed, Step 3 has a specific decision to make rather than an investigation to run — wire path A in, replace path B with it, or formally deprecate path A.

## 7. Methodology Versioning Flow

Four independent version-tag constants exist in the codebase — `classification_methodology_version` and `severity_methodology_version` (in `int.acled_event_classification.sql`), `feature_version` (features layer), and `regime_methodology_version` / `METHODOLOGY_VERSION = "ACLED_REGIME_ENGINE_V1"` (split between the SQL asset and `backfill_acled_pressure_regimes.py`, with a comment noting they must be kept in sync manually). No governance table centralizes these; each is a literal maintained by hand in its own file. This is consistent with, and adds a concrete example to, the "Methodology Governance Layer" gap already identified in the product strategy documents and repeated in the Technical Debt Inventory.

## 8. Documentation Gaps

- The top-level `README.md`'s repository-structure diagram is stale: it lists only one of eight Streamlit pages and omits several `core/` and `components/` modules that are actually imported and used.
- `docs/data-modelling.md` and `docs/civil-liberties-reporting-playbook-Kenya.md` describe a Kimball/CLRI architecture that does not match the implemented reporting layer's actual vocabulary, and `data-modelling.md` additionally contains a duplicated section header and leftover reviewer/LLM commentary that reads as an editorial accident, not intentional content.
- `docs/readme1_1.md` is an earlier, more elaborate draft of the top-level README with a more extensive ethics and responsible-use section than what survived into the current README.
- `streamlit/services/freshness.py` carries an internal header comment (`# utils/validate.py`) that does not match its actual filename or location, and references a schema vocabulary that belongs to the aspirational dimensional model rather than the real reporting marts — further evidence it is a leftover from an earlier architecture iteration.

## 9. Module Maturity Summary

| Module | Maturity | Test Coverage | Debt Level |
|---|---|---|---|
| OONI pipeline (staging → reporting) | High — internally consistent, independently praised in prior audits and confirmed here | None at the logic level | Low-Medium |
| ACLED path A (classification → regime engine) | High engineering sophistication, but possibly unwired (Section 6) | None at the logic level | Medium (pending verification) |
| ACLED path B (legacy aggregation) | Low — no confidence model, no guardrails | None | Medium |
| Google Transparency path | Low-Medium — functional, minimal guardrails | None | Low-Medium |
| Lumen path | Not applicable — data is synthetic | None | Critical (provenance, not logic) |
| Confidence/measurement-quality dimensions | High — the strongest conceptual asset in the codebase | Structural only | Low |
| Streamlit core/contracts.py | High — small, tested, well-scoped | Yes (the only tested module) | Low |
| Streamlit pages 1/2/5/6 | Medium — structurally uniform, minimal defensive coding | None | Low-Medium |
| Streamlit page 3 | High — genuinely defensive, closest in quality to pages 4/7 | None | Low |
| Streamlit services/marts.py | Medium — functional, contains the CROSS JOIN bug and one trivial duplicate function | None | Medium-High |
| infra/ (Terraform + scripts) | Medium — functional, some credential-hygiene and least-privilege gaps | None (not applicable) | Medium |
| scripts/ (local ingestion) | Low-Medium — functional but Windows-only, manual resume state | None | Medium |
