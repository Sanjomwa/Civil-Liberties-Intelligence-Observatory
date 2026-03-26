# Data Modelling Documentation

## 1. Ingestion Layer
We ingested or generated four datasets, each chosen for its relevance to civil liberties and censorship analysis:

### Google Transparency Reports
- **Source**: Google’s public transparency portal.
- **Why**: Official counts of government takedown requests by product/platform.
- **Rationale**: Provides baseline for platform‑level censorship activity.
- **Files**:
  - `raw.google_transparency_requests.py` → ingests country-level request counts.
  - `raw.google_transparency_detailed.py` → ingests detailed platform-level request counts.
- **Keys**: `country`, `platform`, `reason`, `period`.
- **Quality checks**: `not_null` on country, product, reason; `non_negative` on request counts.

### Lumen Database
- **Source**: Mock dataset generated locally (not API).
- **Why**: Complements Google data with broader legal requests across platforms.
- **Rationale**: Needed to demonstrate harmonization of multiple request sources.
- **Keys**: `recipient`, `reason`, `request_id`, `period`.
- **Quality checks**: `unique` on request_id; `not_null` on recipient and reason.

### OONI (Open Observatory of Network Interference)
- **Source**: OONI Probe measurements (Kenya, June 2023–June 2025).
- **Why**: Captures censorship anomalies at the network level.
- **Rationale**: Provides ground‑truth evidence of censorship beyond formal requests.
- **File**: `raw.ooni_conflict_measurements.py` → syncs JSONL.gz from OONI S3, filters by date, converts to Parquet.
- **Keys**: `measurement_id`, `country`, `test_name`, `period`.
- **Quality checks**: `not_null` on test_name and country; `unique` on measurement_id.

### ACLED (Armed Conflict Location & Event Data)
- **Source**: ACLED aggregated conflict events dataset.
- **Why**: Provides context on political violence and fatalities.
- **Rationale**: Enables correlation between conflict intensity and censorship activity.
- **File**: `raw.acled_conflict_events` → ingested aggregated weekly conflict data.
- **Keys**: `week`, `country`, `region`, `event_type`, `id`.
- **Quality checks**: `non_negative` on fatalities and events; surrogate key added for uniqueness.

---

## 2. Staging Layer
Each staging file:
- Cleans raw ingestion (trimming, uppercasing, deduplication).
- Aligns schema to shared keys (`country`, `period`, `half_year_label`).
- Prepares data for fact tables with minimal transformations.

### Google Transparency Staging
- **File**: `stg_google_transparency.sql`.
- **Purpose**: Harmonizes the two ingest files (`raw.google_transparecy_requests`, `raw.google_transparency_detailed`).
- **Transformations**:
  - Normalizes country names and product labels.
  - Aligns request counts into a unified schema.
  - Adds `half_year_label` for temporal analysis.
- **Relationship**: This staging file is the bridge between the two ingest files, ensuring they can be unioned into a single fact table.

### Lumen Staging
- **File**: `stg_lumen.sql`.
- **Purpose**: Cleans mock Lumen data.
- **Transformations**:
  - Deduplicates request IDs.
  - Normalizes recipient and reason fields.
  - Aligns with Google schema for union.

### OONI Staging
- **File**: `stg_ooni.sql` (to be finalized).
- **Purpose**: Cleans OONI measurements.
- **Transformations**:
  - Extracts `period` from `start_time`.
  - Normalizes test names.
  - Ensures measurement IDs are unique.
  - Filters to June 2023–June 2025.

### ACLED Staging
- **File**: `stg_acled.sql`.
- **Purpose**: Cleans ACLED aggregated conflict events.
- **Transformations**:
  - Parses `week` strings into proper DATE.
  - Uppercases region and country.
  - Casts events/fatalities to integers.
  - Adds surrogate key for uniqueness.
  - Retains centroid lat/long for spatial analysis.

---

## 3. Implications for Marts
- **Dims**:  
  - `dim_country` → unified country codes/names across Google, Lumen, OONI, ACLED.  
  - `dim_platform` → from Google Transparency.  
  - `dim_event_type` → from ACLED.  
  - `dim_test_type` → from OONI.  

- **Facts**:  
  - `fact_takedown_requests` → harmonized from Google + Lumen staging.  
  - `fact_network_anomalies` → from OONI staging.  
  - `fact_conflict_events` → from ACLED staging.  

- **Shared keys**: `country`, `period`, `half_year_label` will allow us to correlate censorship requests, network anomalies, and conflict intensity.

---

## 4. Summary
- Ingest layer brings in diverse sources (platform requests, legal requests, network anomalies, conflict events).  
- Staging layer standardizes schemas, fixes parsing issues, and ensures reproducibility.  
- This foundation ensures our marts (dims and facts) will be robust, examiner‑friendly, and analytically powerful.
