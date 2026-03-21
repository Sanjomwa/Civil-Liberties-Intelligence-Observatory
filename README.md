# Civil Liberties & Censorship Analysis in Kenya with Bruin

- Analyzing Government Takedown Requests & Civil Liberties Risks (2024–2026)

## Table of Contents
- [Project Pitch and Problem Statement](#project-pitch-and-problem-statement)
- [Datasets](#datasets)
- [Architecture and Workflow](#architecture-and-workflow)
- [Goals & Deliverables](#goals--deliverables)
- [Repo Structure](#repo-structure)
- [Ethics and Responsible Use](#ethics-and-responsible-use)
- [Quickstart & Low-Cost Runbook](#quickstart--low-cost-runbook)
- [Milestones and Next Steps](#milestones-and-next-steps)
- [License](#license)

---

## Project Pitch and Problem Statement

Reliable, auditable data on government content removal requests is crucial for understanding impacts on civil liberties, freedom of expression, and human rights.

This project builds a **reproducible, low-cost data engineering pipeline** using **Bruin** to:
- Ingest Google Transparency Report takedown data (filtered to Kenya),
- Enrich it with **ACLED** conflict/protest events and global social media censorship incidents,
- Compute temporal/geospatial alignments and a composite **Civil Liberties Risk Index**,
- Produce interactive dashboards highlighting patterns in Kenya (2024–2026).

**Core question**: How do government takedown requests correlate with political events, protests, and conflict spikes in Kenya?

The pipeline remains neutral and evidence-based — no advocacy — focusing on verifiable trends (e.g., ~62% rejection rate of Kenyan requests by Google in H1 2025).

**Audience**: Researchers, journalists, civil society, policy analysts, and data engineers interested in transparency tools.

Built end-to-end with **[Bruin](https://getbruin.com)** (ingestion, SQL/Python transforms, quality checks, orchestration).

---

## Datasets

| Dataset                              | Source                                                                 | Access Method                          | Coverage Focus       | Key Fields                              |
|--------------------------------------|------------------------------------------------------------------------|----------------------------------------|----------------------|-----------------------------------------|
| Google Transparency Report           | https://transparencyreport.google.com/government-removals/data        | CSV download (semi-annual files)       | Global, filter Kenya | Date, country, requester, platform, motive, items requested, action taken |
| ACLED (Armed Conflict Location & Event Data) | https://acleddata.com/data-export-tool/ (myACLED account required) | CSV export tool or API                 | Kenya events         | Event date, location (county), event type, actors, fatalities |
| Global Social Media Censorship       | https://data.mendeley.com/datasets/r49ybxt5j4                         | Direct CSV download                    | 2006–2023 (filter Kenya) | Country, year, platform, reason (morality, misinformation, etc.) |
| Optional                             | OONI (internet measurements), WHO infodemic proxies                   | Manual CSV / API                       | Kenya-specific       | Shutdown dates, misinfo events          |

**Notes**:
- Google: Download full historical CSVs → filter Kenya in staging.
- ACLED: Free registration required for export tool/API.
- All datasets ingested via Bruin (API,CSV file/URL, HTTP connectors).

---

## Architecture and Workflow

1. **Ingestion**  
   Bruin + ingestr connectors:  
   - HTTP / CSV URL for ACLED API exports  
   - File / local CSV for Google & Mendeley downloads

2. **Transformation** (SQL + Python)  
   - Staging: Clean, normalize (dates, Kenya county names, ISO codes)  
   - Enrichment: Temporal windows (e.g., ±30 days), geospatial joins, motive categorization  
   - Marts: Aggregates by motive/date/region + **Risk Index**  
     Risk Index = (normalized takedown count) × (nearby ACLED violent events score) × (social censorship weight)

3. **Orchestration**  
   Bruin pipeline.yml DAG: ingest → stage → quality checks → marts → export  
   Weekly schedule, failure alerts (configurable)

4. **Analysis & Visualization**  
   Streamlit dashboard:  
   - Kenya county heatmap (takedowns + ACLED)  
   - Timeline (spikes vs known protest periods)  
   - Actor breakdown (e.g., CAK vs platforms)  
   - Risk index map & motive pie charts

---

## Goals & Deliverables

- Full Bruin pipeline: ingestion → transformation → quality → orchestration
- Reproducible one-command runs (local DuckDB → BigQuery)
- Interactive Streamlit dashboards (local + optional Cloud Run)
- Short findings: 3–5 key insights (e.g., takedown spikes during 2024 Finance Bill protests)
- Showcase Bruin strengths: unified tool, column lineage, built-in quality/orchestration

---

## Repo Structure

civil-liberties-censorship-kenya-bruin/
├── bruin/
│   ├── assets
│   │   ├── ingest/          # ingestion YAML/SQL/Python
│   │   ├── staging/         # cleaning & normalization
│   │   └── marts/           # enriched tables, risk index
│   └── pipeline.yml         # main DAG definition
├── src/
│   └── streamlit_app/       # app.py + visualizations.py
├── terraform/               # GCP infra (BigQuery, GCS, Cloud Run)
├── tests/                   # asset tests, pytest
├── docs/
│   └── screenshots/         # Bruin lineage, flows, dashboards
├── .env.example
├── Makefile                 # infra-apply, run-pipeline, deploy-app
├── pyproject.toml
├── uv.lock
├── README.md
└── LICENSE


---

## Ethics and Responsible Use

- Data is public/aggregated — no personal information processed.
- Analysis is descriptive and neutral; no causal claims without evidence.
- Findings presented for transparency and research — not political advocacy.
- Users encouraged to verify sources and cite original datasets.

---

## Prerequisites
- Python 3.12+
- Bruin CLI (`pip install bruin-cli` or from https://getbruin.com)
- uv (recommended) or venv + pip
- Free accounts: myACLED (for data export), Google Cloud (optional BigQuery)

### Steps

## 🚀 Setup Instructions

# Step 1: Clone the repo:
   ```bash
   git clone https://github.com/<your-username>/civil-liberties-and-Censorship-Analysis-with-Bruin.git
   cd civil-liberties-and-Censorship-Analysis-with-Bruin
  ```

# Step 2: Environment Setup
Python 3.12 + uv for dependency management.

- Install Bruin CLI.

- Create virtual environment:
  `bash
uv venv
source .venv/bin/activate
uv pip install -e ".[dev,test]"
  `
- Add pyproject.toml + uv.lock for reproducibility.

# Step 3: Ingest Assets
  - ACLED Kenya CSV (via export tool) → place in data/raw/
  - Google Transparency CSV → place in data/raw/
  - Mendeley CSV → place in data/raw/
  - Optional: OONI/WHO → manual CSV ingestion.

Each ingestion asset defined in bruin/assets/ingest/.

# Step 4: Stage Assets
Clean raw tables (dates, country filters).
Normalize schema (Kenya counties, motives).
Store in DuckDB (local .db file).
SQL files in bruin/assets/staging/.

# Step 5: Analytical Marts
events_by_type: takedowns grouped by motive.
events_by_date: temporal alignment with ACLED protests.
events_by_region: geospatial join (Kenya counties).
risk_index: composite score (takedowns × conflict × social events).
SQL in bruin/assets/marts/.

# Step 6: Orchestration
- pipeline.yml defines DAG:
  ``pipeline.yml
ingest_acled → stg_acled
ingest_takedowns → stg_takedowns
ingest_social → stg_social
stg_* → marts (events_by_type, risk_index)
  ``
- Add data quality checks (NOT NULL, UNIQUE, valid date ranges).
- Bruin CLI runs pipeline with:
  ```bash
  bruin run bruin/pipeline.yml
  ```
# Step 7: Dashboard
- Streamlit app in src/streamlit_app/.
Visualizations:
  - Heatmap (counties).
  - Timeline (spikes vs protests).
  - Actor dashboard (CAK vs platforms).
  - Risk index map.

Local run:
```bash
streamlit run src/streamlit_app/app.py
```
# Step 8: Infrastructure
Terraform scripts in /terraform for GCP resources:
  - GCS (data lake).
  - BigQuery (warehouse).
  - Cloud Run (dashboard deployment).
Makefile commands:
  - Make infra-apply → deploy infra.
  - Make app-deploy → deploy Streamlit to Cloud Run.

# Step 9: CI/CD
GitHub Actions workflow:
  - Run tests on push.
  - Lint + format with pre-commit.
  - Deploy infra + dashboard on tagged release.

# Step 11: Documentation
Update README.md with:
  - Architecture diagram.
  - Dataset sources.
  - Setup instructions.
  - Screenshots of Bruin lineage + dashboard.

# Step 12: Submission
Publish repo on GitHub.
Share in Zoomcamp Slack #projects.
Include screenshots + demo link (Cloud Run if deployed).
