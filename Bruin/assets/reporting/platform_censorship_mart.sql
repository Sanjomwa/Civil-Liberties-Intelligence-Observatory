/* @bruin
name: reporting.platform_censorship_mart
type: bq.sql
connection: bigquery-default
description: |
  Platform-level censorship mart combining OONI blocking signals
  normalized to platform, Google Transparency and Lumen takedowns.
  Grain: platform + measurement_date.
owner: civil-liberties-pipeline
tags:
  - reporting_bq
depends:
  - marts.fact_ooni_censorship_signals
  - marts.fact_takedown_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

-- =========================
-- 1. OONI PLATFORM NORMALIZATION
-- =========================
WITH ooni_base AS (
    SELECT
        measurement_date,
        CASE
            WHEN LOWER(input) LIKE '%facebook%'                         THEN 'facebook'
            WHEN LOWER(input) LIKE '%whatsapp%'                         THEN 'whatsapp'
            WHEN LOWER(input) LIKE '%twitter%'
              OR LOWER(input) LIKE '%x.com%'                            THEN 'twitter'
            WHEN LOWER(input) LIKE '%youtube%'                          THEN 'youtube'
            WHEN LOWER(input) LIKE '%telegram%'                         THEN 'telegram'
            WHEN LOWER(input) LIKE '%instagram%'                        THEN 'instagram'
            WHEN LOWER(input) LIKE '%tiktok%'                           THEN 'tiktok'
            ELSE 'other'
        END                                                             AS platform,
        is_blocked
    FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
    WHERE country = 'KE'
),

ooni_agg AS (
    SELECT
        measurement_date,
        platform,
        COUNT(*)                                                        AS tests,
        COUNTIF(is_blocked)                                             AS blocked,
        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*))                      AS block_rate
    FROM ooni_base
    GROUP BY 1, 2
),

-- =========================
-- 2. TAKEDOWN NORMALIZATION
-- =========================
takedown_base AS (
    SELECT
        measurement_date,
        CASE
            WHEN LOWER(platform) LIKE '%facebook%'                      THEN 'facebook'
            WHEN LOWER(platform) LIKE '%whatsapp%'                      THEN 'whatsapp'
            WHEN LOWER(platform) LIKE '%twitter%'
              OR LOWER(platform) LIKE '%x%'                             THEN 'twitter'
            WHEN LOWER(platform) LIKE '%youtube%'                       THEN 'youtube'
            WHEN LOWER(platform) LIKE '%instagram%'                     THEN 'instagram'
            WHEN LOWER(platform) LIKE '%blogger%'                       THEN 'blogger'
            WHEN LOWER(platform) LIKE '%web search%'                    THEN 'web_search'
            WHEN LOWER(platform) LIKE '%play%'                          THEN 'play_store'
            ELSE 'other'
        END                                                             AS platform,
        number_of_requests,
        COALESCE(item_count, items_requested_removal, 1)                AS items_removed
    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
),

takedown_agg AS (
    SELECT
        measurement_date,
        platform,
        SUM(number_of_requests)                                         AS takedown_requests,
        SUM(items_removed)                                              AS items_removed
    FROM takedown_base
    GROUP BY 1, 2
),

-- =========================
-- 3. JOIN
-- =========================
base AS (
    SELECT
        COALESCE(o.measurement_date, t.measurement_date)               AS measurement_date,
        COALESCE(o.platform, t.platform)                               AS platform,
        COALESCE(o.tests, 0)                                           AS tests,
        COALESCE(o.blocked, 0)                                         AS blocked,
        COALESCE(o.block_rate, 0)                                      AS block_rate,
        COALESCE(t.takedown_requests, 0)                               AS takedown_requests,
        COALESCE(t.items_removed, 0)                                   AS items_removed
    FROM ooni_agg o
    FULL OUTER JOIN takedown_agg t
        USING (measurement_date, platform)
),

-- =========================
-- 4. FEATURES
-- =========================
features AS (
    SELECT
        *,
        blocked > 0                                                     AS has_blocking,
        takedown_requests > 0                                           AS has_takedown,
        (
            0.6 * COALESCE(block_rate, 0)
          + 0.4 * LEAST(takedown_requests / 50.0, 1.0)
        )                                                               AS platform_pressure_score
    FROM base
)

SELECT *
FROM features