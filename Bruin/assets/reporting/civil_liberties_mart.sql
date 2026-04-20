/* @bruin
tags:
  - marts_bq
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default

description: |
  Country × ASN civil liberties analytical spine combining:
  - OONI censorship + network blocking
  - ACLED conflict intensity
  - Google + Lumen takedown pressure

  Used as the primary reporting layer for Streamlit dashboards:
  Timeline, Suppression Windows, Finance Bill Crisis, and Map views.

depends:
          * marts.fact_network_blocking_daily
          * marts.fact_conflict_events
          * marts.fact_country_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH

-- =========================
-- OONI (COUNTRY LEVEL ONLY)
-- =========================
ooni AS (
SELECT
DATE(measurement_date) AS measurement_date,
LOWER(country) AS country,

```
SUM(ooni_tests) AS ooni_tests,
SUM(blocked_tests) AS blocked_tests,

SAFE_DIVIDE(
  SUM(blocked_tests),
  NULLIF(SUM(ooni_tests), 0)
) AS block_rate,

SUM(network_block_signals) AS network_block_signals
```

FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
GROUP BY 1,2
),

-- =========================
-- ACLED (COUNTRY LEVEL)
-- =========================
conflict AS (
SELECT
DATE(event_date) AS measurement_date,
LOWER(country) AS country,

```
SUM(event_count) AS conflict_events,
SUM(fatalities) AS fatalities
```

FROM `encoded-joy-485413-k5.marts.fact_conflict_events`
GROUP BY 1,2
),

-- =========================
-- COUNTRY PRESSURE (GOOGLE + LUMEN)
-- =========================
pressure AS (
SELECT
DATE(measurement_date) AS measurement_date,
LOWER(country) AS country,

```
SUM(takedown_requests) AS takedown_requests,
SUM(takedown_items) AS items_removed,
SUM(google_requests) AS google_requests
```

FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
GROUP BY 1,2
),

-- =========================
-- BASE SPINE (COUNTRY × DATE)
-- =========================
base AS (
SELECT
COALESCE(o.measurement_date, c.measurement_date, p.measurement_date) AS measurement_date,
COALESCE(o.country, c.country, p.country) AS country,

```
-- OONI
COALESCE(o.ooni_tests, 0) AS ooni_tests,
COALESCE(o.blocked_tests, 0) AS blocked_tests,
COALESCE(o.block_rate, 0) AS block_rate,
COALESCE(o.network_block_signals, 0) AS network_block_signals,

-- ACLED
COALESCE(c.conflict_events, 0) AS conflict_events,
COALESCE(c.fatalities, 0) AS fatalities,

-- PRESSURE
COALESCE(p.takedown_requests, 0) AS takedown_requests,
COALESCE(p.items_removed, 0) AS items_removed,
COALESCE(p.google_requests, 0) AS google_requests
```

FROM ooni o
FULL OUTER JOIN conflict c
ON o.measurement_date = c.measurement_date
AND o.country = c.country

FULL OUTER JOIN pressure p
ON COALESCE(o.measurement_date, c.measurement_date) = p.measurement_date
AND COALESCE(o.country, c.country) = p.country
),

-- =========================
-- FEATURES
-- =========================
features AS (
SELECT
*,

```
blocked_tests > 0 AS has_blocking,
conflict_events > 0 AS has_conflict,

(blocked_tests > 0 AND conflict_events > 0)
  AS conflict_block_overlap,

(
  0.5 * SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests, 0)) +
  0.3 * LEAST(conflict_events / 10.0, 1.0) +
  0.2 * LEAST((takedown_requests + google_requests) / 100.0, 1.0)
) AS civil_liberties_pressure_index
```

FROM base
),

-- =========================
-- WINDOWS (EVENT SEGMENTS)
-- =========================
windows AS (
SELECT
*,

```
CASE
  WHEN measurement_date BETWEEN DATE '2024-06-15' AND DATE '2024-07-15'
    THEN 'FINANCE_BILL_CRISIS'

  WHEN conflict_events > 0 AND blocked_tests > 0
    THEN 'ACTIVE_SUPPRESSION'

  WHEN block_rate > 0.5
    THEN 'HIGH_NETWORK_BLOCKING'

  WHEN takedown_requests > 0 OR google_requests > 0
    THEN 'LEGAL_OR_PLATFORM_PRESSURE'

  ELSE 'BASELINE'
END AS suppression_window
```

FROM features
)

SELECT *
FROM windows;
