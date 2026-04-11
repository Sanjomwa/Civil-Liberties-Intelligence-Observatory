/* @bruin
name: stg.google_transparency_detailed
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned Google Transparency detailed removal requests
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - load.google_transparency_detailed_to_gcs
@bruin */

WITH raw AS (
    SELECT
        period_ending,
        country_region,
        cldr_territory_code,
        product,
        reason,
        total,
        extracted_at,
        -- Derived fields
        PARSE_DATE('%Y-%m-%d', period_ending) AS period_date,
        EXTRACT(YEAR FROM PARSE_DATE('%Y-%m-%d', period_ending)) AS year
    FROM {{ ref('load.google_transparency_detailed_to_gcs') }}
)

SELECT * FROM raw;