/* @bruin
tags:
  - marts_bq
name: reporting.platform_censorship_mart
type: bq.sql
connection: bigquery-default

description: |
  Platform-level censorship and blocking analytics combining:
  - OONI network interference signals (platform-inferred)
  - platform-normalized takedown request intelligence (Google + Lumen)

  Grain: platform × measurement_date

  Used for:
  - Platform Blocking dashboard
  - Content Removal dashboard
  - Cross-platform comparison analytics

depends:
  - marts.fact_network_blocking_daily
  - marts.fact_takedown_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH

-- =========================
-- OONI → PLATFORM INFERENCE
-- =========================
network AS (
  SELECT
    DATE(measurement_date) AS measurement_date,

    -- No real platform in OONI → keep as "network"
    'network' AS platform,

    SUM(ooni_tests) AS tests,
    SUM(blocked_tests) AS blocked,

    SAFE_DIVIDE(
      SUM(blocked_tests),
      NULLIF(SUM(ooni_tests), 0)
    ) AS block_rate

  FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
  GROUP BY 1,2
),

-- =========================
-- TAKEDOWN PLATFORM NORMALIZATION
-- =========================
takedowns AS (
  SELECT
    DATE(measurement_date) AS measurement_date,

    CASE
      WHEN LOWER(platform) LIKE '%facebook%' THEN 'facebook'
      WHEN LOWER(platform) LIKE '%whatsapp%' THEN 'whatsapp'
      WHEN LOWER(platform) LIKE '%twitter%'
        OR LOWER(platform) LIKE '%x%' THEN 'twitter'
      WHEN LOWER(platform) LIKE '%youtube%' THEN 'youtube'
      WHEN LOWER(platform) LIKE '%instagram%' THEN 'instagram'
      WHEN LOWER(platform) LIKE '%blogger%' THEN 'blogger'
      WHEN LOWER(platform) LIKE '%web%' THEN 'web_search'
      WHEN LOWER(platform) LIKE '%play%' THEN 'play_store'
      ELSE 'other'
    END AS platform,

    SUM(number_of_requests) AS takedown_requests,

    SUM(
      COALESCE(items_removed_legal, 0) +
      COALESCE(items_removed_policy, 0)
    ) AS items_removed

  FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
  GROUP BY 1,2
),

-- =========================
-- COMBINED PLATFORM SPINE
-- =========================
combined AS (
  SELECT
    COALESCE(n.measurement_date, t.measurement_date) AS measurement_date,
    COALESCE(n.platform, t.platform) AS platform,

    COALESCE(n.tests, 0) AS tests,
    COALESCE(n.blocked, 0) AS blocked,
    COALESCE(n.block_rate, 0) AS block_rate,

    COALESCE(t.takedown_requests, 0) AS takedown_requests,
    COALESCE(t.items_removed, 0) AS items_removed

  FROM network n
  FULL OUTER JOIN takedowns t
    ON n.measurement_date = t.measurement_date
   AND n.platform = t.platform
),

-- =========================
-- NORMALIZATION BASE
-- =========================
norm AS (
  SELECT
    *,
    MAX(takedown_requests) OVER () AS max_takedowns
  FROM combined
)

-- =========================
-- FINAL OUTPUT
-- =========================
SELECT

  measurement_date,
  platform,

  -- OONI METRICS
  tests,
  blocked,
  block_rate,

  -- TAKEDOWN METRICS
  takedown_requests,
  items_removed,

  -- FLAGS
  blocked > 0 AS has_blocking,
  takedown_requests > 0 AS has_takedown,

  -- NORMALIZED METRIC
  SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
    AS normalized_takedowns,

  -- FINAL SCORE
  (
    0.6 * IFNULL(block_rate, 0) +
    0.4 * SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
  ) AS platform_pressure_score

FROM norm;