<img width="5797" height="2819" alt="erd_clean" src="https://github.com/user-attachments/assets/bd8b2379-46e5-42d0-abf1-43000daa35f6" /># 🇰🇪 Kenya Civil Liberties & Censorship Observatory
---

### Tracking Digital Repression & Real-World Impact (June 2023 → June 2025)  
**Powered by Bruin | DuckDB | BigQuery | Streamlit**
---


## 🎯
## Problem Statement

Governments increasingly request online content removal. While sometimes justified, these actions can undermine **freedom of expression and civil liberties**.

Kenya offers a critical case:
- Rising **takedown requests** (Google Transparency)
- Increasing **conflict & protests** (ACLED)
- Detected **network interference** (OONI)

👉 Core Question:
```yaml
> How do censorship actions correlate with political unrest and conflict dynamics?
```


---

## 📑 Table of Contents

1. [Why It Matters](#-why-it-matters)
2. [Audience](#-audience)
3. [Tech Stack](#-tech-stack)
4. [Architecture](#-architecture)
5. [Data Pipeline (DAG)](#-data-pipeline-dag)
6. [Data Model Overview](#-data-model-overview)
7. [ERD & Lineage](#-erd--lineage)
8. [Project Structure](#-project-structure)
9. [Datasets](#-datasets)
10. [Data Modelling](#-data-modelling)
11. [Setup Instructions](#-setup-instructions)
12. [Infrastructure (Terraform)](#-infrastructure-terraform)
13. [Dashboard](#-dashboard)
14. [Ethics](#-ethics)
15. [Roadmap](#-roadmap)
16. [Contact](#-contact)
17. [License](#-license)
18. [Acknowledgements](#-acknowledgements)

---

## 🌍
## Why It Matters

- Governments globally expanding censorship powers  
- Lack of **reproducible analysis pipelines**  
- Need for **transparent, auditable data systems**  

This project provides a **reusable blueprint**.

---

## 👥 
## Audience

- Researchers (digital rights)
- Journalists (investigations)
- Civil society (accountability)
- Data engineers (real-world pipelines)

---

## ⚙️ 
## Tech Stack 

| Layer                      | Tools                         | Role in System                                                               |
| -------------------------- | ----------------------------- | ---------------------------------------------------------------------------- |
| **Workflow Orchestration** | Bruin                         | DAG execution, asset dependency graph, scheduling, lineage tracking          |
| **Local Compute Engine**   | DuckDB                        | Fast analytical engine for raw ingestion, validation, parquet transformation |
| **Data Formats**           | Parquet                       | Columnar storage, partitioning, cloud transfer format                        |
| **Cloud Storage Layer**    | GCS (Google Cloud Storage)    | Raw + processed dataset lake                                                 |
| **Warehouse**              | BigQuery                      | Staging → intermediate → marts (analytics layer)                             |
| **Infrastructure as Code** | Terraform                     | GCP provisioning (IAM, GCS, BigQuery, Cloud Run)                             |
| **Dashboard Layer**        | Streamlit                     | Interactive analytics + storytelling layer                                   |
| **Deployment**             | Cloud Run                     | Containerized dashboard hosting                                              |
| **Dev Environment**        | VSCode + Codespaces + Bash    | Local execution, debugging, shell orchestration                              |
| **Data Processing**        | Python 3.12                   | Transformations, validation, orchestration glue                              |
| **Package Management**     | uv                            | Fast dependency resolution and reproducibility                               |
| **CI/CD**                  | GitHub Actions                | Testing, linting, infra deployment, app deployment                           |
| **Data Quality**           | SQL + Python validation rules | NOT NULL, uniqueness, schema enforcement                                     |
| **Version Control**        | Git + GitHub                  | Collaboration + reproducibility                                              |
| **Documentation**          | Markdown + Mermaid            | Architecture + lineage + ERD visualization                                   |


---

🏗️
##  Architecture
  DUCKDB does: 
    •	raw validation 
    •	parquet normalization 
    •	local transformation sandbox 
  GCP does: 
    •	staging 
    •	intermediate + marts 

<img width="2022" height="2225" alt="mermaid-diagram_architecture" src="https://github.com/user-attachments/assets/96140493-b31c-4c04-b7e9-1e97394e05df" />

---

## 🚧
## Data Pipeline (DAG)

<img width="5707" height="908" alt="data_pipeline_DAG" src="https://github.com/user-attachments/assets/19ca0498-0dd2-42a0-9729-cdaecc2b54e4" />

Defined in:
```yaml
pipeline.yml
```
Schedule: @daily
Start date: 2023-06-01
Targets: DuckDB (dev), BigQuery (prod)

---

🧠 Data Model Overview
Layers
| Layer   | Purpose                  |
| ------- | ------------------------ |
| Raw     | Source ingestion         |
| Staging | Cleaning + normalization |
| Dims    | Reference tables         |
| Facts   | Event-level data         |
| Mart    | Unified analytics        |

---

📐
##ERD & Lineage

<img width="5797" height="2819" alt="erd_clean" src="https://github.com/user-attachments/assets/4fddc6a5-cb7d-4f8f-ba4b-f4eff0741afd" />


---

📂
## Project Structure
.
├── .vscode/
├── Bruin/
│   └── assets/
├── docs/
│   ├── data-modelling.md
│   ├── erd-lineage.md
│   └── analysts-questions-playbook.md
├── infra/
│   ├── modules/
│   │   ├── bigquery/
│   │   ├── gcs/
│   │   └── iam/
│   ├── main.tf
│   ├── provider.tf
│   ├── variables.tf
│   └── terraform.tfvars
├── streamlit/
│   ├── pages/
│   ├── utils/
│   ├── app.py
│   └── requirements.txt
├── pipeline.yml
├── requirements.txt
├── README.md
└── LICENSE

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

| Dataset             | Purpose              |
| ------------------- | -------------------- |
| Google Transparency | Government takedowns |
| Lumen (mock)        | Legal requests       |
| OONI                | Network censorship   |
| ACLED               | Conflict events      |

## 📊
## Dataset Lineage
<img width="3609" height="1906" alt="DATA_LINEAGE" src="https://github.com/user-attachments/assets/6da21053-173d-44e2-88bb-f80ebfd1bf46" />

---

##📊 
##Dataset Lineage with Environments

| Dataset (Raw) | Staging Layer | Fact Layer | Reporting Layer | DEV (DuckDB) | PROD (GCP) |
| --- | --- | --- | --- | --- | --- |
| **Google Transparency Report** | `stg_google_transparency.sql` | `fact_takedown_requests.sql` | `civil_liberties_mart` | Raw tables → validation → parquet | BigQuery `fact_takedown_requests` |
| **Lumen (Mock / Generated)** | `stg_lumen.sql` | `fact_lumen_requests.sql` | `civil_liberties_mart` | Local generation + validation | BigQuery `fact_lumen_requests` |
| **OONI Network Measurements** | `stg_ooni.sql` | `fact_censorship_tests.sql` | `civil_liberties_mart` | DuckDB transforms + parquet export | BigQuery `fact_censorship_tests` |
| **ACLED Conflict Events** | `stg_acled.sql` | `fact_conflict_events.sql` | `civil_liberties_mart` | Local cleaning + enrichment | BigQuery `fact_conflict_events` |
| **Dimensions (Shared)** | `dim_country.sql`, `dim_event_type.sql`, `dim_platform.sql`, `dim_reason.sql`, `dim_period.sql` | Joined into all facts | Used across mart layer | DuckDB reference tables | BigQuery `dim_*` datasets |
| **Mart Layer** | - | Aggregated from all facts | `civil_liberties_mart.sql` | Local dev aggregation view | BigQuery reporting view |

## 🔢 
## Data Modelling

This project implements a **multi-source dimensional model** that integrates:
- Google Transparency takedown requests
- Lumen (mocked legal request dataset)
- OONI network interference measurements
- ACLED conflict event data

All datasets are harmonized into a **conformed dimensional model** designed for cross-domain analysis of civil liberties, censorship, and political instability.

### 🧱 Model Architecture

- **Facts (event-centric tables)**  
  - Takedown requests (Google Transparency)  
  - Lumen legal requests  
  - OONI censorship/anomaly measurements  
  - ACLED conflict events  

- **Dimensions (conformed reference tables)**  
  - Country (geo normalization + ISO mapping)  
  - Platform (Google, YouTube, etc.)  
  - Event Type (conflict classification)  
  - Reason (legal / policy categorization)  
  - Period (time alignment across datasets)  

- **Mart Layer (Analytics-ready dataset)**  
  A unified dataset (`civil_liberties_mart`) enabling:
  - Cross-domain correlation (conflict vs censorship)
  - Temporal trend analysis
  - Country-level comparison (Kenya vs global patterns)

- **Reporting Views**
  - Top platforms targeted by takedowns  
  - Conflict intensity vs censorship activity  
  - Censorship vs government requests correlation  
  - Narrative summary layer for dashboards  

📖 Full schema design, joins, grain definitions, surrogate keys, and validation rules are documented in:
👉 [`docs/data-modelling.md`](./docs/data-modelling.md)
