/* @bruin
name: stg.google_transparency_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Google Transparency removal requests for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.google_transparency_requests_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH raw AS (
    SELECT
        time_period,
        country,
        cldr_territory,
        requestor,
        product,
        reason,
        number_of_requests,
        items_requested_removal,
        items_removed_legal,
        items_removed_policy,
        extracted_at,
        PARSE_DATE('%Y-%m', time_period)                    AS period_date,
        EXTRACT(YEAR FROM PARSE_DATE('%Y-%m', time_period)) AS year
    FROM `encoded-joy-485413-k5.civil_liberties_staging.google_transparency_requests`
    WHERE country = 'Kenya'
       OR cldr_territory = 'KE'
)

SELECT * FROM raw
