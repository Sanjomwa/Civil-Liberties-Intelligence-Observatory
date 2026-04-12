/* @bruin
name: civil_liberties_mart
type: bq.sql
connection: bigquery-default
description: |
  Final reporting mart — single wide table that powers all Streamlit dashboards.
  Joins fact_censorship_impact (OONI × ACLED) with all dimensions and enriches
  with takedown request context aggregated to the same date grain.
  Grain: one row per OONI measurement enriched with full dimensional context.
  All dashboard queries hit this table — no further joins needed in Streamlit.
owner: civil-liberties-pipeline

depends:
  - fact_censorship_impact
  - fact_takedown_requests
  - fact_platform_blocking_summary
  - fact_takedown_trends
  - dim_dates
  - dim_regions
  - dim_platforms
  - dim_test_categories
  - dim_reasons
  - dim_event_types
  - dim_requestors

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH

-- ── Takedown activity aggregated to day level ─────────────────────────────
daily_takedowns AS (
    SELECT
        measurement_date,
        COUNT(*)                                    AS takedown_records,
        SUM(number_of_requests)                     AS total_takedown_requests,
        SUM(items_requested_removal)                AS total_items_targeted,
        COUNT(DISTINCT source)                      AS takedown_sources_active,
        COUNT(DISTINCT platform)                    AS platforms_targeted,
        STRING_AGG(DISTINCT reason_group, ', '
            ORDER BY reason_group LIMIT 5)          AS active_reason_groups
    FROM (
        SELECT
            measurement_date,
            source,
            platform,
            number_of_requests,
            items_requested_removal,
            CASE
                WHEN LOWER(reason) LIKE '%defamation%'
                  OR LOWER(reason) LIKE '%privacy%'       THEN 'Privacy & Reputation'
                WHEN LOWER(reason) LIKE '%copyright%'
                  OR LOWER(reason) LIKE '%trademark%'     THEN 'Intellectual Property'
                WHEN LOWER(reason) LIKE '%hate%'
                  OR LOWER(reason) LIKE '%violent%'
                  OR LOWER(reason) LIKE '%terror%'        THEN 'Harmful Content'
                WHEN LOWER(reason) LIKE '%national security%'
                  OR LOWER(reason) LIKE '%government%'    THEN 'Government / National Security'
                WHEN LOWER(reason) LIKE '%fraud%'
                  OR LOWER(reason) LIKE '%spam%'          THEN 'Fraud & Spam'
                ELSE 'Other'
            END AS reason_group
        FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_takedown_requests`
        WHERE measurement_date IS NOT NULL
    )
    GROUP BY measurement_date
),

-- ── Monthly blocking rate context (for trend arrows in dashboard) ─────────
monthly_blocking AS (
    SELECT
        year,
        month,
        test_name,
        blocking_rate,
        confirmed_blocking_rate,
        total_measurements,
        blocked_count,
        distinct_targets_blocked
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_platform_blocking_summary`
),

-- ── Core join: censorship impact × dates × regions × takedowns ───────────
mart_base AS (
    SELECT
        -- Measurement identity
        ci.measurement_id,
        ci.measurement_date,
        ci.year,
        ci.month,
        ci.test_name                                AS platform,
        ci.test_category,
        ci.censorship_status,
        ci.is_blocked,
        ci.is_confirmed_block,
        ci.tested_url_or_app,
        ci.asn,
        ci.probe_asn,
        ci.blocked_on_protest_day,
        ci.extracted_at,

        -- Conflict context (from fact_censorship_impact)
        ci.conflict_event_count,
        ci.total_events                             AS conflict_events_on_day,
        ci.total_fatalities                         AS fatalities_on_day,
        ci.trigger_event_count                      AS protest_events_on_day,
        ci.event_types_on_day,
        ci.counties_affected,
        ci.total_population_exposure,

        -- Date dimension
        dd.day_name,
        dd.month_name,
        dd.year_month,
        dd.half_year_label,
        dd.protest_season_flag,
        dd.political_context_flag,
        dd.is_weekend,
        dd.reporting_period_flag,

        -- Test category dimension
        dtc.category_group,
        dtc.severity_rank                           AS blocking_severity_rank,

        -- Platform dimension
        dp.platform_category,
        dp.source                                   AS platform_source,

        -- Daily takedown context
        td.takedown_records,
        td.total_takedown_requests,
        td.total_items_targeted,
        td.takedown_sources_active,
        td.platforms_targeted                       AS takedown_platforms_targeted,
        td.active_reason_groups,

        -- Monthly blocking rate (for context in single-row views)
        mb.blocking_rate                            AS monthly_platform_blocking_rate,
        mb.confirmed_blocking_rate                  AS monthly_confirmed_blocking_rate

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_impact` ci

    LEFT JOIN `encoded-joy-485413-k5.{{ var.bq_dataset }}.dim_dates` dd
        ON ci.measurement_date = dd.date_key

    LEFT JOIN `encoded-joy-485413-k5.{{ var.bq_dataset }}.dim_test_categories` dtc
        ON ci.test_category = dtc.test_category

    LEFT JOIN `encoded-joy-485413-k5.{{ var.bq_dataset }}.dim_platforms` dp
        ON ci.test_name = dp.platform_name
       AND dp.source = 'OONI'

    LEFT JOIN daily_takedowns td
        ON ci.measurement_date = td.measurement_date

    LEFT JOIN monthly_blocking mb
        ON ci.year      = mb.year
       AND ci.month     = mb.month
       AND ci.test_name = mb.test_name
)

SELECT
    *,

    -- ── Observatory headline metrics (pre-computed for dashboard KPI cards) ──

    -- Censorship intensity score: combines blocking + conflict + takedowns
    ROUND(
        (CASE WHEN is_blocked THEN 0.5 ELSE 0.0 END)
        + (CASE WHEN blocked_on_protest_day THEN 0.3 ELSE 0.0 END)
        + LEAST(COALESCE(protest_events_on_day, 0) * 0.05, 0.2),
    2)                                              AS censorship_intensity_score,

    -- Suppression window flag: blocks + protest same day + takedown activity
    CASE
        WHEN is_blocked
         AND COALESCE(protest_events_on_day, 0) > 0
         AND COALESCE(total_takedown_requests, 0) > 0 THEN 'Full Suppression Window'
        WHEN is_blocked
         AND COALESCE(protest_events_on_day, 0) > 0   THEN 'Blocking + Protest Day'
        WHEN is_blocked
         AND COALESCE(total_takedown_requests, 0) > 0 THEN 'Blocking + Removal Activity'
        WHEN is_blocked                               THEN 'Blocking Only'
        ELSE 'No Suppression Signal'
    END                                             AS suppression_window_type

FROM mart_base
ORDER BY measurement_date DESC, blocking_severity_rank ASC
