/* @bruin
tags:
  - marts_bq
name: marts.fact_platform_blocking_summary
type: bq.sql
connection: bigquery-default
description: Monthly blocking summary by platform.
owner: civil-liberties-pipeline
depends:
  - marts.fact_censorship_measurements
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  test_name AS platform,
  test_category,
  year,
  month,
  FORMAT('%04d-%02d', year, month) AS year_month,
  COUNT(*) AS total_measurements,
  COUNTIF(is_blocked) AS blocked_count,
  COUNTIF(is_confirmed_block) AS confirmed_blocked_count,
  COUNTIF(NOT is_blocked) AS ok_count,
  SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS blocking_rate,
  SAFE_DIVIDE(COUNTIF(is_confirmed_block), COUNT(*)) AS confirmed_blocking_rate,
  COUNT(DISTINCT tested_url_or_app) AS distinct_targets_tested,
  COUNT(DISTINCT IF(is_blocked, tested_url_or_app, NULL)) AS distinct_targets_blocked
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_measurements`
GROUP BY test_name, test_category, year, month
ORDER BY year, month, blocking_rate DESC;
