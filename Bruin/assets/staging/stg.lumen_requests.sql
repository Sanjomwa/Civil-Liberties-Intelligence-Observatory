/* @bruin
tags:
  - stg_bq
  - dataset_lumen_requests
name: stg.lumen_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Lumen takedown requests for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.lumen_requests_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH raw AS (
    SELECT
        request_id,
        country,
        sender,
        recipient,
        date_submitted,
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at,
        DATE(date_submitted)                    AS measurement_date,
        EXTRACT(YEAR FROM date_submitted)       AS year
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
    WHERE country = 'Kenya'
       OR country = 'KE'
)

SELECT * FROM raw
