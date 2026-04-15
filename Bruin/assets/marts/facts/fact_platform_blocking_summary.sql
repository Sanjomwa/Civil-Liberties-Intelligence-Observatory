/* @bruin
tags:
  - marts_bq
name: marts.fact_platform_blocking_summary
type: bq.sql
connection: bigquery-default
description: |
  Monthly blocking summary aggregated by platform and test category.
  Pre-aggregated to power Streamlit "Platform Blocking Trends" charts
  without scanning the full row-level fact each time.

  Now includes blocking_confidence breakdown so dashboards can distinguish
  confirmed vs probable vs disruption events per platform per month.

owner: civil-liberties-pipeline
depends:
  - marts.fact_censorship_measurements
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    test_name                                           AS platform,
    test_category,
    year,
    month,
    FORMAT('%04d-%02d', year, month)                    AS year_month,

    -- ── Volume ────────────────────────────────────────────────────────────
    COUNT(*)                                            AS total_measurements,
    COUNTIF(is_blocked)                                AS blocked_count,
    COUNTIF(is_confirmed_block)                        AS confirmed_blocked_count,
    COUNTIF(has_measurement_failure AND NOT is_blocked) AS disruption_only_count,
    COUNTIF(NOT is_blocked AND NOT has_measurement_failure) AS ok_count,

    -- ── Rates ─────────────────────────────────────────────────────────────
    SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*))          AS blocking_rate,
    SAFE_DIVIDE(COUNTIF(is_confirmed_block), COUNT(*))  AS confirmed_blocking_rate,
    SAFE_DIVIDE(
        COUNTIF(has_measurement_failure), COUNT(*)
    )                                                   AS failure_rate,

    -- ── Blocking confidence breakdown ─────────────────────────────────────
    COUNTIF(blocking_confidence = 'Confirmed')          AS confirmed_count,
    COUNTIF(blocking_confidence = 'Probable')           AS probable_count,
    COUNTIF(blocking_confidence = 'Disruption')         AS disruption_count,
    COUNTIF(blocking_confidence = 'OK')                 AS ok_confidence_count,

    -- ── Breadth ───────────────────────────────────────────────────────────
    COUNT(DISTINCT tested_url_or_app)                   AS distinct_targets_tested,
    COUNT(DISTINCT IF(is_blocked, tested_url_or_app, NULL)) AS distinct_targets_blocked,

    -- ── Top blocking signal for this platform/month ───────────────────────
    -- (most frequent non-null, non-'none' signal type)
    APPROX_TOP_COUNT(
        IF(blocking_signal_type != 'none', blocking_signal_type, NULL), 1
    )[SAFE_OFFSET(0)].value                             AS dominant_blocking_signal

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_measurements`
GROUP BY test_name, test_category, year, month
ORDER BY year, month, blocking_rate DESC
