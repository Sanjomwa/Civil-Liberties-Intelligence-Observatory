name: reporting.platform_censorship_mart
type: sql
materialization: table

description: |
  Platform-level censorship and blocking analytics combining OONI network
  interference signals and takedown request intelligence.

depends:
  - marts.fact_network_blocking_daily
  - marts.fact_takedown_requests

query: |
  CREATE OR REPLACE TABLE reporting.platform_censorship_mart AS
  WITH

  network AS (
    SELECT
      DATE(measurement_date) AS measurement_date,
      'other' AS platform,
      SUM(ooni_tests) AS tests,
      SUM(blocked_tests) AS blocked,
      SAFE_DIVIDE(SUM(blocked_tests), SUM(ooni_tests)) AS block_rate
    FROM marts.fact_network_blocking_daily
    GROUP BY 1,2
  ),

  takedowns AS (
    SELECT
      DATE(measurement_date) AS measurement_date,
      LOWER(platform) AS platform,
      SUM(number_of_requests) AS takedown_requests,
      SUM(items_removed_legal + items_removed_policy) AS items_removed
    FROM marts.fact_takedown_requests
    GROUP BY 1,2
  ),

  combined AS (
    SELECT
      COALESCE(n.measurement_date, t.measurement_date) AS measurement_date,
      COALESCE(n.platform, t.platform) AS platform,
      n.tests,
      n.blocked,
      n.block_rate,
      t.takedown_requests,
      t.items_removed
    FROM network n
    FULL OUTER JOIN takedowns t
      ON n.measurement_date = t.measurement_date
     AND n.platform = t.platform
  ),

  norm AS (
    SELECT
      *,
      MAX(takedown_requests) OVER () AS max_takedowns
    FROM combined
  )

  SELECT
    measurement_date,
    platform,

    tests,
    blocked,
    block_rate,

    takedown_requests,
    items_removed,

    SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0)) AS normalized_takedowns,

    (
      0.6 * IFNULL(block_rate, 0) +
      0.4 * SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
    ) AS platform_pressure_score

  FROM norm;
