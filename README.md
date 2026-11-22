# CLIO — Civil Liberties Intelligence Observatory

> A historical observatory that shows internet-measurement results (OONI), ACLED's weekly aggregated conflict and protest data, and platform takedown-request counts (Google Transparency Report) side by side, and derives confidence-qualified, partly experimental indicators of civil-liberties pressure from them. The data is historical: OONI measurements run to June 2025 and ACLED weeks to the week of 2026-03-14. Kenya is the current pilot country — the methodology is built to generalize, not to stay Kenya-only.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Bruin](https://img.shields.io/badge/Bruin-Orchestration-FF9900?style=for-the-badge)](https://getbruin.com/)
[![BigQuery](https://img.shields.io/badge/BigQuery-Warehouse-4285F4?style=for-the-badge&logo=googlebigquery&logoColor=white)](https://cloud.google.com/bigquery)
[![Streamlit](https://img.shields.io/badge/Streamlit-Intelligence%20Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Terraform](https://img.shields.io/badge/Terraform-Infrastructure-844FBA?style=for-the-badge&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Bruin%20Asset%20Runtime-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Parquet](https://img.shields.io/badge/Parquet-Columnar%20Data-005571?style=for-the-badge)](https://parquet.apache.org/)

## Scope

CLIO (Civil Liberties Intelligence Observatory) is Kenya-**piloted**, not Kenya-only. It shows network measurements, conflict indicators, and platform transparency data side by side, through governed BigQuery marts and a Streamlit dashboard. Legal-pressure (Lumen) data is not used: the Lumen figures in the pipeline are synthetic and are excluded from all live output. Country, dataset, and date-range settings are pipeline configuration variables rather than hardcoded assumptions, so the same methodology is designed to extend to additional countries as they're onboarded.

Kenya's data coverage is uneven across sources: ACLED's weekly aggregated conflict data in the pipeline runs from 1997 to the week of 2026-03-14, while the OONI/Google-Transparency-driven daily marts (the ones behind the composite pressure index) are bounded to a fixed June 2023 – June 2025 date-dimension window. The pipeline is not ingesting new data on a schedule; the dashboard shows a historical backfill, not live monitoring. The Finance Bill 2024 protests are the project's main case study to date (see "Case Study" below); it reports a null result for a method that has since been retired, and is not a validation of CLIO's indicators.

The platform is designed to help examine questions such as:

- Did OONI measurement anomalies rise during political stress windows?
- Which protocols' tests looked anomalous against their own baseline?
- On which networks did probes record the most anomalous measurements? (This describes measurements, not what an operator did.)
- Did pressure indicators move together around the Finance Bill 2024 period?
- Which signals are statistically weak because of sparse data, low confidence, or zero variance?

The platform derives civil-liberties pressure indicators from historical data; it does not perform live operational surveillance.

## Why This Matters

Digital repression is rarely observable through one clean dataset. It can appear as protocol anomalies, DNS or TCP failures, platform removals, legal pressure, protest dynamics, and inconsistent measurement coverage.

This project treats censorship analysis as an observability and inference problem. It places fragmented civil-liberties indicators side by side and derives auditable statistical outputs from them, while preserving guardrails that prevent weak or sparse evidence from being overstated.

The result is a reference architecture for civil-liberties observability and analytical inference; several of its indicators are experimental or retired, and none has been validated.

---

## Case Study: Finance Bill 2024

CLIO's main case study looks at Kenya's June–July 2024 Finance Bill protest period. The dashboard page reports what the retired rolling correlation between OONI protocol anomalies and the composite pressure index (experimental; ~75% ACLED weekly conflict data, ~25% Google Transparency, no OONI input) showed for that window: no protocol-day row reached the moderate or strong threshold, a null result for that method, which CLIO has since retired (ADR-0016). The page also notes that the 25 June 2024 disruption was mainly a drop in connectivity, which OONI's app tests largely cannot see, so the page cannot assess it. An earlier version of the report cited a same-day spike in high-confidence DNS-blocking signals concentrated on Signal as OONI evidence for the window; it was retracted in July 2026, because a classification bug had counted Signal's own health-check hostname (`uptime.signal.org`, which always resolves to loopback) as blocking. With the bug fixed, the count for that day is zero. Separately, ACLED's experimental regime classifier (computed in the pipeline; its labels are not shown on the dashboard until they are validated) labels the week of the Bill's May 11, 2024 tabling MOBILISATION and the week Parliament was stormed CRISIS; that was checked against windows chosen after the fact, which is not validation, and the classifier has known misses (see `docs/02-architecture/methodology.md`).

The page's figures were re-checked against BigQuery when it was written. Lumen/legal-pressure data is deliberately excluded from the report, since it remains synthetic pending a real Lumen export — see "Data Licensing & Attribution" below. The full analysis is built as `streamlit/pages/finance_bill_2024_incident_report.py`; see "Hosted Dashboard" below for current access status.

---

## Dashboard Showcase

### Welcome / What CLIO Is

![](docs/images/screenshot-welcome.png)

What CLIO is and isn't — an observatory showing ACLED's weekly aggregated conflict data, OONI internet-measurement data, and platform takedown-request counts side by side, with confidence-qualified indicators derived from them, currently piloted in Kenya.

---

### Finance Bill 2024 (retired method)

![](docs/images/screenshot-finance-bill-2024-incident-report.png)

A case study of what the retired rolling-correlation method showed for the June–July 2024 Finance Bill protest period — a null result for that method — and why the method was retired (ADR-0016).

<details>
<summary>Six more dashboard pages</summary>

### National Stress Observatory

![](docs/images/screenshot-national-stress-observatory.png)

Country-level view of the composite pressure index (experimental), driven primarily by ACLED conflict intensity with platform-pressure signals alongside it, shown as an experimental value that has not been validated, with OONI protocol-escalation load and OONI weekly anomalous/blocked rates shown alongside (not combined into it). Pressure band labels (MODERATE/ELEVATED/SEVERE) and ACLED regime labels are hidden until they are validated against a pre-specified list of events.

### Pressure Attribution

![](docs/images/screenshot-pressure-attribution.png)

Splits CLIO's composite pressure index (experimental) for a chosen date into its two arithmetic inputs (ACLED weekly conflict intensity, Google Transparency platform pressure), with that day's OONI measurements shown alongside rather than as a composite input. This shows how the number was derived; it does not explain why conditions were as they were.

### Protocol Anomalies vs. Composite Index

![Protocol Anomalies vs. Composite Index page](docs/images/screenshot-protocol-repression-correlation-engine.png)

Compares protocol-level OONI anomaly measures with the composite pressure index: the rolling correlation between them and the measures derived from it — all labelled as retired (ADR-0016) and no longer used for findings — and how far the two series diverge; a second tab shows every protocol's values on one chosen date.

### Protocol Intelligence

![](docs/images/screenshot-protocol-intelligence.png)

Protocol-level regime classification for DNS, HTTP, TCP, and TLS — stress heatmap, per-protocol regime evolution, and a ranking on the latest date in range in one tab; observation-reliability composition and the per-app/per-protocol-layer blocking breakdown (Telegram vs. WhatsApp vs. Signal vs. Psiphon) in the other. Consolidates what were two separate, largely-duplicative pages (TD-16) into one, removing the duplication rather than just relocating it.

### Network Measurement Profiles (ASN)

![Network Measurement Profiles (ASN) page](docs/images/screenshot-asn-behavioral-intelligence.png)

Per-network (ASN) measurement profiles: an experimental measurement anomaly score and evidence reliability for OONI probes on each network. A score describes how often tests from probes on that network looked anomalous; it does not show what the network operator did, since blocking seen from a network can come from upstream or transit networks or the destination service itself.

### Methodology & Statistical Guardrails

![](docs/images/screenshot-methodology-statistical-guardrails.png)

Methodology view documenting how sparse data, confidence weighting, variance checks, and rolling baselines constrain interpretation before signals enter intelligence outputs.

</details>

---

## Hosted Dashboard

Streamlit deployment (the app is hosted; the data it shows is historical — OONI to June 2025, ACLED weeks to 2026-03-14):

https://civil-lliberties-intelligence-observatory-toafjdj5xoc.streamlit.app/

A dedicated Welcome page orients first-time visitors — what CLIO is, a one-line guide to every page, a suggested reading order by role (journalist/NGO/legal reader vs. methodology reviewer), and the key caveats stated upfront rather than discovered page-by-page.

Key intelligence surfaces (7 pages beyond Welcome):

- National Stress Observatory
- Protocol Intelligence (regime classification, stress heatmap, per-app blocking breakdown)
- Protocol Anomalies vs. Composite Index (TD-98: two tabs — Protocol Drill-Down, Date Snapshot — merged from the former separate Suppression Event Explorer page)
- Network Measurement Profiles (ASN)
- Finance Bill 2024 (retired method)
- Methodology & Statistical Guardrails
- Pressure Attribution

---

## How Bruin Is Used

- Python ingestion assets
- SQL transformation assets
- Asset dependency orchestration
- Feature and intelligence materialization
- Validation and quality checks
- Historical partition execution
- BigQuery-backed marts
- Streamlit-facing reporting assets

---

## Architecture Overview

```mermaid
flowchart LR
    Sources["OONI, ACLED, Google Transparency, Lumen-style data"]
    Ingest["Python ingestion and Parquet normalization"]
    Warehouse["BigQuery staging, facts, dimensions, features"]
    Intelligence["ACLED conflict-regime classification, protocol regimes, lag relationships, pressure correlation"]
    Reporting["Dashboard-facing reporting marts"]
    Contracts["Streamlit query services and dataframe contracts"]
    Dashboard["Streamlit intelligence observatory"]

    Sources --> Ingest
    Ingest --> Warehouse
    Warehouse --> Intelligence
    Intelligence --> Reporting
    Reporting --> Contracts
    Contracts --> Dashboard
```

Design principles:

- Preserve source data as re-runnable analytical inputs.
- Separate ingestion, staging, features, intelligence, and reporting.
- Apply statistical guardrails before surfacing intelligence claims.
- Preserve mart versioning and snapshot metadata in the dashboard.
- Normalize BigQuery date and timestamp types before dashboard validation.
- Treat the system as historical reconstruction, not live surveillance.

**What DuckDB actually does here:** it is not a local analytics/querying layer a developer runs ad hoc — it's the connection Bruin's own CLI uses to execute this pipeline's `type: python` ingestion assets (the `duckdb-parquet` connection declared in `.bruin.yml`/`Bruin/pipeline.yml`), most visibly at the raw→load Parquet boundary (`raw.acled_conflict_events`, `raw.ooni_conflict_measurements`, and similar assets). Each of those assets runs inside its own ephemeral `uv`-managed environment that Bruin builds per `Bruin/requirements.txt` — a separate dependency surface from the top-level `pyproject.toml`/`uv.lock`, which governs local dev tooling (tests, Streamlit, `scripts/`) instead. Confirmed empirically 2026-08-02: `bruin run` against a `duckdb-parquet`-connected asset installs and uses whatever version `Bruin/requirements.txt` pins, independent of what (if anything) is installed in the top-level Python environment.

## Engineering Reliability Controls

| Control                              | Implementation                                                                                                                                                    |
| ------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Contract-enforced schema validation  | `streamlit/core/contracts.py` validates required columns, expected dtypes, and non-null fields for dashboard-facing marts.                                        |
| Environment portability              | `.env.example`, `streamlit/core/config.py`, `TARGET_ENV`, `BRUIN_ENV`, `GOOGLE_CLOUD_PROJECT`, country, date, and dataset settings support runtime configuration. |
| CI-backed verification               | `.github/workflows/lint.yml`, `.github/workflows/tests.yml`, and `tests/test_contracts.py` provide lint and contract-test entry points.                           |
| Query normalization                  | `streamlit/services/bq.py` normalizes BigQuery `DATE` and timestamp outputs before page rendering.                                                                |
| Sparse-window resilience             | Mart fetch contracts allow guarded statistical nulls where sparse history or zero variance makes inference unsafe.                                                |
| Dashboard contract safety            | `streamlit/services/marts.py` centralizes mart queries and validation before page code consumes results.                                                          |
| Service-layer separation of concerns | BigQuery execution, mart access, dataframe validation, reusable components, and page rendering are separated.                                                     |
| Deployment portability               | Dependency pins, `.env.example`, Terraform modules, and Codespaces reinstall commands reduce environment-specific breakage.                                       |

These controls are intended to keep the observatory stable across local development, Codespaces, and cloud-backed BigQuery execution.

## Repository Structure

Generated from the repository's tracked files (`git ls-files`), not the local working tree — some `docs/` subdirectories (internal planning and governance material) are deliberately excluded from the public repository via `.gitignore` and will not appear on a fresh clone.

```text
.
|-- Bruin/
|   |-- README.md
|   |-- pipeline.yml
|   |-- requirements.txt
|   |-- config/
|   |   `-- observatory.yml
|   |-- scripts/
|   |   |-- agreement_check/          # OONI classification agreement-check panel (ADR-0013,
|   |   |                             # workflow_dispatch only -- cron permanently disabled)
|   |   |-- country_literal_check/    # CI guard against hardcoded country literals
|   |   |-- historical_initializer/   # ACLED regime engine backfill driver
|   |   |-- safe_run/                 # Cascade-safe materialize wrapper (ADR-0012) -- the
|   |   |                             # only sanctioned way to run `bruin run` in this repo
|   |   |-- staleness_check/          # Materialization-staleness CI guard
|   |   `-- steady_state/             # Resolves and runs the single next unprocessed
|   |                                 # ACLED regime week (TD-38) -- never bare `bruin run`
|   `-- assets/
|       |-- ingest/          # Raw source ingestion assets (OONI, ACLED, Google, Lumen)
|       |-- load/            # GCS and BigQuery external table loaders
|       |-- staging/         # Source normalization models
|       |-- intermediate/    # Cross-source preparation models
|       |-- marts/
|       |   |-- dims/        # Conformed dimensions
|       |   `-- facts/       # Analytics-ready fact tables
|       |-- features/        # Model-ready protocol and pressure features
|       |-- intelligence/    # Regime classification and relationship inference
|       `-- reporting/       # Dashboard-facing marts, incl. pressure-attribution
|-- .devcontainer/
|   |-- devcontainer.json
|   `-- setup-gcp-tooling.sh   # Installs gcloud/bq/bruin tooling on every Codespace rebuild
|-- .env.example                # Portable environment variable template
|-- .github/
|   `-- workflows/
|       |-- lint.yml                    # CI lint scaffolding
|       |-- tests.yml                   # CI test scaffolding
|       |-- gcp-auth.yml                # Workload Identity Federation auth check
|       |-- staleness-check.yml         # Materialization-staleness CI job
|       |-- country-literal-check.yml   # Hardcoded-country-literal CI guard
|       `-- ooni-agreement-check.yml    # OONI agreement-check panel (ADR-0013,
|                                       # workflow_dispatch only -- cron permanently disabled)
|-- .vscode/
|   |-- mcp.json
|   `-- settings.json
|-- docs/
|   |-- 02-architecture/     # ADRs, architecture assessment, decision log, TD inventory,
|   |   |                    # data-modelling.md, data_sources.md, erd-lineage.md
|   |   `-- adr/             # Accepted architecture decision records
|   |-- 03-development/      # Coding standards, testing strategy, documentation standards
|   `-- images/              # Dashboard screenshots referenced by this README's
|       |                    # Dashboard Showcase section (moved from repo root)
|       |-- screenshot-asn-behavioral-intelligence.png
|       |-- screenshot-finance-bill-2024-incident-report.png
|       |-- screenshot-methodology-statistical-guardrails.png
|       |-- screenshot-national-stress-observatory.png
|       |-- screenshot-pressure-attribution.png
|       |-- screenshot-protocol-intelligence.png
|       |-- screenshot-protocol-repression-correlation-engine.png
|       `-- screenshot-welcome.png
|-- Archive/                 # Superseded docs, kept (not deleted) with an explanation
|   `-- README.md            # of what each archived file was and what replaced it
|-- infra/
|   |-- main.tf
|   |-- provider.tf
|   |-- variables.tf
|   |-- terraform.tfvars
|   |-- setup-gcp.sh
|   |-- verify-gcp.sh
|   `-- modules/
|       |-- bigquery/
|       |-- gcs/
|       `-- iam/
|-- llm_report_writer/       # LLM-assisted narrative report drafting + verification
|   |                        # over CLIO's own already-computed marts (ADR-0010) --
|   |                        # never a new-fact source, grounded/completeness-checked
|   |-- report_writer_openai.py
|   |-- template_writer.py
|   |-- deterministic_analysis.py
|   |-- claim_check.py
|   |-- causal_language_check.py
|   |-- coherence_check.py
|   |-- completeness_check.py
|   |-- style_lint.py
|   |-- verify_report.py
|   |-- bigquery_lookup.py
|   |-- run_report.py
|   |-- run_baseline_comparison.py
|   |-- run_live_windows.py
|   |-- requirements.txt
|   |-- README.md
|   |-- fixtures/
|   `-- tests/
|-- logs/
|   `-- query_log.sql        # Tracked but empty; TD-32 recommends deletion (not yet done)
|-- scripts/
|   |-- download_ooni.ps1
|   |-- local_ingest_ooni.py
|   |-- lumen_parquet.py
|   `-- ooni_api_validation.py     # Live cross-check against OONI's own API (rate-limited, disk-cached)
|-- streamlit/
|   |-- app.py                # Thin st.navigation entrypoint - pages own their
|   |   |                     # title/icon via st.Page(), not filename parsing
|   |-- requirements.txt
|   |-- .streamlit/
|   |   `-- config.toml
|   |-- pages/                # Welcome + 7 pages: National Stress Observatory,
|   |   |                     # Protocol Intelligence (consolidated, TD-16),
|   |   |                     # Protocol Anomalies vs. Composite Index (two tabs,
|   |   |                     # merged with the former Suppression Event Explorer
|   |   |                     # page, TD-98), Network Measurement Profiles (ASN), Finance
|   |   |                     # Bill 2024 (retired method), Methodology &
|   |   |                     # Statistical Guardrails, Pressure Attribution
|   |-- services/
|   |   |-- bq.py
|   |   |-- marts.py
|   |   `-- freshness.py
|   |-- core/
|   |   |-- config.py
|   |   |-- constants.py
|   |   |-- contracts.py
|   |   |-- filters.py
|   |   |-- state.py
|   |   `-- theme.py
|   |-- components/
|   |   |-- charts.py
|   |   |-- kpis.py
|   |   |-- status.py
|   |   `-- trust.py          # ACLED/OONI attribution footer
|   `-- assets/
|       |-- annotations/
|       `-- methodology/
|           `-- thresholds.yml
|-- tests/
|   |-- fixtures/
|   |   |-- acled_regimes_golden/                                  # Finance Bill 2024, Jan-Feb 2008
|   |   |-- ooni_dnscheck_bootstrap_classification/
|   |   |-- ooni_signal_probe_version_discard/
|   |   |-- ooni_weekly_golden/
|   |   |-- ooni_whatsapp_endpoints_blocked_count_removed/
|   |   |-- ooni_whatsapp_registration_accessible_classification/
|   |   `-- ooni_whatsapp_web_accessible_classification/
|   |-- test_contracts.py                    # Dashboard contract validation tests
|   |-- test_acled_pressure_regimes_golden.py
|   |-- test_ooni_confirmed_guard.py
|   |-- test_ooni_dns_bogon_classification.py
|   |-- test_ooni_dns_canary_classification.py
|   |-- test_ooni_dnscheck_bootstrap_failed_classification.py
|   |-- test_ooni_signal_probe_version_discard.py
|   |-- test_ooni_tls_failure_evidence_tiering.py
|   |-- test_ooni_tls_handshake_success_fix.py
|   |-- test_ooni_tls_root_ca_exclusion.py
|   |-- test_ooni_weekly_aggregation_golden.py
|   |-- test_ooni_whatsapp_endpoints_blocked_count_removed.py
|   |-- test_ooni_whatsapp_registration_accessible_classification.py
|   `-- test_ooni_whatsapp_web_accessible_classification.py
|-- CLAUDE.md
|-- LICENSE
|-- pyproject.toml
|-- runtime.txt
|-- uv.lock
`-- README.md
```

---

## Quickstart

### 1. Clone

```bash
git clone https://github.com/Sanjomwa/Civil-Liberties-Intelligence-Observatory.git
cd Civil-Liberties-Intelligence-Observatory
```

### 2. Create a Python Environment

Using standard `venv`:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir -r streamlit/requirements.txt
```

Using `uv`:

```bash
uv venv
source .venv/bin/activate
uv pip install -r streamlit/requirements.txt
```

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir -r streamlit\requirements.txt
```

### 3. Dependency Compatibility

`streamlit/requirements.txt` pins NumPy below 2.0 to avoid ABI conflicts with `pyarrow`/`google-cloud-bigquery`:

```text
numpy>=1.26.4,<2.0
```

(A prior version of this section also described pinned `shapely`/`geopandas` versions for a geospatial stack — corrected here: neither package appears anywhere in `streamlit/requirements.txt`, `pyproject.toml`, `uv.lock`, or the `streamlit/` codebase today. There is no map-rendering dependency in this project currently.)

If dependency state is stale, rebuild the virtual environment and reinstall from `streamlit/requirements.txt`.

### 4. Environment Variables

Replace these values for your own deployment.

```bash
export GOOGLE_CLOUD_PROJECT="encoded-joy-485413-k5"
export GCP_PROJECT_ID="encoded-joy-485413-k5"
export GCS_BUCKET="civil-liberties-data"
export TARGET_ENV="staging"
export BRUIN_ENV="dev"
export COUNTRY="Kenya"
export ISO2="KE"
export DEFAULT_START="2023-06-01"
export DEFAULT_END="2025-06-30"
```

PowerShell:

```powershell
$env:GOOGLE_CLOUD_PROJECT = "encoded-joy-485413-k5"
$env:GCP_PROJECT_ID = "encoded-joy-485413-k5"
$env:GCS_BUCKET = "civil-liberties-data"
$env:TARGET_ENV = "staging"
$env:BRUIN_ENV = "dev"
$env:COUNTRY = "Kenya"
$env:ISO2 = "KE"
$env:DEFAULT_START = "2023-06-01"
$env:DEFAULT_END = "2025-06-30"
```

The Streamlit configuration also supports `.env` values and Bruin configuration defaults.

### 5. Authenticate BigQuery

For local development:

```bash
gcloud auth application-default login
gcloud config set project encoded-joy-485413-k5
```

For service-account based execution:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/service-account.json"
gcloud auth activate-service-account --key-file "$GOOGLE_APPLICATION_CREDENTIALS"
gcloud config set project encoded-joy-485413-k5
```

### 6. Install Bruin

```bash
curl -LsSf https://getbruin.com/install/cli | sh
bruin --version
```

The Bruin pipeline expects these connection names:

- `bigquery-default`
- `duckdb-parquet`

### 7. Prepare Source Data

Four sources feed the pipeline. Their raw-ingest assets expect real, specific local files — the exact expected filenames and destination paths below are taken directly from each asset's own code (`Bruin/assets/ingest/*.py`), not paraphrased.

| Source | Required? | Where to get it | Exact expected path |
|---|---|---|---|
| **ACLED** | Yes — feeds the conflict-pressure/regime-classifier chain | [ACLED's Data Export Tool](https://acleddata.com/data-export-tool/) (free registration required for non-commercial use; a separate paid Commercial License Agreement applies for commercial use — see `docs/02-architecture/data_sources.md`) | `data/dev/acled/Africa_aggregated_data_up_to_week_of-2026-03-14.csv` |
| **OONI** | Yes — feeds the protocol/censorship-measurement chain, the dashboard's primary evidence source | OONI's public S3 bucket, `s3://ooni-data-eu-fra/raw/<YYYYMMDD>/` (no account needed), fetched with `scripts/download_ooni.ps1` (`aws s3 sync --no-sign-request`, Kenya only; set the start date and folder at the top of the script, then move the files to the path at right). CLIO's corpus contains six test types: dnscheck, WhatsApp, Telegram, Psiphon, Signal and Tor. Web Connectivity and Facebook Messenger were missing because the script's patterns used `web_connectivity`/`facebook_messenger`, while the bucket's folders are `webconnectivity`/`facebookmessenger`; the script now uses the folder names, with Web Connectivity off by default because of its size (about 90 GB compressed for this window). **Web Connectivity and Facebook Messenger are not in the corpus**, although OONI holds about 5.1 million and 51,000 Kenya measurements of them for 2023-06-01 to 2025-06-30 (OONI aggregation API, checked 2026-11-05). CLIO's OONI layer therefore does not cover website blocking. | `.jsonl.gz` files under `data/dev/ooni/ooni-kenya-censorship/`, normalized by `raw.ooni_conflict_measurements` into `data/dev/ooni/ooni_measurements.parquet` |
| **Google Transparency Report** | Feeds `platform_pressure_score` and the pressure-attribution platform-drivers mart; the pipeline can be scoped to skip it (see below) | Google's Transparency Report government-requests pages, CSV export per report type (no official bulk API confirmed — see `docs/02-architecture/data_sources.md`) | `data/dev/google/google-government-removal-requests.csv` and `data/dev/google/google-government-detailed-removal-requests.csv` |
| **Lumen** | No — nothing to obtain | N/A. `raw.lumen_requests` fabricates its rows in code (`np.random.seed(42)`, deterministic); it does not read any external file. This branch is also formally excluded from the composite pressure score (ADR-0004) — it materializes but nothing live reads it. | N/A |

**A real, disclosed reproducibility limitation:** the raw source files under `data/dev/` are not in this repository; you have to obtain them yourself. The ingest and load scripts find them relative to the repository root (`Path(__file__).resolve().parents[3]`), so a clone at any location works once the files are in place. **If you don't have ACLED registration, or haven't downloaded the OONI files with `scripts/download_ooni.ps1`, you cannot reproduce the full pipeline end-to-end** — this is a genuine boundary, not a "just clone and run" claim. A partial run scoped to whichever source(s) you do have real data for is possible via Bruin's `--selector`/`--exclude-tag`/`--tag` flags (`bruin run --help`), since Bruin's DAG only materializes an asset once its declared dependencies exist — running the full `pipeline.yml` default against incomplete source data will halt at the first missing upstream asset, not degrade gracefully.

See `docs/02-architecture/data_sources.md` for full per-source licensing, grain, and known-limitation detail, and `docs/02-architecture/data-modelling.md` for schema/modeling detail.

### 8. Run Bruin

From the repository root:

```bash
cd Bruin
bruin run pipeline.yml
```

Example targeted runs:

```bash
bruin run assets/features/protocol_daily_signals.sql
bruin run assets/intelligence/protocol_relationships.sql
bruin run assets/reporting/protocol_repression_correlation_mart.sql
```

### 9. Launch Streamlit

From the repository root:

```bash
cd streamlit
python -m streamlit run app.py
```

Open:

```text
http://localhost:8501
```

### 10. Codespaces Clean Reinstall

```bash
cd /workspaces/Civil-Liberties-and-Censorship-Analysis-with-Bruin
deactivate 2>/dev/null || true
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
python -m pip install --no-cache-dir -r streamlit/requirements.txt

python - <<'PY'
import numpy
from google.cloud import bigquery
print("numpy", numpy.__version__)
print("bigquery import ok")
PY

cd streamlit
python -m streamlit run app.py
```

Expected NumPy version:

```text
1.26.x
```

---

## Data Model and Methodology

Four sources feed the pipeline today — OONI, ACLED, Google Transparency Report, and a currently-synthetic, benched Lumen branch — through seven layers (raw → staging → intermediate → features → intelligence → marts → reporting). Full detail lives in three dedicated documents rather than duplicated here, so this section doesn't become a second, silently-drifting copy of them:

The repository also holds a prototype AI-assisted report writer, `llm_report_writer/` (ADR-0010). It is designed to draft narrative report text only from CLIO's own already-computed marts — never a new fact sourced from outside CLIO — with every generated claim re-checked against the exact mart row it cites, plus a completeness check that a report citing synthetic-derived data (e.g. Lumen) must include the required disclosure. It has been run live only in a one-off evaluation (2026-08-03: drafts for 11 historical windows compared with a template baseline, plus one follow-up spot-check; see `decision-log.md`), producing internal drafts, not published reports. It is not part of the dashboard, sits outside Bruin's DAG, and is not run by the pipeline or on a schedule.

- **[`docs/02-architecture/data_sources.md`](docs/02-architecture/data_sources.md)** — every source's real grain, licensing status, and ingestion path, plus which additional sources (STOP/Access Now, CPJ, IODA, Freedom House) are recommended but not yet ingested.
- **[`docs/02-architecture/data-modelling.md`](docs/02-architecture/data-modelling.md)** — the live dimension/fact/reporting schema, with a Mermaid ER diagram generated from the actual BigQuery schema, and a documented gotcha (two different `composite_pressure_score` formulas share a column name across two tables — see that doc before assuming which one you're reading).
- **[`docs/02-architecture/erd-lineage.md`](docs/02-architecture/erd-lineage.md)** — the full pipeline dependency graph per source, generated from the live Bruin DAG, including the two guardrails that keep it from silently corrupting (the ACLED regime engine's execution-order precondition, and the materialization-staleness CI check).

### Statistical Methodology

The platform uses guarded statistical inference rather than raw-count interpretation.

Core methods:

- Rolling baselines compare current pressure against recent historical behavior.
- Anomaly scoring measures protocol deviation from expected signal patterns.
- Sparse-window suppression prevents weak evidence from producing strong claims.
- Confidence weighting gives stronger influence to higher-quality observations.
- Variance guardrails suppress correlation claims when statistical windows collapse.
- Protocol inference evaluates DNS, HTTP, TCP, and TLS regime behavior.
- Pressure correlation modeling aligns protocol anomalies with national pressure signals.

> **Retired pending removal (2026-11-14, ADR-0016).** The rolling OONI–pressure correlation is no longer used for findings. It is being replaced by an episode-based method; see [ADR-0016](docs/02-architecture/adr/0016-episode-based-method-replaces-rolling-correlation.md).

Correlation outputs include:

- `SYNCHRONIZED_ESCALATION`
- `INVERSE_MOVEMENT`
- `PROTOCOL_DIVERGENCE`
- `PRESSURE_ONLY`
- `NO_CLEAR_ALIGNMENT`

These states are analytical indicators, not causal findings.

## Validation and Contracts

The repository includes Bruin validation assets, Streamlit dataframe contracts, and pytest-based contract checks.

Bruin validation assets:

- `features.validate_protocol_daily_signals`
- `intelligence.validate_ooni_intelligence_contracts`

Streamlit contract layer:

- validates required mart columns
- coerces date and timestamp fields
- coerces numeric display fields
- supports string ASNs
- permits valid sparse-window nulls
- returns empty dataframes only for true contract failures

Automated test entry point:

```bash
pytest -q
```

Lint entry point:

```bash
ruff check .
```

### Validation History

Run commands and asset names tell you validation *exists*; they don't tell you what's actually been checked or what came back. This section states that plainly, with real numbers, not vague claims — full detail lives in `docs/02-architecture/technical-debt-inventory.md` and `docs/02-architecture/decision-log.md`; this is the top-line summary, not a duplicate of either.

**ACLED regime classifier — golden-file regression tests.** `tests/test_acled_pressure_regimes_golden.py` asserts the ACLED "Path A" regime classifier's output against recorded fixtures for two real historical windows: the Finance Bill 2024 protests (2024-05-11 to 2024-07-13) and the Jan–Feb 2008 post-election violence. This is a drift check against previously reviewed, materialized BigQuery output (not a validation of the classifier), gated behind an opt-in `RUN_BIGQUERY_TESTS=1` environment variable — without it, both tests skip cleanly (2 skipped, offline, well under 1 second); re-run live for this section (2026-08-31) with the flag set and real BigQuery access, both windows pass (2 passed, ~11 seconds). The repository's full test suite (`pytest -q`, re-run 2026-11-16 without BigQuery access) reports 39 passed, 43 skipped. The skips are the BigQuery-gated tests, not failures — but they are most of the behavioural tests. The tests that run the classification, regime and aggregation logic against data need BigQuery, and they are skipped in CI, where `tests.yml` has no GCP credentials (TD-39). The 39 that pass offline are mostly static checks of the SQL text and its lookup tables, plus the Streamlit contract helper.

**A disclosed, self-found bug: 91.5% of the TLS observation table was misclassified for months.** `stg.ooni_tls_observations.handshake_success` was structurally `NULL` for 100% of 422,487 rows across every ingested app (Signal, WhatsApp, Telegram, Psiphon) — the extraction read a JSONPath (`$.status.success`) that belongs to a different OONI data shape than TLS handshake objects actually have. The consequence: 386,617 of 422,487 rows (91.5%) that should have read `OK` (a genuinely successful handshake) instead fell through to `UNKNOWN`. Found and fixed on this project's own initiative — not flagged by an outside party — and disclosed here rather than left to be found later in the commit history. Full before/after numbers per app, and the downstream cascade this fix was traced through, are in `technical-debt-inventory.md`'s TD-72 entry.

**External validation against OONI's own live API (2026-08-01), not just this project's own tables.** A dedicated validation pass checked CLIO's TLS classification against OONI's raw measurement JSON directly, across four independent strata (~1,054 live API calls against `api.ooni.org`, rate-limited, disk-cached):

- **Core premise: 100/100 exact matches.** Sampled rows CLIO moved `UNKNOWN`→`OK` were checked against OONI's raw JSON at the exact recorded offset — did `failure` actually show present-and-null, or was an extraction miss silently read as a false success? Zero divergences.
- **Extractor verbatim match: 113/113.** Every available row for CLIO's four re-tiered TLS failure modes matched OONI's raw `failure` string exactly.
- **All 361 real `BLOCKED` rows individually checked, not sampled.** In August 2026 all 361 TLS observations CLIO then classified BLOCKED were checked against OONI's own records: 281 agreed, and 80 came from measurements OONI itself scores at zero accuracy. A November 2026 check found that those measurements had been explained but never excluded from CLIO's counts, and that CLIO's copy of OONI's discard rules was out of date (ADR-0017). CLIO now applies OONI's current rules at both measurement and observation level: 90 of the 361 TLS observations are excluded, and 271 remain classified BLOCKED. This checks the precision of CLIO's BLOCKED rows only; it does not measure recall (blocking CLIO failed to mark BLOCKED).
- **Residual sample (informational): 99/100.** A sample of the remaining ambiguous `ssl_*` `UNKNOWN` rows would be discarded by the same known-bad-probe-version table — a concrete, evidence-backed lead for a still-open confidence-elevation question, not itself a pass/fail check.

Full stratum-by-stratum methodology is in `decision-log.md`'s 2026-08-01 (fifth session) entry.

**ACLED ingestion-layer fidelity audit (2026-08-02).** A separate check of whether the ACLED ingestion pipeline (`raw.acled_conflict_events` → `load.acled_conflict_events_to_gcs` → `stg.acled_conflict_events`) transcribes ACLED's own export data faithfully, one layer upstream of the regime-classifier tests above. Checked field-by-field for the Finance Bill 2024 window and two quiet control periods (the Aug 2010 constitutional referendum and the Sept 2017 Supreme Court election annulment): row counts, fatality sums, event/sub-event-type coding, date/week-anchor alignment, and county (`admin1`) coverage all matched exactly, including a full row-level equality diff beyond the requested aggregate checks (0 mismatches, either direction, in every window), and the same result held at the full 267,956-row, 58-country dataset level. **One honestly-disclosed gap, not smoothed over:** the original ACLED CSV that `raw.acled_conflict_events` reads wasn't available in that session's environment, so the earliest ingestion leg (CSV → Parquet) was verified by code inspection — a pure 1:1 column rename with no computation — rather than an executed byte-level diff. Full results are in `decision-log.md`'s 2026-08-02 entry.

This project also has an on-demand guardrail that re-checks a sample of its OONI-based classifications against OONI's own published measurement data, to catch drift or regressions in how CLIO interprets raw network measurements. It is run by hand (`workflow_dispatch` on `ooni-agreement-check.yml`, or the script locally), typically after the OONI verdict chain is rematerialized; its weekly cron is permanently disabled. See `docs/02-architecture/adr/0013-ooni-agreement-check-external-reference-oracle-guardrail.md` for the full design, including how the check panel is chosen and why it's kept public.

## Infrastructure and Deployment

Terraform under `infra/` provisions the cloud backbone:

- Google Cloud Storage bucket
- BigQuery staging and production datasets
- IAM bindings

Deployment portability is supported through:

- environment variable configuration
- `.env.example`
- Terraform modules
- pinned dashboard dependencies
- CI lint and test workflows

Additional production controls may include: secret management, least-privilege IAM, remote Terraform state, authenticated dashboard hosting, and BigQuery cost controls.

## Roadmap

Near-term platform evolution:

- Multi-country expansion using configurable country, dataset, and date settings
- Deeper mart contract coverage across all dashboard-facing models
- Evidence lineage tracing from dashboard scores back to source records
- Deployment hardening for authenticated cloud hosting
- Reporting API layer over curated marts

## Responsible Use

This system is observational and historical. It does not identify individuals, track users, exploit networks, or provide real-time operational surveillance.

- **No individual attribution.** Only aggregated, publicly available datasets are used; there is no ingestion of personally identifiable information and no attempt to de-anonymize or infer identities. All analysis operates at country, network, or platform level — never at the level of a specific person, activist, or journalist.
- **No political stance embedded.** The models measure signals, not blame. Outputs are evidence-weighted indicators, not definitive proof of intent or causality, and should not be read as an accusation or endorsement.
- **No exploitation tooling.** Nothing in this repository is designed to exploit vulnerabilities, target infrastructure, or enable censorship. The system is observational, not operational.
- **Responsible interpretation is expected of anyone using this project's outputs** — avoid misrepresenting findings, avoid unsupported conclusions, and never use outputs to justify harm, discrimination, or misinformation.

Civil-liberties analysis requires context, source awareness, and careful communication: observed correlations (e.g. conflict alongside blocking) do not imply direct causation, and results should be interpreted alongside political context, legal frameworks, and known infrastructure limitations.

## Data Licensing & Attribution

CLIO's evidence sources carry their own, separate licensing terms, re-verified directly from primary sources:

- **OONI** — CC BY-NC-SA 4.0 (Attribution-NonCommercial-ShareAlike).
- **ACLED** — a contractual, non-Creative-Commons license: free for non-commercial use with registration; commercial use requires a separate paid license from ACLED.
- **Google Transparency Report** — no source-specific reuse license could be located despite direct search; status is **Cannot Determine**, not assumed compliant.
- **Lumen Database** — the platform's current Lumen-derived figures are synthetic placeholders, not real Lumen data, and are excluded from all live output (see "Data Model and Methodology" above).

Because of the OONI and ACLED terms above, **CLIO's OONI- and ACLED-derived intelligence layer is treated as non-commercial and grant/public-interest-funded for the foreseeable term, not as a product for direct sale.** This project does not redistribute the underlying third-party datasets — only transforms them into attributed, confidence-qualified findings — but transformation does not, on its own, remove either source's NonCommercial restriction. The Finance Bill 2024 case study is released as free public-interest research, not a paid deliverable.

This posture governs CLIO's data and findings; it is separate from the MIT license on this repository's own code (see below).

Some test fixtures contain OONI data (CC BY-NC-SA 4.0) or ACLED-derived labels (ACLED's terms), not MIT-licensed code — see [`tests/fixtures/LICENSE-NOTE.md`](tests/fixtures/LICENSE-NOTE.md).

**Before relying on any CLIO finding commercially** — including in a paid engagement, product, or service — contact the maintainer first (see below). CLIO's current default is non-commercial; nothing in this repository should be read as a license to resell OONI- or ACLED-derived findings.

## How to Cite CLIO

If citing CLIO's findings in research, journalism, or advocacy work:

> CLIO (Civil Liberties Intelligence Observatory), Samwel Njogu, [github.com/Sanjomwa/Civil-Liberties-Intelligence-Observatory](https://github.com/Sanjomwa/Civil-Liberties-Intelligence-Observatory). Accessed [date]. Findings derived from OONI (CC BY-NC-SA 4.0) and ACLED (contractual, non-commercial by default) — see "Data Licensing & Attribution" above for each source's own required citation elements.

Findings that draw on ACLED or OONI data should also carry each source's own required attribution (ACLED: access date, filters/subset used, and any manipulation performed; OONI: credit, license link, and any changes made) — not CLIO's citation alone. See "Data Licensing & Attribution" above.

## Attribution and License

Maintained by Samwel Njogu  
LinkedIn: [www.linkedin.com/in/samwel-mwaniki-6482563b2](https://www.linkedin.com/in/samwel-mwaniki-6482563b2)

Built as a civil-liberties observability platform — currently piloted in Kenya — using Bruin, BigQuery, Streamlit, Terraform, Python, OONI, ACLED, and Google Transparency Report data. A Lumen-derived legal-pressure signal exists in the pipeline but is currently synthetic and benched from all live output (see "Data Licensing & Attribution" above).

This repository's own code is licensed under the MIT License. Third-party data sources retain their own separate licensing terms — see "Data Licensing & Attribution" above.
