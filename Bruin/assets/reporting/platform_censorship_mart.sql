/* @bruin
name: reporting.platform_censorship_mart
type: bq.sql
connection: bigquery-default
description: |
  Platform-level censorship mart combining:
  - OONI network blocking (fact level)
  - Takedown pressure (Google + Lumen)

  Grain: measurement_date × platform
owner: civil-liberties-pipeline
materialization:
  type: table
  strategy: create+replace
@bruin */

-- =========================
-- 1. OONI (USE FACT LEVEL, NOT SIGNALS)
-- =========================
WITH ooni AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,

        CASE
            WHEN LOWER(asn) IS NULL THEN 'unknown'
            ELSE 'unknown'  -- platform not available at ASN level
        END AS platform,

        SUM(ooni_tests) AS tests,
        SUM(blocked_tests) AS blocked,
        SAFE_DIVIDE(SUM(blocked_tests), SUM(ooni_tests)) AS block_rate

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
    GROUP BY 1,2,3
),

-- =========================
-- 2. TAKEDOWN (CLEAN PLATFORM MAP)
-- =========================
takedowns AS (

    SELECT
        measurement_date,

        LOWER(COALESCE(platform, 'unknown')) AS platform,

        SUM(number_of_requests) AS takedown_requests,
        SUM(COALESCE(items_removed, 0)) AS items_removed

    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
    GROUP BY 1,2
),

-- =========================
-- 3. JOIN ON CLEAN GRAIN
-- =========================
base AS (

    SELECT
        COALESCE(o.measurement_date, t.measurement_date) AS measurement_date,
        COALESCE(o.platform, t.platform) AS platform,

        COALESCE(o.tests, 0) AS tests,
        COALESCE(o.blocked, 0) AS blocked,
        COALESCE(o.block_rate, 0) AS block_rate,

        COALESCE(t.takedown_requests, 0) AS takedown_requests,
        COALESCE(t.items_removed, 0) AS items_removed

    FROM ooni o
    FULL OUTER JOIN takedowns t
        USING (measurement_date, platform)
),

-- =========================
-- 4. FEATURES
-- =========================
features AS (

    SELECT
        *,

        blocked > 0 AS has_blocking,
        takedown_requests > 0 AS has_takedown,

        (
            0.6 * COALESCE(block_rate, 0)
          + 0.4 * LEAST(takedown_requests / 50.0, 1.0)
        ) AS platform_pressure_score

    FROM base
)

SELECT *
FROM features;
