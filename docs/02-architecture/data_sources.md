# CLIO Data Sources

Status: rewritten 2026-07-12, replacing the archived pre-restructure version at `Archive/data_sources.md` (TD-23). Grounded directly in the live Bruin DAG (`Bruin/assets/**`, verified via `bruin validate` and each asset's own `depends:` field) and `docs/07-governance/licensing-compliance-register.md`, not restated from memory. See `architecture-assessment.md` for the broader system design; this document covers sources only.

Four sources are actually ingested and live in the pipeline today. Four more are recommended by ADR-0003 but **not yet ingested** — they are listed at the bottom, explicitly marked as not-yet-live, so this document cannot be misread as claiming broader coverage than exists.

## Live sources

### OONI (Open Observatory of Network Interference)

- **What it is**: crowdsourced, probe-collected network-measurement data — DNS, TCP, TLS, and HTTP-layer tests that detect blocking, tampering, and interference.
- **Grain**: measurement-level (one row per probe test result), the finest grain of any source in the pipeline.
- **Role in CLIO**: primary censorship-measurement evidence; the only source ADR-0003 and the 2026-07-06 near-real-time architecture note class as genuinely capable of continuous refresh (probes submit continuously; nothing currently schedules the pipeline to consume that continuously — see `implementation-roadmap.md` Step 7).
- **Licensing**: CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike), verified from `github.com/ooni/license` and OONI's own Data Policy page. NonCommercial only; attribution required per license Section 3(a). See `docs/07-governance/licensing-compliance-register.md` for full detail — verify that register is still current before relying on this summary for a commercial-use decision.
- **Ingestion path**: `Bruin/assets/ingest/ooni_raw.py` (raw) → `Bruin/assets/load/ooni_to_gcs.py` → `stg.ooni_measurements` → four protocol-specific staging assets (`stg.ooni_dns_observations`, `stg.ooni_tcp_observations`, `stg.ooni_tls_observations`, `stg.ooni_http_observations`) → `int.ooni_experiment_results` → `marts.fact_ooni_censorship_signals` → `features.protocol_daily_signals` → the protocol-intelligence and pressure-attribution layers.
- **Known limitation**: OONI's Python ingest hardcodes `PROBE_CC = "KE"` (`ooni_raw.py`), unlike ACLED and Google Transparency which ingest broadly and filter in SQL — logged as TD-60, not yet fixed (untestable in this environment since re-ingestion isn't runnable here).

### ACLED (Armed Conflict Location & Event Data Project)

- **What it is**: coded conflict and protest event data — who did what, where, when, with what outcome.
- **Grain**: two distinct grains live in the pipeline, and they must not be conflated. `int.acled_event_classification` and the reporting-layer `mart_pressure_attribution_conflict_drivers` operate at true event grain. Everything feeding the regime engine operates at **weekly aggregate** grain (`features.acled_pressure_signals`, `intelligence.acled_pressure_regimes` — both keyed on `week_start_date`), which is ACLED's own real coding cadence for the regime classification use case, not an artificially coarsened view.
- **Role in CLIO**: conflict-pressure evidence, feeding both the categorical regime classifier (Path A) and, at ~75-80% weight, the continuous composite pressure score.
- **Licensing**: a contractual (not Creative Commons) license — free for non-commercial use with registration, a separate paid Commercial License Agreement required for commercial use. Carries a specific, broad prohibition on creating a "functional substitute" for ACLED's own products, applying regardless of commercial status. See the governance register for the full detail, including required attribution elements (access date, filters/subset used, manipulation performed) beyond a generic source credit.
- **Ingestion path**: `Bruin/assets/ingest/raw_acled_aggregated.py` (raw) → `Bruin/assets/load/acled_conflict_events.py` → `stg.acled_conflict_events` → `int.acled_event_classification` → `features.acled_pressure_signals` → `intelligence.acled_pressure_regimes` (the regime engine — see `erd-lineage.md` for its EXECUTION CONTRACT precondition) → broadcast into `marts.fact_country_pressure_daily`'s `regime_*` columns.
- **Known limitation**: `marts.dim_dates`' date spine (and therefore `fact_country_pressure_daily` and everything downstream of it) is bounded to 2023-06-01–2025-06-30, even though `intelligence.acled_pressure_regimes` itself is not bound by `dim_dates` and covers 1997-01-11 through 2026-03-14 live.

### Google Transparency Report

- **What it is**: Google's own published statistics on government content-removal requests and platform compliance.
- **Grain**: semiannual aggregate. ADR-0003 classifies this source **Contextual/Backdrop** — a legitimate pipeline input, computed and reported strictly at its own six-month grain, feeding narrative context (e.g. "formal legal-removal pressure on this platform rose X% this half") rather than any incident-level score or composite-score input finer than that. It must never be broadcast down to a weekly or daily grain the way ACLED's regime engine honestly broadcasts a real weekly value — Google's real grain is six months, and treating it as finer would repeat the mistake already caught and fixed at TD-40.
- **Role in CLIO**: platform/legal removal-pressure signal, ~20-25% weight in the composite pressure score, and a named driver in the pressure-attribution decomposition (ADR-0006).
- **Licensing**: **Cannot Determine.** No source-specific reuse or redistribution license was located despite direct search (logged as TD-64, still open) — Google's general Terms of Service govern the service broadly but don't speak specifically to reuse of published transparency statistics. Treat as attributed, non-commercial input pending clarification, consistent with ADR-0003's grain-based constraint.
- **Ingestion path**: `Bruin/assets/ingest/google_transparency_requests.py` and `google_transparency_detailed.py` (raw) → respective `load/` assets → `stg.google_transparency_requests`, `stg.google_transparency_detailed` → `int.google_pressure_periodized` → `marts.fact_country_pressure_daily`'s `platform_pressure_score` and `reporting.mart_pressure_attribution_platform_drivers`.

### Lumen Database — synthetic, benched

- **What it is intended to be**: a database of legal takedown/removal notices (the real Lumen Database, `lumendatabase.org`).
- **What it actually is today**: entirely synthetic. `scripts/lumen_parquet.py` fabricates rows via `np.random.seed(42)` — no real Lumen export has ever been ingested. A real, per-row `is_synthetic` flag (TD-01, resolved 2026-07-05) originates at `stg.lumen_requests` and propagates through the pipeline via `LOGICAL_OR` at every grain change.
- **Current status**: **benched.** ADR-0004 formally dropped Lumen's term from `composite_pressure_score` entirely — the live formula is `conflict_pressure_score * 0.75 + platform_pressure_score * 0.25`, with no Lumen/legal term. TD-46 (resolved) removed the now-inapplicable synthetic-data disclosure banners from pages 1, 6, and 7, since nothing on those pages remained Lumen-derived once the reweighting shipped. `marts.fact_takedown_activity` and `marts.fact_takedown_pressure_daily` still materialize from the synthetic data (Branch B/A distinction — see TD-01), but nothing in the live dashboard reads them today.
- **Licensing**: moot while synthetic. If a real Lumen export replaces the fabricated data, its licensing terms would need their own review before this section's status changes.
- **Ingestion path**: `Bruin/assets/ingest/lumen_raw.py` → `Bruin/assets/load/lumen_requests.py` (declares `depends: raw.lumen_requests`, but its actual code reads a disconnected local file — TD-42, a known DAG-lineage mismatch) → `stg.lumen_requests` → `int.lumen_pressure_daily` (dead-end branch, zero consumers) and directly into `marts.fact_takedown_activity` (the branch that materializes, though nothing downstream of it reads live).

## Not yet ingested — recommended by ADR-0003, not live

Do not read these as current pipeline inputs. Status per ADR-0003's evaluation tiers:

| Source | Tier | Status |
|---|---|---|
| STOP / Access Now (#KeepItOn) | Core | Not ingested. Feasibility confirmed (CC BY 4.0, permissive; unauthenticated CSV export; Kenya rows independently corroborate CLIO's own tracked ASNs). A courtesy check with Access Now's methodology contact about scraping cadence is recommended before production ingestion, not yet performed. |
| CPJ (killed/attacked journalists) | Core, downgraded | Blocked pending direct resolution with CPJ. Licensed CC BY-NC-ND 4.0 (NoDerivatives) — a materially poor fit for CLIO's derivative-composite model, discovered after the original Core classification. No further engineering investment until CPJ (`press@cpj.org`) confirms CLIO's intended use is permitted. |
| CPJ (imprisonment census) | Secondary | Not ingested; needs explicit grain handling on ingestion (annual snapshot historically, dynamic tracking only since 2025) before being treated as continuous data. |
| IODA (CAIDA / Georgia Tech) | Secondary | Not ingested. Genuinely independent instrumentation from OONI (BGP routing, darknet background radiation, active probing), but answers substantially the same reachability question — a cross-method confidence booster on OONI's findings, not a new axis of evidence. |
| Freedom House (Freedom on the Net) | Optional | Not ingested. Annual, country-level; real value as a once-a-year manual directional cross-reference, zero incident-level usefulness. |
| CIPESA | Rejected as pipeline source | Real, credible regional analysis, but periodic and qualitative — not a structured incident-dated dataset. Legitimate role is a human report-writer's citation, entirely outside the SQL pipeline. |

See `docs/02-architecture/adr/0003-evidence-architecture-and-foundation-datasets.md` for the full evaluation reasoning behind each tier.
