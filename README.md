# Civil Liberties & Censorship Analysis in Kenya with Bruin
## Analyzing Government Takedown Requests & Civil Liberties Risks (June 2023–June 2026)

## 🎯 Project Pitch and Problem Statement

Across the world, governments are increasingly requesting the removal of online content — from social media posts to blogs, videos, and news articles. While some requests may be justified (e.g., protecting minors, removing illegal content), others risk undermining civil liberties, freedom of expression, and democratic resilience. Without transparent, reproducible analysis, it is difficult for researchers, journalists, and civil society to distinguish legitimate governance from censorship.

Kenya provides a timely case study. Between 2024 and 2026, the country has experienced waves of political protests, contentious legislation, and heightened online activism. During this period, Google Transparency Reports show a surge in takedown requests from Kenyan authorities, with a rejection rate of ~62% in H1 2025. At the same time, ACLED data records spikes in conflict events and fatalities, while OONI and other internet measurement projects detect anomalies in access to social platforms. These signals suggest a complex relationship between political unrest, government actions, and digital freedoms.

This project builds a reproducible, low‑cost data engineering pipeline using Bruin to:

- Ingest Google Transparency Report takedown data (filtered to Kenya),

- Enrich it with ACLED conflict/protest events and global social media censorship incidents,
        
- Compute temporal and geospatial alignments across datasets,
        
- Generate a composite Civil Liberties Risk Index that quantifies suppression patterns,
        
- Produce interactive dashboards highlighting trends in Kenya (2024–2026) and offering a template for global replication.

Core question: How do government takedown requests correlate with political events, protests, and conflict spikes in Kenya — and what lessons can be drawn for other countries facing similar dynamics?

## 🔹 Why It Matters Globally

Although Kenya is the focal case study, the methodology is globally relevant:

- Governments worldwide are increasing reliance on takedown requests and censorship measures.
    
- Researchers and journalists need reproducible tools to audit these actions.
    
- Civil society organizations benefit from transparent dashboards that highlight suppression patterns.
    
- Data engineers can showcase how modern pipelines (Bruin, DuckDB, BigQuery, Terraform) can be applied to socially impactful problems.

## Audience:

- Researchers studying freedom of expression and digital rights
    
- Journalists investigating censorship and government transparency
    
- Civil society and policy analysts monitoring democratic resilience
    
- Data engineers and students seeking reproducible, impactful pipeline projects

Built end‑to‑end with Bruin — ingestion, SQL/Python transforms, quality checks, orchestration — this project demonstrates how reproducible pipelines can illuminate one of the most pressing issues of our time: the balance between state authority and civil liberties in the digital age.

---

## 📑 Table of Contents
1. [Tech Stack](#tech-stack)
2. [Project Architecture](#project-architecture)
3. [Entity Relationship Diagram (ERD)](#entity-relationship-diagram-erd)
4. [Project Structure](#project-structure)
5. [Data Access](#data-access)
6. [Datasets](#datasets)
7. [Dataset Lineage](#dataset-lineage)
8. [Data-Modelling](#data-modelling)
9. [Data Pipeline](#data-pipeline)
10. [Ethics and Responsible Use](#ethics-and-responsible-use)
11. [Dashboard + Visualizations](#dashboard--visualizations)
12. [Setup Instructions](#setup-instructions)
13. [Milestones and Next Steps](#milestones-and-next-steps)
14. [Contact Information](#contact-information)



---

⚙️
## Tech Stack

- Bruin → ingestion, transformations, orchestration, lineage
    
- DuckDB (Dev) → local, low‑cost, reproducible runs
    
- GCP (Prod) → scalable deployment
    
- GCS (data lake)
    
- BigQuery (warehouse)
    
- Bruin Cloud Dashboard (pipeline monitoring, lineage, orchestration)
    
- Cloud Run + Streamlit (public dashboard)
    
- Terraform → infrastructure as code (GCS, BigQuery, IAM, Cloud Run)
    
- Python 3.12 + uv → dependency management
    
- Streamlit → interactive dashboards
    
- GitHub Actions → CI/CD (tests, linting, infra deploy, app deploy)

---
  
🏗
## Project Architecture

```mermaid
flowchart TD
    subgraph Dev[Development - Local]
        A[Raw CSVs] --> B[DuckDB Staging]
        B --> C[DuckDB Marts]
        C --> D[Streamlit Dashboard]
    end

    subgraph Prod[Production - GCP]
        E[GCS Buckets] --> F[BigQuery Staging]
        F --> G[BigQuery Marts]
        G --> H[Streamlit on Cloud Run]
        G --> I[Bruin Cloud Dashboard]
    end

    Dev --> Prod
```
### Environments
This pipeline is designed for reproducibility across environments:

### Development (DuckDB):  
Runs locally with DuckDB for low‑cost experimentation, fast iteration, and reproducibility. Ideal for students, researchers, and collaborators without cloud credits.

### Production (GCP + Bruin Cloud):

- GCS → raw/staging storage

- BigQuery → facts + marts

- Bruin Cloud Dashboard → monitoring, lineage, orchestration

- Cloud Run + Streamlit → public dashboard

This dual setup mirrors industry practice: DuckDB ensures reproducibility, while GCP provides scalability and durability. Together, they guarantee transparent infrastructure and examiner‑friendly reproducibility.

---

📊
## Entity Relationship Diagram (ERD)
```mermaid
erDiagram
    %% RAW INGESTION
    google_transparency_raw {
        string request_id
        date date
        string country
        string product
        string reason
        int items_requested
    }
    lumen_generated {
        string lumen_id
        date date
        string country
        string recipient
        string reason
    }
    ooni_raw {
        string measurement_id
        date date
        string country
        string test_name
        string input
    }
    acled_raw {
        string event_id
        date date
        string country
        string admin1
        string event_type
        int fatalities
    }

    %% STAGING
    stg_google_transparency {
        string request_id
        string country
        string product
        string reason
        string period
    }
    stg_lumen {
        string lumen_id
        string country
        string recipient
        string reason
        string period
    }
    stg_ooni {
        string measurement_id
        string country
        string test_name
        string input
        string period
    }
    stg_acled {
        string event_id
        string country
        string admin1
        string event_type
        int fatalities
        string period
    }

    %% DIMENSIONS
    dims_country {
        string country_id
        string country_code
        string country_name
    }
    dims_platform {
        string platform_id
        string platform_name
    }
    dims_event_type {
        string event_type_id
        string event_type
    }
    dims_reasons {
        string reason_id
        string reason_name
    }
    dims_periods {
        string period_id
        string period
        string half_year_label
    }

    %% FACTS
    fact_takedown_requests {
        string request_id
        string country_id
        string platform_id
        string reason_id
        string period_id
        int request_count
        int items_requested
    }
    fact_lumen_platforms {
        string lumen_id
        string country_id
        string platform_id
        string reason_id
        string period_id
    }
    fact_censorship_tests {
        string measurement_id
        string country_id
        string event_type_id
        string period_id
    }
    fact_conflict_events {
        string event_id
        string country_id
        string event_type_id
        string period_id
        int event_count
        int fatalities
    }

    %% MART
    civil_liberties_mart {
        string country_id
        string period_id
        int takedown_requests
        int lumen_requests
        int censorship_tests
        int conflict_events
        int fatalities
    }

    %% RELATIONSHIPS
    google_transparency_raw ||--o{ stg_google_transparency : feeds
    lumen_generated ||--o{ stg_lumen : feeds
    ooni_raw ||--o{ stg_ooni : feeds
    acled_raw ||--o{ stg_acled : feeds

    stg_google_transparency ||--o{ fact_takedown_requests : transforms
    stg_lumen ||--o{ fact_lumen_platforms : transforms
    stg_ooni ||--o{ fact_censorship_tests : transforms
    stg_acled ||--o{ fact_conflict_events : transforms

    dims_country ||--o{ fact_takedown_requests : joins
    dims_country ||--o{ fact_lumen_platforms : joins
    dims_country ||--o{ fact_censorship_tests : joins
    dims_country ||--o{ fact_conflict_events : joins

    dims_platform ||--o{ fact_takedown_requests : joins
    dims_platform ||--o{ fact_lumen_platforms : joins

    dims_event_type ||--o{ fact_conflict_events : joins
    dims_event_type ||--o{ fact_censorship_tests : joins

    dims_reasons ||--o{ fact_takedown_requests : joins
    dims_reasons ||--o{ fact_lumen_platforms : joins

    dims_periods ||--o{ fact_takedown_requests : joins
    dims_periods ||--o{ fact_lumen_platforms : joins
    dims_periods ||--o{ fact_censorship_tests : joins
    dims_periods ||--o{ fact_conflict_events : joins

    fact_takedown_requests ||--o{ civil_liberties_mart : aggregates
    fact_lumen_platforms ||--o{ civil_liberties_mart : aggregates
    fact_censorship_tests ||--o{ civil_liberties_mart : aggregates
    fact_conflict_events ||--o{ civil_liberties_mart : aggregates
```


---
📂
## Project Structure
```
civil-liberties-censorship-kenya-bruin/
├── bruin/
│   ├── assets/ingest/          # ingestion YAML/SQL/Python for raw sources
│   │   ├── google_transparency_ingest.yml
│   │   ├── lumen_generated_ingest.yml
│   │   ├── ooni_ingest.yml
│   │   └── acled_ingest.yml
│   ├── assets/staging/         # cleaning & normalization
│   │   ├── stg_google_transparency.sql
│   │   ├── stg_lumen.sql
│   │   ├── stg_ooni.sql
│   │   └── stg_acled.sql
│   ├── assets/dims/            # reference dimensions
│   │   ├── dims_country.sql
│   │   ├── dims_platform.sql
│   │   ├── dims_event_type.sql
│   │   ├── dims_reasons.sql
│   │   └── dims_periods.sql
│   ├── assets/facts/           # harmonized fact tables
│   │   ├── fact_takedown_requests.sql
│   │   ├── fact_lumen_platforms.sql
│   │   ├── fact_censorship_tests.sql
│   │   └── fact_conflict_events.sql
│   ├── assets/marts/           # enriched tables, risk index
│   │   └── civil_liberties_mart.sql
│   ├── assets/reporting/       # analytical views
│   │   ├── view.top_platforms_requests.sql
│   │   ├── view.conflict_vs_takedowns.sql
│   │   ├── view.censorship_vs_requests.sql
│   │   └── view.narrative_summary.sql
│   └── pipeline.yml            # DAG definition for Bruin
├── src/streamlit_app/          # app.py + visualizations.py
│   ├── app.py
│   └── visualizations.py
├── infra/                      # Terraform + GCP infra
│   ├── main.tf
│   ├── variables.tf
│   ├── terraform.tfvars
│   ├── provider.tf
│   ├── outputs.tf
│   └── modules/
│       ├── gcs/
│       ├── bigquery/
│       └── iam/
├── tests/                      # asset tests, pytest
├── docs/                       # documentation + diagrams
│   ├── data-modelling.md        # full rationale, joins, keys, quality checks
│   ├── erd.md                   # ERD diagram (Mermaid)
│   ├── lineage.md               # dataset lineage diagram (Mermaid + table)
│   ├── project-structure.md     # folder tree + rationale
│   └── screenshots/             # Bruin lineage, flows, dashboards
├── .env.example
├── Makefile                     # infra-apply, run-pipeline, deploy-app
├── pyproject.toml
├── uv.lock
├── README.md
└── LICENSE

```
---
📌 
## Data Access

### Lumen Database Access
The Lumen Database aggregates takedown requests across multiple platforms. However, access requires approval and is not guaranteed for all researchers. Since direct access was not available during this project, we generated mock Lumen‑style data via a Python script to ensure pipeline completeness and reproducibility.

### Why Mock Data?
- Keeps the ERD and lineage tables intact (stg_lumen.sql, fact_lumen_platforms.sql).

- Ensures the pipeline runs end‑to‑end without missing assets.

- Dates and fields are aligned to the 2024–2026 timeframe for consistency with other datasets.

- Demonstrates reproducibility, even when real data is gated.

### How to Swap for Real Sources
- Replace mock_lumen_data.csv with actual Lumen exports once access is granted.

- Adjust ingestion assets (bruin/assets/ingest/lumen_raw.py) to point to the real CSV/API.

- Pipeline will run unchanged — staging, facts, marts and reporting are schema‑compatible.

### Optional Enrichment
If Lumen access remains unavailable, similar transparency datasets can be substituted although fragmented for the time period of the project scope:

- Meta Transparency Center (Facebook/Instagram government requests).

- X (Twitter) Transparency Archive (government takedown summaries).

- Google Transparency Report (already included).
---

📊
## Datasets

| Dataset | Source | Access Method | Coverage Focus | Key Fields |
| --- | --- | --- | --- | --- |
| Google Transparency Report | [Google Transparency](https://transparencyreport.google.com/government-removals/data) | CSV download (semi‑annual files) | Global, filter Kenya | request_id, date, requester, platform, motive, items_requested, action_taken |
| ACLED (Armed Conflict Location & Event Data) | [ACLED Export Tool](https://acleddata.com/data-export-tool/) (myACLED account required) | CSV export tool or API | Kenya events | event_id, event_date, county, event_type, actors, fatalities |
| Lumen Database (Takedown Requests) | [Lumen Database](https://lumendatabase.org) | CSV/JSON export, API | Global, filter Kenya | lumen_id, date, platform, request_type, requester, outcome |
| OONI (Open Observatory of Network Interference) | [OONI Data](https://ooni.org/data/) | API / CSV download | Kenya‑specific | test_id, date, platform, shutdown_type, measurement |
| WHO Infodemic Proxies *(Optional)* | WHO datasets / reports | Manual CSV / API | Kenya‑specific | misinfo_event_id, date, topic, severity |

---

📊
## Dataset Lineage
```mermaid
flowchart TD
    %% RAW INGESTION
    A1[Google Transparency Raw] --> B1[stg_google_transparency]
    A2[Lumen Generated Data] --> B2[stg_lumen]
    A3[OONI Raw Measurements] --> B3[stg_ooni]
    A4[ACLED Raw Events] --> B4[stg_acled]

    %% STAGING TO FACTS
    B1 --> C1[fact_takedown_requests]
    B2 --> C2[fact_lumen_platforms]
    B3 --> C3[fact_censorship_tests]
    B4 --> C4[fact_conflict_events]

    %% DIMENSIONS
    D1[dims_country]
    D2[dims_platform]
    D3[dims_event_type]
    D4[dims_reasons]
    D5[dims_periods]

    %% FACTS TO MART
    C1 --> E[civil_liberties_mart]
    C2 --> E
    C3 --> E
    C4 --> E

    %% DIM JOINS
    D1 --> C1
    D1 --> C2
    D1 --> C3
    D1 --> C4

    D2 --> C1
    D2 --> C2

    D3 --> C3
    D3 --> C4

    D4 --> C1
    D4 --> C2

    D5 --> C1
    D5 --> C2
    D5 --> C3
    D5 --> C4

    %% REPORTING VIEWS
    E --> F1[view.top_platforms_requests]
    E --> F2[view.conflict_vs_takedowns]
    E --> F3[view.censorship_vs_requests]
    E --> F4[view.narrative_summary]
```



## 📊 Dataset Lineage with Environments
| Dataset (Raw) | Staging Table | Fact Table | Reporting Layer | DEV (DuckDB) | PROD (GCP) |
| --- | --- | --- | --- | --- | --- |
| **Google Transparency Report** | ``stg_google_transparency.sql`` | ``fact_takedown_requests.sql`` | ``civil_liberties_mart.sql`` | DuckDB local tables | BigQuery dataset ``fact_takedown_requests`` |
| **Lumen (Generated Data)** | ``stg_lumen.sql`` | ``fact_lumen_platforms.sql`` | ``civil_liberties_mart.sql`` | DuckDB local tables | BigQuery dataset ``fact_lumen_platforms`` |
| **OONI (Network Interference)** | ``stg_ooni.sql`` | ``fact_censorship_tests.sql`` | ``civil_liberties_mart.sql`` | DuckDB local tables | BigQuery dataset ``fact_censorship_tests`` |
| **ACLED Conflict Events** | ``stg_acled.sql`` | ``fact_conflict_events.sql`` | ``civil_liberties_mart.sql`` | DuckDB local tables | BigQuery dataset ``fact_conflict_events`` |
| **Dims (Reference Tables)** | ``dims_country.sql``, ``dims_event_type.sql``, ``dims_platform.sql``, ``dims_reasons.sql``, ``dims_periods.sql`` | Join into facts for normalization | Used in reporting joins | DuckDB local tables | BigQuery datasets ``dims_*`` |

**Notes**:
- Google: Download full historical CSVs → filter Kenya in staging.
- ACLED: Free registration required for export tool/API.
- All datasets ingested via Bruin (API,CSV file/URL, HTTP connectors).

---
🔢
## Data Modelling

I integrated **Google Transparency**, **generated Lumen data**, **OONI**, and **ACLED** datasets into a unified civil liberties mart.  
The pipeline stages raw ingestion, harmonizes facts and dimensions, and produces examiner‑friendly reporting views.

- **Facts:** takedown requests, lumen platforms, censorship tests, conflict events  
- **Dims:** country, platform, event type, reasons, periods  
- **Mart:** integrated civil liberties dataset  
- **Views:** top platforms, conflict vs takedowns, censorship vs requests, narrative summary  

📖 For full details on ingestion rationale, joins, surrogate keys, and quality checks, see [data-modelling.md](./docs/data-modelling.md)
---

🔄
## Data Pipeline 

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
   Bruin cloud + Streamlit dashboard:  
       - Kenya county heatmap (takedowns + ACLED)  
       - Timeline (spikes vs known protest periods)  
       - Actor breakdown (e.g., CAK vs platforms)  
       - Risk index map & motive pie charts

---

⚖️
## Ethics and Responsible Use

- Data is public/aggregated — no personal information processed.
- Analysis is descriptive and neutral; no causal claims without evidence.
- Findings presented for transparency and research — not political advocacy.
- Users encouraged to verify sources and cite original datasets.

---

📊
## Dashboard & Visualizations

Kenya county heatmap (takedowns + ACLED)

- Timeline (spikes vs protests)
    
- Actor breakdown (CAK vs platforms)

- Risk index map & motive pie charts
    
    👉 Placeholder: screenshots to be added before submission.

---

🚀
## Setup Instructions

### Step 1: Clone the repo:
   ```bash
   git clone https://github.com/<your-username>/civil-liberties-and-Censorship-Analysis-with-Bruin.git
   cd civil-liberties-and-Censorship-Analysis-with-Bruin
  ```

### Step 2: Environment Setup
Python 3.12 + uv for dependency management.

- Install Bruin CLI.

- Create virtual environment:

```bash
uv venv source .venv/bin/activate
uv pip install -e ".[dev,test]"
  ```
- Add pyproject.toml + uv.lock for reproducibility.

### Step 3: Ingest Assets
  - ACLED Kenya CSV (via export tool) → place in data/raw/
  - Google Transparency CSV → place in data/raw/
  - Mendeley CSV → place in data/raw/
  - Optional: OONI/WHO → manual CSV ingestion.

Each ingestion asset defined in bruin/assets/ingest/.

### Step 4: Stage Assets
- Clean raw tables (dates, country filters).
- Normalize schema (Kenya counties, motives).
- Store in DuckDB (local .db file).
- SQL files in bruin/assets/staging/.

### Step 5: Analytical Marts
events_by_type: takedowns grouped by motive.
events_by_date: temporal alignment with ACLED protests.
events_by_region: geospatial join (Kenya counties).
risk_index: composite score (takedowns × conflict × social events).
SQL in bruin/assets/marts/.

### Step 6: Orchestration
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
### Step 7: Dashboard
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
### Step 8: Infrastructure
Terraform scripts in /terraform for GCP resources:
  - GCS (data lake).
  - BigQuery (warehouse).
  - Cloud Run (dashboard deployment).
Makefile commands:
  - Make infra-apply → deploy infra.
  - Make app-deploy → deploy Streamlit to Cloud Run.

### Step 9: CI/CD
workflow:
  - Run tests on push.
  - Lint + format with pre-commit.
  - Deploy infra + dashboard on tagged release.

### Step 11: Documentation
Update README.md with:
  - Architecture diagram.
  - Dataset sources.
  - Setup instructions.
  - Screenshots of Bruin lineage + dashboard.

### Step 12: Submission
Publish repo on GitHub.
Share in Zoomcamp Slack #projects.
Include screenshots + demo link (Cloud Run if deployed).

---

📅
## Milestones and Next Steps
[x] Ingestion assets defined

[x] Staging + marts built

[ ] Terraform infra applied

[ ] Dashboard screenshots added

[ ] CI/CD pipeline finalized

[ ] Submission package prepared

---

📬
## Contact Information
Project Owner: Samwel Njogu

Focus: Civil liberties, censorship analysis, reproducible pipelines

X: @sam_njogu9
