# 🇰🇪 Kenya Civil Liberties & Censorship Observatory
### Tracking Digital Repression & Real-World Impact (June 2023 → June 2025)  
**Powered by Bruin | DuckDB | BigQuery | Streamlit**

---

## 📑 Table of Contents

1. [Problem Statement](#-problem-statement)
2. [Why It Matters](#-why-it-matters)
3. [Audience](#-audience)
4. [Tech Stack](#-tech-stack)
5. [Architecture](#-architecture)
6. [Data Pipeline (DAG)](#-data-pipeline-dag)
7. [Data Model Overview](#-data-model-overview)
8. [ERD & Lineage](#-erd--lineage)
9. [Project Structure](#-project-structure)
10. [Datasets](#-datasets)
11. [Data Modelling](#-data-modelling)
12. [Setup Instructions](#-setup-instructions)
13. [Infrastructure (Terraform)](#-infrastructure-terraform)
14. [Dashboard](#-dashboard)
15. [Ethics](#-ethics)
16. [Roadmap](#-roadmap)
17. [Contact](#-contact)
18. [License](#-license)
19. [Acknowledgements](#-acknowledgements)

---

## 🎯 Problem Statement

Governments increasingly request online content removal. While sometimes justified, these actions can undermine **freedom of expression and civil liberties**.

Kenya offers a critical case:
- Rising **takedown requests** (Google Transparency)
- Increasing **conflict & protests** (ACLED)
- Detected **network interference** (OONI)

👉 Core Question:
> How do censorship actions correlate with political unrest and conflict dynamics?

---

## 🌍 Why It Matters

- Governments globally expanding censorship powers  
- Lack of **reproducible analysis pipelines**  
- Need for **transparent, auditable data systems**  

This project provides a **reusable blueprint**.

---

## 👥 Audience

- Researchers (digital rights)
- Journalists (investigations)
- Civil society (accountability)
- Data engineers (real-world pipelines)

---

## ⚙️ Tech Stack

| Layer | Tools |
|------|------|
| Orchestration | Bruin |
| Local Dev | DuckDB |
| Cloud | GCP (BigQuery, GCS) |
| Infra | Terraform |
| App | Streamlit |
| CI/CD | GitHub Actions |
| Python | 3.12 + uv |

---

## 🏗️ Architecture

```mermaid
flowchart TD
    subgraph DEV[Local Development]
        A[Raw Data] --> B[DuckDB Staging]
        B --> C[DuckDB Facts/Marts]
        C --> D[Streamlit App]
    end

    subgraph PROD[GCP Production]
        E[GCS] --> F[BigQuery Staging]
        F --> G[BigQuery Facts/Marts]
        G --> H[Streamlit Cloud Run]
        G --> I[Bruin Cloud Dashboard]
    end



    DEV --> PROD
