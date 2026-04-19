# 📐 Data Modelling — Civil Liberties & Censorship Observatory

## 🧭 Overview

This document defines the **dimensional data model** used to integrate:
- Google Transparency Reports
- Lumen (mock legal requests)
- OONI network interference data
- ACLED conflict events

The model is designed to support:
- Cross-domain correlation analysis
- Time-series alignment
- Country-level comparisons
- Reproducible analytics in DuckDB and BigQuery

---

## 🏗️ 1. Data Architecture Pattern

This project follows a **Kimball-style dimensional modeling approach**:

Raw Sources → Staging → Facts → Dimensions → Mart → Reporting Views


### Key Principles:
- Each fact table represents a **single analytical grain**
- Dimensions are **conformed across all facts**
- Mart layer is **denormalized for analytics**
- No heavy computation in reporting layer

---

## 📊 2. Fact Tables

### 2.1 fact_takedown_requests

**Grain:** One row per (request_id, country, platform, period)

| Column | Type | Description |
|------|------|-------------|
| request_id | string | Unique takedown request |
| country_id | string | FK → dim_country |
| platform_id | string | FK → dim_platform |
| reason_id | string | FK → dim_reason |
| period_id | string | FK → dim_period |
| request_count | int | Number of requests |
| items_requested | int | Content items affected |

---

### 2.2 fact_lumen_requests

**Grain:** One row per Lumen legal request event

| Column | Type | Description |
|------|------|-------------|
| lumen_id | string | Unique request ID |
| country_id | string | FK → dim_country |
| reason_id | string | FK → dim_reason |
| period_id | string | FK → dim_period |

---

### 2.3 fact_censorship_tests (OONI)

**Grain:** One row per measurement

| Column | Type | Description |
|------|------|-------------|
| measurement_id | string | Unique probe measurement |
| country_id | string | FK → dim_country |
| period_id | string | FK → dim_period |

---

### 2.4 fact_conflict_events (ACLED)

**Grain:** One row per conflict event

| Column | Type | Description |
|------|------|-------------|
| event_id | string | Unique ACLED event |
| country_id | string | FK → dim_country |
| event_type_id | string | FK → dim_event_type |
| period_id | string | FK → dim_period |
| fatalities | int | Number of deaths |

---

## 🧱 3. Dimension Tables (Conformed Dimensions)

### 3.1 dim_country
- Normalized country names
- ISO codes for consistency

```text
country_id (PK)
country_name
iso_code
```

---

### 3.2 dim_platform
Used for mapping digital platforms targeted by takedown requests.
```
platform_id (PK)
platform_name
```

---

### 3.3 dim_event_type
Used for ACLED classification.
```
event_type_id (PK)
event_type
```

---

### 3.4 dim_reason
Standardized classification of censorship or legal justification.
```
reason_id (PK)
reason_name
```

---

### 3.5 dim_period
Temporal alignment layer across all datasets.
```
period_id (PK)
period (YYYY-MM)
half_year_label
```

---

## 🧮 4. Mart Layer — civil_liberties_mart
Purpose:
A fully denormalized analytical dataset used for dashboards and reporting.
Grain:
One row per:
```
(country_id, period_id)
```
| Column            | Description                  |
| ----------------- | ---------------------------- |
| country_id        | Geography                    |
| period_id         | Time period                  |
| takedown_requests | Google + aggregated requests |
| lumen_requests    | Legal requests               |
| censorship_tests  | OONI anomalies               |
| conflict_events   | ACLED events                 |
| fatalities        | Conflict severity metric     |
 
---

## 🔗 5. Join Strategy
All facts are joined through conformed dimensions:

country_id → dim_country
period_id → dim_period
reason_id → dim_reason
platform_id → dim_platform
event_type_id → dim_event_type

This ensures:
  - No duplication across facts
  - Consistent aggregation logic
  - Cross-dataset comparability
    
---

## 🧠 6. Data Grain Rules
| Layer   | Grain                           |
| ------- | ------------------------------- |
| Raw     | Source-specific event           |
| Staging | Cleaned record per dataset      |
| Facts   | One event per analytical entity |
| Mart    | One row per country-period      |

---

## 🧹 7. Data Quality Checks

Implemented in DuckDB + Bruin:

Mandatory rules:
NOT NULL constraints on all keys
Unique constraints on all primary IDs
Non-negative values for:
request_count
fatalities
Validation examples:
```sql
-- Ensure no duplicate events
SELECT request_id, COUNT(*)
FROM fact_takedown_requests
GROUP BY request_id
HAVING COUNT(*) > 1;
```

---

## ⏱️ 8. Temporal Alignment Logic

All datasets are normalized to:

period = YYYY-MM
Derived from raw timestamps
Ensures alignment across:
ACLED weekly events
Google semiannual reports
OONI daily measurements

----

## ⚠️ 9. Design Decisions

Why no direct joins between facts?
 - Prevents double counting
 - Maintains independence of event domains
 - Why a mart layer?
 - Enables fast dashboard queries
 - Removes join complexity from BI layer
 - Why DuckDB + Parquet locally?
 - Fast iteration
 - Columnar performance
 - Reproducible transformations

---

## 📌 10. Summary

This model enables:
  - Cross-domain civil liberties analysis
  - Temporal correlation between censorship and conflict
  - Scalable migration from DuckDB → BigQuery
  - Reproducible, audit-friendly data engineering pipeline
