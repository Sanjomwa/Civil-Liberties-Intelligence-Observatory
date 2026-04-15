/* @bruin
tags:
  - marts_bq
name: dim_test_categories
type: bq.sql
connection: bigquery-default
description: OONI test category dimension.
owner: civil-liberties-pipeline
depends:
  - stg.ooni
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
  test_category,
  CASE
    WHEN test_category = 'Website/DNS Blocking' THEN 'Infrastructure Blocking'
    WHEN test_category = 'Messaging App Blocking' THEN 'Communication Suppression'
    WHEN test_category = 'Circumvention Tool Blocking' THEN 'Anti-Circumvention'
    ELSE 'Other'
  END AS category_group,
  CASE
    WHEN test_category = 'Circumvention Tool Blocking' THEN 1
    WHEN test_category = 'Messaging App Blocking' THEN 2
    WHEN test_category = 'Website/DNS Blocking' THEN 3
    ELSE 4
  END AS severity_rank
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_ooni`
WHERE probe_cc = 'KE'
  AND test_category IS NOT NULL
ORDER BY severity_rank;
