/* @bruin
name: dim_test_categories
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: OONI test categories for censorship analysis
owner: civil-liberties-pipeline

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
    END AS category_group
FROM {{ ref('stg.ooni') }}
WHERE country = 'KE';
