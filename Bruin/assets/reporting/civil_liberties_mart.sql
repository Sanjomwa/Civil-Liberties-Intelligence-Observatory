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
  - marts.fact_ooni_censorship_signals
  - marts.fact_network_blocking_daily
  - marts.fact_conflict_events
  - marts.fact_country_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

CREATE OR REPLACE TABLE reporting.civil_liberties_mart AS

WITH

-- =========================
-- OONI (ASN + country grain)
-- =========================
ooni AS (
  SELECT
    DATE(start_time) AS measurement_date,
    LOWER(country) AS country,
    asn,

    COUNT(*) AS ooni_tests,
    SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END) AS blocked_tests,

    SAFE_DIVIDE(
      SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END),
      COUNT(*)
    ) AS block_rate,

    SUM(CASE WHEN blocking_signal_type IS NOT NULL THEN 1 ELSE 0 END)
      AS network_block_signals

  FROM marts.fact_ooni_censorship_signals
  GROUP BY 1,2,3
),

-- =========================
-- NETWORK BLOCKING DAILY
-- =========================
network AS (
  SELECT
    DATE(measurement_date) AS measurement_date,
    asn,

    SUM(ooni_tests) AS net_tests,
    SUM(blocked_tests) AS net_blocked,

    SAFE_DIVIDE(
      SUM(blocked_tests),
      NULLIF(SUM(ooni_tests), 0)
    ) AS net_block_rate

  FROM marts.fact_network_blocking_daily
  GROUP BY 1,2
),

-- =========================
-- ACLED CONFLICT EVENTS
-- =========================
conflict AS (
  SELECT
    DATE(event_date) AS measurement_date,
    LOWER(country) AS country,

    SUM(event_count) AS conflict_events,
    SUM(fatalities) AS fatalities

  FROM marts.fact_conflict_events
  GROUP BY 1,2
),

-- =========================
-- COUNTRY PRESSURE (GOOGLE + LUMEN)
-- =========================
country_pressure AS (
  SELECT
    DATE(measurement_date) AS measurement_date,
    LOWER(country) AS country,

    SUM(takedown_requests) AS takedown_requests,
    SUM(takedown_items) AS items_removed,
    SUM(google_requests) AS google_requests

  FROM marts.fact_country_pressure_daily
  GROUP BY 1,2
),

-- =========================
-- SPINE (OONI + NETWORK)
-- =========================
spine AS (
  SELECT
    o.measurement_date,
    o.country,
    o.asn,

    o.ooni_tests,
    o.blocked_tests,
    o.block_rate,
    o.network_block_signals,

    n.net_tests,
    n.net_blocked,
    n.net_block_rate

  FROM ooni o

  LEFT JOIN network n
    ON o.measurement_date = n.measurement_date
   AND o.asn = n.asn
),

-- =========================
-- ENRICHMENT LAYER
-- =========================
enriched AS (
  SELECT
    s.*,
    c.conflict_events,
    c.fatalities,
    cp.takedown_requests,
    cp.items_removed,
    cp.google_requests

  FROM spine s

  LEFT JOIN conflict c
    ON s.measurement_date = c.measurement_date
   AND s.country = c.country

  LEFT JOIN country_pressure cp
    ON s.measurement_date = cp.measurement_date
   AND s.country = cp.country
),

-- =========================
-- NORMALIZATION BASE
-- =========================
norm AS (
  SELECT
    *,
    MAX(conflict_events) OVER () AS max_conflict_events,
    MAX(takedown_requests) OVER () AS max_takedowns
  FROM enriched
)

-- =========================
-- FINAL OUTPUT
-- =========================
SELECT

  measurement_date,
  country,
  asn,

  -- OONI
  ooni_tests,
  blocked_tests,
  block_rate,
  network_block_signals,

  -- NETWORK
  net_tests,
  net_blocked,
  net_block_rate,

  -- ACLED
  conflict_events,
  fatalities,

  -- PRESSURE
  takedown_requests,
  items_removed,
  google_requests,

  -- FLAGS
  block_rate > 0 AS has_blocking,
  conflict_events > 0 AS has_conflict,
  (block_rate > 0 AND conflict_events > 0) AS conflict_block_overlap,

  -- NORMALIZED COMPONENTS
  SAFE_DIVIDE(conflict_events, NULLIF(max_conflict_events, 0))
    AS conflict_events_normalized,

  SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
    AS takedown_pressure_normalized,

  -- FINAL INDEX
  (
    0.5 * block_rate +
    0.3 * SAFE_DIVIDE(conflict_events, NULLIF(max_conflict_events, 0)) +
    0.2 * SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
  ) AS civil_liberties_pressure_index

FROM norm;
