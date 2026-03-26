
This document explains how our data flows from **raw sources → staging → marts → reporting**.

---

## 🏗️ **1. Ingestion Layer**
We ingested or generated **four datasets**, each chosen for its relevance to civil liberties and censorship analysis:

### 🔹 **Google Transparency Reports**
- **Source**: Google’s public transparency portal  
- **Why**: Official counts of government takedown requests by product/platform  
- **Rationale**: Provides baseline for platform‑level censorship activity  
- **Files**:  
  - `raw.google_transparency_requests.py` → ingests country-level request counts  
  - `raw.google_transparency_detailed.py` → ingests detailed platform-level request counts  
- **Keys**: `country`, `platform`, `reason`, `period`  
- **Quality checks**: `not_null` on country, product, reason; `non_negative` on request counts  

### 🔹 **Lumen Database**
- **Source**: Mock dataset generated locally  
- **Why**: Complements Google data with broader legal requests  
- **Rationale**: Needed to demonstrate harmonization of multiple request sources  
- **Keys**: `recipient`, `reason`, `request_id`, `period`  
- **Quality checks**: `unique` on request_id; `not_null` on recipient and reason  

### 🔹 **OONI (Open Observatory of Network Interference)**
- **Source**: OONI Probe measurements (Kenya, June 2023–June 2025)  
- **Why**: Captures censorship anomalies at the network level  
- **Rationale**: Provides ground‑truth evidence of censorship beyond formal requests  
- **File**: `raw.ooni_conflict_measurements.py`  
- **Keys**: `measurement_id`, `country`, `test_name`, `period`  
- **Quality checks**: `not_null` on test_name and country; `unique` on measurement_id  

### 🔹 **ACLED (Armed Conflict Location & Event Data)**
- **Source**: ACLED aggregated conflict events dataset  
- **Why**: Provides context on political violence and fatalities  
- **Rationale**: Enables correlation between conflict intensity and censorship activity  
- **File**: `raw.acled_conflict_events`  
- **Keys**: `week`, `country`, `region`, `event_type`, `id`  
- **Quality checks**: `non_negative` on fatalities/events; surrogate key added for uniqueness  

---

## 🧹 **2. Staging Layer**
The staging layer is like a *laundry room* — we clean and prepare the data before analysis.

### 🔹 **Google Transparency Staging**
- **File**: `stg_google_transparency.sql`  
- **Purpose**: Harmonizes the two ingest files  
- **Transformations**:  
  - Normalizes country names and product labels  
  - Aligns request counts into a unified schema  
  - Adds `half_year_label` for temporal analysis  

### 🔹 **Lumen Staging**
- **File**: `stg_lumen.sql`  
- **Purpose**: Cleans mock Lumen data  
- **Transformations**:  
  - Deduplicates request IDs  
  - Normalizes recipient and reason fields  
  - Aligns with Google schema for union  

### 🔹 **OONI Staging**
- **File**: `stg_ooni.sql`  
- **Purpose**: Cleans OONI measurements  
- **Transformations**:  
  - Extracts `period` from `start_time`  
  - Normalizes test names  
  - Filters to June 2023–June 2025  

### 🔹 **ACLED Staging**
- **File**: `stg_acled.sql`  
- **Purpose**: Cleans ACLED aggregated conflict events  
- **Transformations**:  
  - Parses `week` strings into proper DATE  
  - Uppercases region and country  
  - Casts events/fatalities to integers  
  - Adds surrogate key for uniqueness  
  - Retains centroid lat/long for spatial analysis  

---

## 📊 **3. Civil Liberties Mart**
This is our **main analytical layer**. It combines all sources into a single schema for reporting.

### 🗂️ **Dimensions (Dims)**
- **`dim_country`** → unified country codes/names  
- **`dim_platform`** → platforms (Google, YouTube, etc.)  
- **`dim_event_type`** → conflict event categories (protests, battles, etc.)  
- **`dim_test_type`** → OONI test categories (web connectivity, DNS anomalies)  

### 📈 **Facts**
- **`fact_takedown_requests`** → harmonized from Google + Lumen staging  
- **`fact_network_anomalies`** → from OONI staging  
- **`fact_conflict_events`** → from ACLED staging  

### 📝 **Reporting View: `civil_liberties_mart`**
This is the **union‑ready view** examiners and dashboards use. It joins dims + facts into one table:

| country | period | platform | reason | takedown_requests | censorship_tests | conflict_events | fatalities |
|---------|--------|----------|--------|------------------|-----------------|----------------|------------|

- **Keys**: `country`, `period`  
- **Purpose**: Enables dashboards to compare Kenya vs Global across censorship, conflict, and fatalities  
- **Quality checks**: Surrogate keys, non‑negative counts, consistent period alignment  

---

## 📈 **4. Reporting Layer**
This is where dashboards and charts live:

- **Kenya Focus** → Profile, Platform Analysis, Reasons, Conflict vs Censorship, Fatalities, Heatmap  
- **Global Comparison** → Leaders & Losers, Global Heatmap, Kenya vs Global Overview  
- **Civil Liberties Mart** → feeds all dashboards with harmonized facts and dims  

---

## 📝 **5. Summary**
- **Ingestion** → raw data from Google, Lumen, OONI, ACLED  
- **Staging** → cleaned, standardized schemas  
- **Mart** → dims + facts combined into `civil_liberties_mart`  
- **Reporting** → dashboards for Kenya and global comparison  

---

 
