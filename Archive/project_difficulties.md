# Kenya Civil Liberties & Censorship Observatory

## Project Difficulties & Lessons Learned

**Project:** Multi-source data pipeline tracking internet censorship, political violence, and content takedowns in Kenya (Jun 2023 – Jun 2025)  
**Stack:** Bruin · Python 3.11 · Google Cloud Storage · BigQuery · DuckDB · Streamlit  
**Sources:** OONI · ACLED · Google Transparency Report · Lumen Database

---

## 1. OONI Data Modeling — Wrong Abstraction from the Start

### What happened

The original pipeline used a single generic `status IN ('anomaly', 'confirmed', 'failure')` flag across all OONI test types. This was logically incorrect because OONI measurements are fundamentally test-specific — a `telegram` measurement has explicit boolean blocking fields (`telegram_http_blocking`, `telegram_tcp_blocking`) while a `tor` measurement has numeric reachability counts (`or_port_accessible`) and a `psiphon` measurement only has a generic failure string.

The generic flag produced an incoherent mix of signals: a Tor handshake AUTH mismatch was treated identically to a confirmed WhatsApp endpoint block.

### What was required

A complete rewrite of `raw.ooni_conflict_measurements` following the [OONI Data Pipeline design](https://docs.ooni.org/data/pipeline-design/). Per-test blocking derivation logic was implemented for six test types:

| Test               | Blocking logic                                                            |
| ------------------ | ------------------------------------------------------------------------- |
| `telegram`         | `telegram_http_blocking OR telegram_tcp_blocking`                         |
| `whatsapp`         | `whatsapp_endpoints_blocked` (confirmed) or `dns_inconsistent` (probable) |
| `signal`           | `signal_backend_failure IS NOT NULL` — disruption only, never confirmed   |
| `tor`              | `or_port_accessible = 0` — circumvention disruption                       |
| `psiphon`          | `psiphon_failure IS NOT NULL` — disruption only                           |
| `web_connectivity` | Standard OONI `anomaly`/`confirmed` flags                                 |

### Lesson

OONI data is not uniform across test types. The pipeline design document must be read before modeling — not after the first broken run.

---

## 2. Timestamp Type Instability Across the Pipeline

### What happened

The Lumen synthetic dataset suffered from a cascading timestamp type problem that caused failures at every layer of the pipeline:

- The **raw asset** generated timestamps as `datetime64[ns, UTC]` (nanosecond precision)
- Parquet wrote these as 64-bit integers internally
- BigQuery's external table autodetect inferred the column as `INT64` instead of `TIMESTAMP`
- The **staging SQL** then tried to recover by doing `SAFE_CAST(date_submitted AS INT64)` followed by `TIMESTAMP_MICROS(DIV(..., 1000))` — a pointless and destructive round-trip that produced dates in the year 56000 (nanoseconds interpreted as microseconds)
- The **BQ external table** was created with `autodetect = True`, which is unreliable for timestamp columns

The BigQuery error `TIMESTAMP value is out of allowed range: from 0001-01-01 to 9999-12-31` came from this chain.

### What was required

Three coordinated fixes across three layers:

1. **Raw asset:** Explicit `datetime64[us, UTC]` dtype (microsecond, not nanosecond) with `assert` guards that fail at write time if the type is wrong
2. **Load asset:** `autodetect = False` with an explicit `bigquery.SchemaField` list declaring `TIMESTAMP` for both `date_submitted` and `extracted_at`
3. **Staging SQL:** Remove the `SAFE_CAST` round-trip entirely — read `date_submitted` directly as `TIMESTAMP`, derive `measurement_date` with `DATE(date_submitted)`

### Lesson

Never use `autodetect = True` for timestamp columns in BigQuery external tables. Always supply an explicit schema. And never cast a `TIMESTAMP` to `INT64` in SQL — if you need a date, use `DATE()`.

---

## 3. Bruin DAG Dependency Mismatches

### What happened

Bruin validates the full dependency graph at parse time — every string in a `depends:` block must exactly match a `name:` declared somewhere in the project. Several assets had broken references that caused all pipeline validation to fail:

| File                         | Broken reference                 | Correct name                                  |
| ---------------------------- | -------------------------------- | --------------------------------------------- |
| `fact_censorship_impact.sql` | `marts.fact_conflict_events`     | `fact_conflict_events`                        |
| `civil_liberties_mart.sql`   | `fact_censorship_impact`         | `marts.fact_censorship_impact`                |
| `civil_liberties_mart.sql`   | `fact_platform_blocking_summary` | `marts.fact_platform_blocking_summary`        |
| 4 load scripts               | `raw.acled_conflict_events` etc. | Removed — no managed raw assets for these     |
| 4 dim/fact files             | `stg.lumen_requests`             | Had to be created — file was missing entirely |

Additionally, older asset names (`int.ooni_measurements`, `marts.fact_ooni_censorship_signals`) persisted in `depends:` blocks after those assets were renamed, causing Bruin to report `Dependency does not exist` even though the replacement files existed.

### What was required

A systematic audit: extract all declared `name:` values, extract all `depends:` references, find the diff, fix each broken edge individually. The missing `stg.lumen_requests` file had to be created from scratch.

### Lesson

In Bruin, renaming an asset requires a global search-and-replace across all `depends:` blocks in the project. Deleting an asset without removing its references is equally breaking. A naming convention enforced from day one (e.g., always prefix with layer: `stg.`, `marts.`, `fact_`) prevents silent mismatches.

---

## 4. YAML Parse Errors Blocking Entire Pipeline

### What happened

A single malformed `@bruin` YAML header in `platform_censorship_mart.sql` caused every asset in the project to show as `Unknown Asset`. Bruin cannot load the pipeline at all if any asset file has invalid YAML — it does not skip the bad file and continue.

The specific failures were:

- **Unindented `description:` block:** The `description: |` block scalar requires all continuation lines to be indented by at least 2 spaces. Lines written flush-left caused `yaml: line 7: did not find expected alphabetic or numeric character`
- **Bullet characters in description:** `*` is a YAML alias marker. Using `* OONI blocking signals` inside a description block caused a parse error
- **Markdown code fences in SQL body:** Triple-backtick fences (` ``` `) were pasted into the SQL body from a markdown document. Bruin's SQL parser treated the first ` ``` ` as an unclosed BigQuery quoted identifier and threw `Expecting ) at line 23`

### What was required

Fix the YAML header indentation, replace `*` bullets with plain text, and strip all ` ``` ` fences from the SQL body.

### Lesson

The `@bruin` header is YAML, not freeform text. Every line of a `description: |` block must be indented. Never paste markdown-formatted content directly into SQL files. One broken file breaks the entire project.

---

## 5. Marts Reading from Wrong Layer

### What happened

Several mart SQL files were querying raw external tables (e.g., `ooni_measurements`, `acled_conflict_events`) instead of the staging tables (`stg_ooni`, `stg_acled_conflict_events`). This bypassed the entire staging layer — Kenya filters, date parsing, and derived columns like `test_category`, `measurement_date`, and `is_censorship_trigger_event` were all missing from mart outputs.

The result was that marts produced data with out-of-scope dates (rows from 2020, 2021, 2022 appearing in a Jun 2023–Jun 2025 project), null values in derived columns, and broken downstream joins because the join key `measurement_date` did not exist on the raw tables.

### What was required

All 13 mart files were updated to read from `stg_*` tables. The staging layer is where Kenya filtering and date normalization happen — marts must never skip it.

### Lesson

The layer boundary between external tables and staging is not cosmetic. External tables are schema-unstable (autodetected, unfiltered, unparsed). Staging tables are the contract. Marts must always read from staging.

---

## 6. Lumen Synthetic Data Out of Project Scope

### What happened

The original synthetic Lumen dataset was generated with:

```python
pd.to_datetime(np.random.randint(1600000000, 1760000000, n), unit="s", utc=True)
```

The epoch range `1600000000–1760000000` seconds corresponds to September 2020 – November 2025 — partially overlapping the project scope but not aligned to it. Combined with the timestamp type problem, the staging SQL was producing `measurement_date = 1970-01-01` for all rows (epoch zero from the INT64 round-trip), meaning zero Lumen rows ever joined to the OONI or ACLED spine in the reporting mart.

The reporting mart showed takedown counts of 0 for all dates while the underlying data existed in BigQuery.

### What was required

The raw asset was rewritten to generate dates strictly within `2023-06-01` to `2025-06-30` using a fixed `seed=42` for reproducibility. A date range assertion was added to fail fast if any generated row falls outside the project window.

### Lesson

Synthetic datasets need the same scope constraints as real data. A `seed` must be set for reproducibility. Date range assertions at the raw layer prevent silent join failures downstream.

---

## 7. Environment Isolation and Credential Management

### What happened

The pipeline runs in two phases: a dev phase (local DuckDB/parquet) and a staging/prod phase (BigQuery). Several issues arose from environment handling:

- Load scripts used only `BRUIN_ENVIRONMENT` to detect the environment, but Bruin sets different variables depending on how it is invoked (`BRUIN_ENV`, `BRUIN_ENVIRONMENT`, `BRUIN_PIPELINE_ENVIRONMENT`)
- Raw assets had no guard preventing them from running in staging/prod, meaning a `bruin run --environment staging` could accidentally trigger expensive raw ingest
- GCS object paths were not env-prefixed (`ooni/ooni_measurements.parquet` instead of `staging/ooni/ooni_measurements.parquet`), so staging and prod runs overwrote each other's data
- Application Default Credentials expired mid-session, causing Bruin to report all assets as `Unknown Asset` with EC2 IMDS warnings (the AWS SDK falling through to EC2 metadata as a credential source)

### What was required

A shared `_env.py` utility with a three-variable resolver, `require_dev()` and `require_cloud()` guards, and `gcs_object(env, domain, filename)` for env-prefixed paths. A `pyrightconfig.json` was added to resolve Pylance import errors for the shared module.

### Lesson

Environment isolation must be designed in from the start, not retrofitted. Credential expiry in cloud dev environments is routine — `gcloud auth application-default login` should be part of the session startup checklist.

---

## 8. `fact_cross_source_censorship_events` — Implicit TIMESTAMP Casting

### What happened

The cross-source spine mart joined OONI, ACLED, and Lumen on `measurement_date`. The Lumen CTE included:

```sql
DATE(TIMESTAMP_MICROS(CAST(date_submitted AS INT64))) AS measurement_date
```

This cast a `TIMESTAMP` column to `INT64` (producing nanoseconds since epoch — a 19-digit number), then passed that to `TIMESTAMP_MICROS()` which expects microseconds. The resulting timestamp was in the year 56000+, outside BigQuery's allowed range, producing:

```
TIMESTAMP value is out of allowed range: from 0001-01-01 00:00:00 to 9999-12-31 23:59:59
```

The fix was to remove the cast entirely and read `date_submitted` as a `TIMESTAMP` directly, deriving `measurement_date` with `DATE(date_submitted)`.

### Lesson

Never cast `TIMESTAMP → INT64` in BigQuery SQL. If a TIMESTAMP column exists, use `DATE()` or `EXTRACT()` to derive date parts. The `TIMESTAMP_MICROS(CAST(... AS INT64))` pattern is only valid when the source column is genuinely stored as epoch microseconds as an integer — not when BigQuery already resolved it as a `TIMESTAMP`.

---

## Summary

| #   | Problem                               | Root Cause                                           | Resolution                                       |
| --- | ------------------------------------- | ---------------------------------------------------- | ------------------------------------------------ |
| 1   | Wrong OONI blocking logic             | Generic flag applied across test-specific schema     | Per-test derivation per OONI design doc          |
| 2   | Timestamp instability                 | Nanosecond dtype + autodetect + SQL round-trip       | `datetime64[us,UTC]` + explicit BQ schema        |
| 3   | Broken DAG dependencies               | Asset renames not propagated, missing staging file   | Systematic audit + `stg.lumen_requests` created  |
| 4   | YAML parse errors blocking all assets | Unindented description, `*` bullets, markdown fences | Strict YAML formatting, no markdown in SQL files |
| 5   | Marts skipping staging layer          | SQL reading raw external tables directly             | All marts updated to read from `stg_*` tables    |
| 6   | Lumen data out of scope               | Synthetic epoch range misaligned                     | Scoped to `2023-06-01`–`2025-06-30`, seed=42     |
| 7   | Environment isolation gaps            | No env guards, shared GCS paths, expired ADC         | `_env.py` utility, env-prefixed GCS paths        |
| 8   | Cross-source TIMESTAMP out of range   | `TIMESTAMP → INT64` cast in SQL                      | Remove cast, use `DATE(date_submitted)` directly |
