/* @bruin
tags:
  - reporting_bq
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default
description: |
  Final observatory mart powering all Streamlit dashboards.
  Built from cross-source censorship spine (OONI + ACLED + platform + takedowns).
  One row per censorship event timeline record enriched with full dimensional context.

owner: civil-liberties-pipeline

depends:
  - marts.fact_cross_source_censorship_events
  - marts.fact_platform_blocking_summary
  - marts.fact_takedown_requests
  - marts.fact_takedown_trends
  - marts.dim_dates
  - marts.dim_regions
  - marts.dim_platforms
  - marts.dim_reasons
  - marts.dim_asn
  - marts.dim_blocking_signals
  - marts.dim_censorship_confidence

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH

/* ─────────────────────────────────────────────
   TAKEDOWN DAILY AGGREGATION
──────────────────────────────────────────── */
daily_takedowns AS (
    SELECT
        measurement_date,

        COUNT(*) AS takedown_records,
        SUM(number_of_requests) AS total_takedown_requests,
        SUM(items_requested_removal) AS total_items_targeted,

        COUNT(DISTINCT source) AS takedown_sources_active,
        COUNT(DISTINCT platform) AS platforms_targeted,

        STRING_AGG(DISTINCT reason, ', ' LIMIT 5) AS top_reasons

    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
    WHERE measurement_date IS NOT NULL
    GROUP BY measurement_date
),

/* ─────────────────────────────────────────────
   PLATFORM MONTHLY SUMMARY
──────────────────────────────────────────── */
monthly_platform AS (
    SELECT
        year,
        month,
        platform,
        blocking_rate,
        confirmed_blocking_rate,
        total_measurements,
        blocked_count
    FROM `encoded-joy-485413-k5.marts.fact_platform_blocking_summary`
),

/* ─────────────────────────────────────────────
   BASE SPINE (CORE OBSERVATORY TABLE)
──────────────────────────────────────────── */
base AS (
    SELECT
        f.event_id,
        f.measurement_date,
        f.year,
        f.month,

        f.asn,
        f.probe_asn,

        f.platform,
        f.test_category,

        f.blocking_signal_type,
        f.blocking_confidence,
        f.is_blocked,

        f.conflict_event_count,
        f.conflict_events_on_day,
        f.fatalities_on_day,
        f.protest_events_on_day,

        f.extracted_at

    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events` f
)

/* ─────────────────────────────────────────────
   FINAL MART
──────────────────────────────────────────── */
SELECT

    b.*,

    /* ── DIMENSIONS ───────────────────────── */
    d.day_name,
    d.month_name,
    d.year_month,
    d.half_year_label,
    d.is_weekend,

    r.region_name,

    a.asn_name,
    a.asn_country,
    a.asn_type,

    ps.platform_category,

    bs.signal_category,

    cc.confidence_level,

    /* ── TAKEDOWNS ───────────────────────── */
    t.takedown_records,
    t.total_takedown_requests,
    t.total_items_targeted,
    t.takedown_sources_active,
    t.top_reasons,

    /* ── PLATFORM BEHAVIOUR ──────────────── */
    mp.blocking_rate AS monthly_blocking_rate,
    mp.confirmed_blocking_rate AS monthly_confirmed_blocking_rate,

    /* ── CORE SCORE (LIGHTWEIGHT, NO OVERENGINEERING) ─ */
    CASE
        WHEN b.is_blocked THEN 0.6 ELSE 0.0
    END
    + CASE WHEN b.protest_events_on_day > 0 THEN 0.3 ELSE 0.0 END
    + LEAST(COALESCE(t.takedown_records, 0) * 0.02, 0.1)
    AS censorship_intensity_score,

    CASE
        WHEN b.is_blocked AND b.protest_events_on_day > 0 THEN 'High Suppression Window'
        WHEN b.is_blocked THEN 'Blocking Activity'
        WHEN b.protest_events_on_day > 0 THEN 'Political Unrest Window'
        ELSE 'Normal'
    END AS suppression_window_type

FROM base b

LEFT JOIN `encoded-joy-485413-k5.marts.dim_dates` d
    ON b.measurement_date = d.date_key

LEFT JOIN `encoded-joy-485413-k5.marts.dim_regions` r
    ON r.region_code = 'KE'

LEFT JOIN `encoded-joy-485413-k5.marts.dim_asn` a
    ON b.asn = a.asn

LEFT JOIN `encoded-joy-485413-k5.marts.dim_platforms` ps
    ON b.platform = ps.platform_name

LEFT JOIN `encoded-joy-485413-k5.marts.dim_blocking_signals` bs
    ON b.blocking_signal_type = bs.signal_type

LEFT JOIN `encoded-joy-485413-k5.marts.dim_censorship_confidence` cc
    ON b.blocking_confidence = cc.confidence_level

LEFT JOIN daily_takedowns t
    ON b.measurement_date = t.measurement_date

LEFT JOIN monthly_platform mp
    ON b.year = mp.year
   AND b.month = mp.month
   AND b.platform = mp.platform
;