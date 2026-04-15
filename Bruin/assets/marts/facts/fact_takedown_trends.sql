/* @bruin
tags:
  - marts_bq
name: marts.fact_takedown_trends
type: bq.sql
connection: bigquery-default
description: Monthly aggregated takedown trends.
owner: civil-liberties-pipeline
depends:
  - marts.fact_takedown_requests
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
  SELECT
    source,
    platform,
    reason,
    CASE
      WHEN LOWER(reason) LIKE '%defamation%' OR LOWER(reason) LIKE '%privacy%' THEN 'Privacy & Reputation'
      WHEN LOWER(reason) LIKE '%copyright%' OR LOWER(reason) LIKE '%trademark%' THEN 'Intellectual Property'
      WHEN LOWER(reason) LIKE '%hate%' OR LOWER(reason) LIKE '%violent%' OR LOWER(reason) LIKE '%terror%' THEN 'Harmful Content'
      WHEN LOWER(reason) LIKE '%national security%' OR LOWER(reason) LIKE '%government%' THEN 'Government / National Security'
      WHEN LOWER(reason) LIKE '%fraud%' OR LOWER(reason) LIKE '%spam%' THEN 'Fraud & Spam'
      ELSE 'Other'
    END AS reason_group,
    number_of_requests,
    items_requested_removal,
    measurement_date,
    EXTRACT(YEAR FROM measurement_date) AS year,
    EXTRACT(MONTH FROM measurement_date) AS month
  FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
  WHERE measurement_date IS NOT NULL
)
SELECT
  source,
  reason_group,
  year,
  month,
  FORMAT('%04d-%02d', year, month) AS year_month,
  COUNT(*) AS request_records,
  SUM(number_of_requests) AS total_requests,
  SUM(items_requested_removal) AS total_items_targeted,
  COUNT(DISTINCT platform) AS platforms_affected,
  SUM(SUM(number_of_requests)) OVER (
    PARTITION BY source, reason_group
    ORDER BY year, month
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS cumulative_requests
FROM base
GROUP BY source, reason_group, year, month
ORDER BY year, month, source, total_requests DESC;
