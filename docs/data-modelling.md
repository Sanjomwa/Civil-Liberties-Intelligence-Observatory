# Data Modelling Documentation

## 1. Ingestion Layer
We ingested or generated four datasets, each chosen for its relevance to civil liberties:

- **Google Transparency Reports**
  - Source: Google’s public transparency portal
  - Why: Official counts of government takedown requests by product/platform
  - Rationale: Provides baseline for platform‑level censorship activity
  - Keys: `country`, `product`, `reason`, `period`
  - Quality checks: `not_null` on country, product, reason; `non_negative` on request counts

- **Lumen Database**
  - Source: **Generated mock data** (not ingested via API/web/http) to simulate takedown requests
  - Why: Complements Google data with broader legal requests across platforms
  - Rationale: Needed to demonstrate harmonization of multiple request sources
  - Keys: `recipient`, `reason`, `request_id`, `period`
  - Quality checks: `unique` on request_id; `not_null` on recipient and reason

- **OONI (Open Observatory of Network Interference)**
  - Source: OONI Probe measurements
  - Why: Captures censorship anomalies at the network level
  - Rationale: Provides ground‑truth evidence of censorship beyond formal requests
  - Keys: `country`, `test_name`, `measurement_id`, `period`
  - Quality checks: `not_null` on test_name and country; `unique` on measurement_id

- **ACLED (Armed Conflict Location & Event Data)**
  - Source: ACLED conflict event dataset
  - Why: Provides context on political violence and fatalities
  - Rationale: Enables correlation between conflict intensity and censorship activity
  - Keys: `country`, `admin1`, `event_type`, `period`
  - Quality checks: `non_negative` on fatalities and event_count; `not_null` on event_type

---

## 2. Staging Layer
Each staging file:
- Cleans raw ingestion (trimming, lowercasing, deduplication).
- Aligns schema to shared keys (`country`, `period`, `half_year_label`).
- Prepares data for fact tables with minimal transformations.

---

## 3. Fact Layer
We define harmonized fact tables:

- **fact.takedown_requests**  
  Joins: `country_id` → `dims.country`, `platform_id` → `dims.platform`, `reason_id` → `dims.reasons`, `period_id` → `dims.periods`  
  Keys: surrogate keys from dims + natural keys from staging  
  Quality checks: `not_null` on country, product, reason; `non_negative` on request counts

- **fact.lumen_platforms**  
  Joins: `country_id` → `dims.country`, `platform_id` → `dims.platform`, `reason_id` → `dims.reasons`, `period_id` → `dims.periods`  
  Keys: surrogate keys + `request_id`  
  Quality checks: `unique` on request_id; `not_null` on recipient and reason

- **fact.censorship_tests**  
  Joins: `country_id` → `dims.country`, `event_type_id` → `dims.event_type`, `period_id` → `dims.periods`  
  Keys: surrogate keys + `measurement_id`  
  Quality checks: `unique` on measurement_id; `not_null` on test_name

- **fact.conflict_events**  
  Joins: `country_id` → `dims.country`, `event_type_id` → `dims.event_type`, `period_id` → `dims.periods`  
  Keys: surrogate keys + natural keys (`admin1`, `event_type`)  
  Quality checks: `non_negative` on fatalities and event_count; `valid_period_range` custom check (Jun 2023–Jun 2025)

---

## 4. Dimension Layer
We created five core dims:

- **dims.country**  
  Surrogate key: `country_id`  
  Joins: all facts on `country_id`  
  Quality checks: `unique` and `not_null`

- **dims.platform**  
  Surrogate key: `platform_id`  
  Joins: takedown_requests + lumen_platforms  
  Quality checks: `unique` and `not_null`

- **dims.event_type**  
  Surrogate key: `event_type_id`  
  Joins: conflict_events + censorship_tests  
  Quality checks: `unique` and `not_null`

- **dims.reasons**  
  Surrogate key: `reason_id`  
  Joins: takedown_requests + lumen_platforms  
  Quality checks: `unique` and `not_null`

- **dims.periods**  
  Surrogate key: `period_id`  
  Joins: all facts  
  Quality checks: `valid_period_range` (Jun 2023–Jun 2025)

---

## 5. Mart Layer
- **mart.civil_liberties.sql** integrates all facts + dims
- Joins: full outer joins on `country_id` + `period_id`
- Aggregates: takedown requests, censorship tests, conflict events, fatalities
- Quality checks: enforced via fact tables, mart inherits validated data

---

## 6. Reporting Layer
Analytical views simplify storytelling:
- **Top Platforms by Requests** → ranks platforms per country/period
- **Conflict vs Takedowns** → compares conflict events/fatalities with takedown requests
- **Censorship vs Requests** → compares OONI anomalies with takedown requests
- **Narrative Summary** → generates examiner‑friendly text blocks

---

