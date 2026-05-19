# Kenya Civil Liberties Intelligence Observatory

> A historical intelligence platform for reconstructing latent censorship pressure in Kenya by fusing fragmented civil-liberties indicators into auditable statistical signals.

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Bruin](https://img.shields.io/badge/Bruin-Orchestration-FF9900?style=for-the-badge)](https://getbruin.com/)
[![BigQuery](https://img.shields.io/badge/BigQuery-Warehouse-4285F4?style=for-the-badge&logo=googlebigquery&logoColor=white)](https://cloud.google.com/bigquery)
[![Streamlit](https://img.shields.io/badge/Streamlit-Intelligence%20Dashboard-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Terraform](https://img.shields.io/badge/Terraform-Infrastructure-844FBA?style=for-the-badge&logo=terraform&logoColor=white)](https://www.terraform.io/)
[![DuckDB](https://img.shields.io/badge/DuckDB-Local%20Analytics-FFF000?style=for-the-badge&logo=duckdb&logoColor=black)](https://duckdb.org/)
[![Parquet](https://img.shields.io/badge/Parquet-Columnar%20Data-005571?style=for-the-badge)](https://parquet.apache.org/)

## Intelligence Reconstruction Scope

This repository reconstructs historical digital repression pressure across Kenya from June 2023 through June 2025. It combines network measurements, conflict indicators, legal-pressure signals, and platform transparency data into governed BigQuery marts and Streamlit intelligence views.

The platform is designed to answer high-context analytical questions:

- Did network interference intensify during political stress windows?
- Which protocols showed abnormal censorship behavior?
- Which ASNs concentrated the strongest interference signals?
- Did pressure indicators align around the Finance Bill 2024 period?
- Which signals are statistically weak because of sparse data, low confidence, or zero variance?

The platform reconstructs historical civil-liberties pressure; it does not perform live operational surveillance.

## Why This Matters

Digital repression is rarely observable through one clean dataset. It can appear as protocol anomalies, DNS or TCP failures, platform removals, legal pressure, protest dynamics, and inconsistent measurement coverage.

This project treats censorship analysis as an observability and inference problem. It fuses fragmented civil-liberties indicators into auditable statistical outputs, while preserving guardrails that prevent weak or sparse evidence from being overstated.

TThe result is a production-oriented reference architecture for civil-liberties observability, analytical inference, and governed public-interest intelligence reconstruction.

---

## Dashboard Showcase

### National Stress Observatory

![](<Screenshot 2026-05-18 182543.png>)

Executive view of national digital-pressure movement, baseline divergence, suppression-window probability, and evidence quality across the Kenya observation window.

---

### Protocol Regime Monitor

![](<Screenshot 2026-05-18 182816.png>)

Protocol-level regime classification for DNS, HTTP, TCP, and TLS, showing when network behavior moves from normal range into elevated, severe, or insufficient-evidence states.

---

### Protocol Stress Intelligence Observatory

![](<Screenshot 2026-05-18 183302.png>)

Comparative protocol-intelligence surface exposing anomaly escalation, confidence-weighted severity, and regime transition behavior across monitored transport layers.

---

### Protocol ↔ Repression Correlation Engine

![](<Screenshot 2026-05-18 183334.png>)

Statistical alignment engine measuring whether protocol anomalies move with national repression-pressure indicators across rolling historical windows.

---

### ASN Behavioral Intelligence

![](<Screenshot 2026-05-18 183400.png>)

Network-level intelligence view ranking ASNs by blocking intensity, behavioral priority, evidence maturity, dominant protocol, and reliability of observed interference.

---

### Finance Bill 2024 Incident Report

![](<Screenshot 2026-05-18 183519.png>)

Focused reconstruction of the Finance Bill 2024 period, connecting protocol behavior, national pressure signals, and major-provider activity during a known political stress window.

---

### Suppression Event Explorer

![](<Screenshot 2026-05-18 183454.png>)

Investigation surface for exploring synchronized censorship escalation windows, correlation states, divergence patterns, and protocol-specific pressure signals.

---

### Methodology & Statistical Guardrails

![](<Screenshot 2026-05-18 183550.png>)

Methodology view documenting how sparse data, confidence weighting, variance checks, and rolling baselines constrain interpretation before signals enter intelligence outputs.

---

## Architecture Overview

```mermaid
flowchart LR
    Sources["OONI, ACLED, Google Transparency, Lumen-style data"]
    Ingest["Python ingestion and Parquet normalization"]
    Warehouse["BigQuery staging, facts, dimensions, features"]
    Intelligence["Protocol regimes, lag relationships, pressure correlation"]
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

```text
.
|-- Bruin/
|   |-- pipeline.yml
|   |-- requirements.txt
|   `-- assets/
|       |-- ingest/          # Raw source ingestion assets
|       |-- load/            # GCS and BigQuery external table loaders
|       |-- staging/         # Source normalization models
|       |-- intermediate/    # Cross-source preparation models
|       |-- marts/
|       |   |-- dims/        # Conformed dimensions
|       |   `-- facts/       # Analytics-ready fact tables
|       |-- features/        # Model-ready protocol features
|       |-- intelligence/    # Regime and relationship inference
|       `-- reporting/       # Dashboard-facing marts
|-- .env.example             # Portable environment variable template
|-- .github/
|   `-- workflows/
|       |-- lint.yml         # CI lint scaffolding
|       `-- tests.yml        # CI test scaffolding
|-- docs/
|   |-- analysts-questions-playbook.md
|   |-- civil-liberties-reporting-playbook-Kenya.md
|   |-- data-modelling.md
|   |-- data_sources.md
|   |-- erd-lineage.md
|   `-- project_difficulties.md
|-- infra/
|   |-- main.tf
|   |-- provider.tf
|   |-- variables.tf
|   |-- setup-gcp.sh
|   |-- verify-gcp.sh
|   `-- modules/
|       |-- bigquery/
|       |-- gcs/
|       `-- iam/
|-- scripts/
|   |-- download_ooni.ps1
|   |-- local_ingest_ooni.py
|   `-- lumen_parquet.py
|-- streamlit/
|   |-- app.py
|   |-- requirements.txt
|   |-- pages/
|   |   `-- 3_Protocol__Stress_Intelligence_Observatory.py
|   |-- services/
|   |   |-- bq.py
|   |   `-- marts.py
|   |-- core/
|   |   |-- config.py
|   |   |-- constants.py
|   |   `-- contracts.py
|   |-- components/
|   |   |-- charts.py
|   |   |-- status.py
|   |   |-- tables.py
|   |   `-- trust.py
|   `-- assets/
|       |-- annotations/
|       `-- methodology/
|           `-- thresholds.yml
|-- tests/
|   `-- test_contracts.py    # Automated dashboard contract tests
|-- pyproject.toml
|-- uv.lock
`-- README.md
```

---

## Quickstart

### 1. Clone

```bash
git clone https://github.com/Sanjomwa/Civil-Liberties-and-Censorship-Analysis-with-Bruin.git
cd Civil-Liberties-and-Censorship-Analysis-with-Bruin
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

The dashboard requirements pin the geospatial stack to avoid NumPy ABI conflicts during BigQuery imports:

```text
numpy>=1.26.4,<2.0
shapely==2.0.3
geopandas==0.14.3
```

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

Minimum source expectations:

- OONI JSONL gzip files normalized into `ooni_measurements.parquet`
- ACLED aggregated Kenya/Africa CSV export
- Google Transparency CSV exports
- Lumen-style Parquet data, generated or replaced with approved real exports

See `/docs` for expanded data acquisition and modeling notes.

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
import numpy, shapely, geopandas
from google.cloud import bigquery
print("numpy", numpy.__version__)
print("shapely", shapely.__version__)
print("geopandas", geopandas.__version__)
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

### Source Inputs

| Source              | Analytical role                                                 |
| ------------------- | --------------------------------------------------------------- |
| OONI                | Network interference and protocol-level censorship measurements |
| ACLED               | Protest, conflict, and political pressure context               |
| Google Transparency | Government and platform removal-pressure indicators             |
| Lumen-style data    | Takedown and legal-pressure signal branch                       |

ACLED ingestion depends on approved API or export access; reproducibility guidance is documented in `/docs`.

### Modeling Layers

| Layer        | Purpose                                            | Examples                                                                                      |
| ------------ | -------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Raw / ingest | Preserve source shape and land reprocessable files | OONI raw measurements, ACLED aggregated events, Google requests                               |
| Staging      | Normalize source fields and data types             | `stg.ooni`, `stg.acled_conflict_events`, `stg.google_transparency_requests`                   |
| Intermediate | Prepare cross-source pressure signals              | OONI observations, Google periodization, Lumen daily pressure                                 |
| Facts        | Analytics-ready event and daily pressure tables    | `fact_country_pressure_daily`, `fact_ooni_censorship_signals`, `fact_takedown_pressure_daily` |
| Dimensions   | Reference and descriptive context                  | `dim_dates`, `dim_asn`, `dim_country`, `dim_platforms`, `dim_reasons`                         |
| Features     | Model-ready statistical features                   | `features.protocol_daily_signals`                                                             |
| Intelligence | Inference over regimes and relationships           | `intelligence.protocol_signal_regimes`, `intelligence.protocol_relationships`                 |
| Reporting    | Streamlit-facing marts                             | `mart_political_stress_windows`, `protocol_repression_correlation_mart`                       |

Key reporting marts:

- `reporting.mart_political_stress_windows`
- `reporting.mart_protocol_interference_trends`
- `reporting.protocol_repression_correlation_mart`
- `reporting.asn_behavior_profile_mart`

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

Outputs should be interpreted as evidence-weighted indicators, not definitive proof of intent or causality. Civil-liberties analysis requires context, source awareness, and careful communication.

## Attribution and License

Maintained by Samwel Njogu  
X: [@sam_njogu9](https://x.com/sam_njogu9)

Built as a Kenya-focused civil-liberties observability platform using Bruin, BigQuery, Streamlit, Terraform, Python, OONI, ACLED, Google Transparency, and Lumen-style legal pressure data.

This project is licensed under the MIT License.
