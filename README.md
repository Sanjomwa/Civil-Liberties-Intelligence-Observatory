# 🇰🇪 Kenya Civil Liberties & Censorship Observatory
### Tracking Digital Repression & Real-World Impact (June 2023 → June 2025)  
**Powered by Bruin | DuckDB | BigQuery | Streamlit**

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

## 🌍 Why This Matters

This is not just Kenya:
- Governments globally expanding censorship powers
- Lack of **reproducible analysis pipelines**
- Need for **auditable, transparent data systems**

This project provides a **reusable blueprint**.

---

## 👥 Audience

- Researchers (digital rights, governance)
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
        G --> I[Bruin Cloud]
    end

    DEV --> PROD
