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

### fact.takedown_requests

```sql
SELECT f.request_id,
       d.country_name,
       p.platform_name,
       r.reason_name,
       pr.period,
       f.request_count
FROM fact_takedown_requests f
JOIN dims_country d ON f.country_id = d.country_id
JOIN dims_platform p ON f.platform_id = p.platform_id
JOIN dims_reasons r ON f.reason_id = r.reason_id
JOIN dims_periods pr ON f.period_id = pr.period_id;
```

### fact.lumen_platforms

```sql
SELECT f.lumen_id,
       d.country_name,
       p.platform_name,
       r.reason_name,
       pr.period
FROM fact_lumen_platforms f
JOIN dims_country d ON f.country_id = d.country_id
JOIN dims_platform p ON f.platform_id = p.platform_id
JOIN dims_reasons r ON f.reason_id = r.reason_id
JOIN dims_periods pr ON f.period_id = pr.period_id;
```

### fact.censorship_tests
```sql
SELECT f.measurement_id,
       d.country_name,
       e.event_type,
       pr.period
FROM fact_censorship_tests f
JOIN dims_country d ON f.country_id = d.country_id
JOIN dims_event_type e ON f.event_type_id = e.event_type_id
JOIN dims_periods pr ON f.period_id = pr.period_id;
```

### fact.conflict_events

```sql
SELECT f.event_id,
       d.country_name,
       e.event_type,
       pr.period,
       f.event_count,
       f.fatalities
FROM fact_conflict_events f
JOIN dims_country d ON f.country_id = d.country_id
JOIN dims_event_type e ON f.event_type_id = e.event_type_id
JOIN dims_periods pr ON f.period_id = pr.period_id;
```
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

### civil_liberties_mart Aggregation
```sql
SELECT 
    d.country_name,
    pr.period,
    pr.half_year_label,
    COALESCE(SUM(tr.request_count), 0) AS takedown_requests,
    COALESCE(SUM(lp.request_count), 0) AS lumen_requests,
    COALESCE(COUNT(DISTINCT ct.measurement_id), 0) AS censorship_tests,
    COALESCE(SUM(ce.event_count), 0) AS conflict_events,
    COALESCE(SUM(ce.fatalities), 0) AS fatalities
FROM dims_country d
JOIN fact_takedown_requests tr ON d.country_id = tr.country_id
JOIN fact_lumen_platforms lp ON d.country_id = lp.country_id
JOIN fact_censorship_tests ct ON d.country_id = ct.country_id
JOIN fact_conflict_events ce ON d.country_id = ce.country_id
JOIN dims_periods pr ON tr.period_id = pr.period_id
GROUP BY d.country_name, pr.period, pr.half_year_label;
```
---


## 6. Reporting Layer
Analytical views simplify storytelling:
- **Top Platforms by Requests** → ranks platforms per country/period
- **Conflict vs Takedowns** → compares conflict events/fatalities with takedown requests
- **Censorship vs Requests** → compares OONI anomalies with takedown requests
- **Narrative Summary** → generates examiner‑friendly text blocks

view.top_platforms_requests
sql/md
SELECT 
    country,
    period,
    platform_name,
    SUM(request_count) AS total_requests
FROM fact_takedown_requests f
JOIN dims_country d ON f.country_id = d.country_id
JOIN dims_platform p ON f.platform_id = p.platform_id
JOIN dims_periods pr ON f.period_id = pr.period_id
GROUP BY country, period, platform_name
ORDER BY total_requests DESC;
Purpose: Ranks platforms by takedown requests per country/period.

Examiner use: Identify which platforms are most targeted.

view.conflict_vs_takedowns
sql/md
SELECT 
    country,
    period,
    conflict_events,
    fatalities,
    COALESCE(takedown_requests, 0) AS takedown_requests,
    COALESCE(lumen_requests, 0) AS lumen_requests,
    (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) AS total_requests,
    CASE 
        WHEN (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) > 0
        THEN ROUND(conflict_events::FLOAT / (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)), 2)
        ELSE NULL
    END AS conflict_to_request_ratio
FROM civil_liberties_mart;
Purpose: Compares conflict intensity with takedown activity.

Examiner use: Spot correlations between violence and censorship.

view.censorship_vs_requests
sql/md
SELECT 
    country,
    period,
    censorship_tests,
    COALESCE(takedown_requests, 0) AS takedown_requests,
    COALESCE(lumen_requests, 0) AS lumen_requests,
    (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) AS total_requests,
    CASE 
        WHEN (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)) > 0
        THEN ROUND(censorship_tests::FLOAT / (COALESCE(takedown_requests, 0) + COALESCE(lumen_requests, 0)), 2)
        ELSE NULL
    END AS censorship_to_request_ratio
FROM civil_liberties_mart;
Purpose: Compares OONI censorship anomalies with takedown requests.

### view.narrative_summary
```sql
SELECT 
    country,
    period,
    CONCAT(
        'In ', country, ' during ', period, ': ',
        'There were ', conflict_events, ' conflict events with ',
        fatalities, ' fatalities. ',
        'OONI recorded ', censorship_tests, ' censorship tests. ',
        'Google reported ', takedown_requests, ' requests, ',
        'Lumen recorded ', lumen_requests, '. ',
        'Overall, this period reflects ',
        CASE 
            WHEN conflict_events > 50 OR censorship_tests > 100 THEN 'heightened civil liberties pressures.'
            WHEN (takedown_requests + lumen_requests) > 50 THEN 'significant takedown activity.'
            ELSE 'moderate activity across all signals.'
        END
    ) AS summary_text
FROM civil_liberties_mart;
```
---
7. Quality Checks
Not Null Checks
```sql
SELECT *
FROM fact_takedown_requests
WHERE country_id IS NULL
   OR platform_id IS NULL
   OR reason_id IS NULL;
```
Non‑Negative Checks
```sql
SELECT *
FROM fact_conflict_events
WHERE fatalities < 0
   OR event_count < 0;
```
Unique Key Checks
```sql
SELECT lumen_id, COUNT(*)
FROM fact_lumen_platforms
GROUP BY lumen_id
HAVING COUNT(*) > 1;
```
Valid Period Range

```sql
SELECT *
FROM dims_periods
WHERE period < '2023-06'
   OR period > '2025-06';
```
## 8. Visual References

For a complete visual overview of the pipeline, including:

Entity Relationship Diagram (ERD) → showing facts, dims, marts, and joins

Dataset Lineage Diagram → showing ingestion → staging → facts → mart → reporting flow

📖 Please see [erd-lineage.md](./docs/data-modelling.md)

