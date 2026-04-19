/*@bruin
tags:
  - staging_bq
  - dataset_lumen_requests
name: stg.lumen_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Lumen takedown requests (contract-aligned staging layer)
owner: civil-liberties-pipeline

depends:
  - load.lumen_requests_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin*/

WITH base AS (

    SELECT
        request_id,
        LOWER(country) AS country,
        sender,
        recipient,
        date_submitted,
        extracted_at,
        period,
        half_year_label,
        reason,
        request_count,
        item_count

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`

    WHERE date_submitted IS NOT NULL
)

SELECT
    *,
    DATE(date_submitted) AS measurement_date,
    EXTRACT(YEAR FROM date_submitted) AS year,
    FORMAT_DATE('%Y-%m', DATE(date_submitted)) AS year_month

FROM base;
