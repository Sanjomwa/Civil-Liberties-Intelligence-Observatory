/* @bruin
name: dim_test_categories
type: bq.sql
connection: bigquery-default
description: |
  OONI test categories with higher-level grouping for censorship analysis.
  Drives the category filter on the Streamlit censorship dashboard.
owner: civil-liberties-pipeline

depends:
  - stg.ooni

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
    test_category,

    -- Broader group for dashboard top-level filtering
    CASE
        WHEN test_category = 'Website/DNS Blocking'     THEN 'Infrastructure Blocking'
        WHEN test_category = 'Messaging App Blocking'   THEN 'Communication Suppression'
        WHEN test_category = 'Circumvention Tool Blocking' THEN 'Anti-Circumvention'
        ELSE 'Other'
    END                                                 AS category_group,

    -- Civil liberties impact severity (for colour coding in dashboards)
    CASE
        WHEN test_category = 'Circumvention Tool Blocking' THEN 1
        WHEN test_category = 'Messaging App Blocking'      THEN 2
        WHEN test_category = 'Website/DNS Blocking'        THEN 3
        ELSE 4
    END                                                 AS severity_rank

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
WHERE probe_cc = 'KE'
  AND test_category IS NOT NULL
ORDER BY severity_rank
