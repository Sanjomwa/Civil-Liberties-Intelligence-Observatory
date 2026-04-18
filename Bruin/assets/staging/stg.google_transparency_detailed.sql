/* @bruin
tags:
  - staging_bq
  - dataset_google_transparency_detailed
name: stg.google_transparency_detailed
type: bq.sql
connection: bigquery-default
description: Cleaned Google Transparency detailed removal requests for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.google_transparency_detailed_to_gcs

materialization:
  type: table
  strategy: create+replace
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
        PARSE_DATE('%Y-%m-%d', period_ending)                    AS period_date,
        EXTRACT(YEAR FROM PARSE_DATE('%Y-%m-%d', period_ending)) AS year
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.google_transparency_detailed`
    WHERE cldr_territory_code = 'KE'
)

SELECT * FROM raw
