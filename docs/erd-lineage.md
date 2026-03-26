# 📐 **ERD and Dataset Lineage**

## 🗂️ **Entity Relationship Diagram (ERD)**

```mermaid
erDiagram
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
