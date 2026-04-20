/* @bruin
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH

-- =========================
-- OONI NETWORK BLOCKING
-- =========================
ooni AS (
  SELECT
    DATE(measurement_date) AS measurement_date,
    LOWER(country) AS country,

    SUM(ooni_tests) AS ooni_tests,
    SUM(blocked_tests) AS blocked_tests,

    SAFE_DIVIDE(SUM(blocked_tests), NULLIF(SUM(ooni_tests), 0)) AS block_rate,

    SUM(network_block_signals) AS network_block_signals

  FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
  GROUP BY 1,2
),

-- =========================
-- CONFLICT EVENTS
-- =========================
conflict AS (
  SELECT
    DATE(event_date) AS measurement_date,
    LOWER(country) AS country,

    SUM(event_count) AS conflict_events,
    SUM(fatalities) AS fatalities

  FROM `encoded-joy-485413-k5.marts.fact_conflict_events`
  GROUP BY 1,2
),

-- =========================
-- PRESSURE SIGNALS (FIXED)
-- =========================
pressure AS (
  SELECT
    DATE(measurement_date) AS measurement_date,
    LOWER(country) AS country,

    SUM(takedown_requests) AS takedown_requests,
    SUM(COALESCE(google_requests, 0)) AS google_requests

  FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
  GROUP BY 1,2
),

-- =========================
-- BASE SPINE JOIN
-- =========================
base AS (
  SELECT
    COALESCE(o.measurement_date, c.measurement_date, p.measurement_date) AS measurement_date,
    COALESCE(o.country, c.country, p.country) AS country,

    o.ooni_tests,
    o.blocked_tests,
    o.block_rate,
    o.network_block_signals,

    c.conflict_events,
    c.fatalities,

    p.takedown_requests,
    p.google_requests

  FROM ooni o
  FULL OUTER JOIN conflict c
    ON o.measurement_date = c.measurement_date
   AND o.country = c.country

  FULL OUTER JOIN pressure p
    ON COALESCE(o.measurement_date, c.measurement_date) = p.measurement_date
   AND COALESCE(o.country, c.country) = p.country
),

-- =========================
-- FEATURE ENGINEERING
-- =========================
features AS (
  SELECT
    *,

    COALESCE(blocked_tests, 0) > 0 AS has_blocking,
    COALESCE(conflict_events, 0) > 0 AS has_conflict,

    (
      COALESCE(blocked_tests, 0) > 0
      AND COALESCE(conflict_events, 0) > 0
    ) AS conflict_block_overlap,

    -- normalized pressure index (stable + bounded)
    (
      0.5 * SAFE_DIVIDE(COALESCE(blocked_tests, 0), NULLIF(ooni_tests, 0)) +
      0.3 * LEAST(COALESCE(conflict_events, 0) / 10.0, 1.0) +
      0.2 * LEAST(
        (COALESCE(takedown_requests, 0) + COALESCE(google_requests, 0)) / 100.0,
        1.0
      )
    ) AS civil_liberties_pressure_index

  FROM base
),

-- =========================
-- SUPPRESSION WINDOWS
-- =========================
windows AS (
  SELECT
    *,

    CASE
      WHEN conflict_events > 0 AND blocked_tests > 0
        THEN 'ACTIVE_SUPPRESSION'

      WHEN block_rate > 0.5
        THEN 'HIGH_NETWORK_BLOCKING'

      WHEN takedown_requests > 0 OR google_requests > 0
        THEN 'LEGAL_OR_PLATFORM_PRESSURE'

      ELSE 'BASELINE'
    END AS suppression_window

  FROM features
),

-- =========================
-- GEO DIMENSION
-- =========================
geo AS (
  SELECT
    LOWER(raw_country) AS country,
    country_name,
    iso2,

    CASE
      WHEN country_name = 'Kenya' THEN -1.286389
      WHEN country_name = 'DRC' THEN -4.0383
      ELSE NULL
    END AS latitude,

    CASE
      WHEN country_name = 'Kenya' THEN 36.817223
      WHEN country_name = 'DRC' THEN 21.7587
      ELSE NULL
    END AS longitude

  FROM `encoded-joy-485413-k5.marts.dim_country`
)

-- =========================
-- FINAL OUTPUT
-- =========================
SELECT
  w.measurement_date,
  g.country_name,
  g.iso2,
  g.latitude,
  g.longitude,

  COALESCE(w.ooni_tests, 0) AS ooni_tests,
  COALESCE(w.blocked_tests, 0) AS blocked_tests,
  w.block_rate,
  COALESCE(w.network_block_signals, 0) AS network_block_signals,

  COALESCE(w.conflict_events, 0) AS conflict_events,
  COALESCE(w.fatalities, 0) AS fatalities,

  COALESCE(w.takedown_requests, 0) AS takedown_requests,
  COALESCE(w.google_requests, 0) AS google_requests,

  w.has_blocking,
  w.has_conflict,
  w.conflict_block_overlap,

  w.civil_liberties_pressure_index,
  w.suppression_window

FROM windows w
LEFT JOIN geo g
ON w.country = g.country;