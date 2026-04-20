/* @bruin
tags:
  - stg_bq
  - dataset_lumen
name: stg.lumen_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Lumen takedown requests for Kenya (Jun 2023–Jun 2025)
owner: civil-liberties-pipeline
depends:
  - load.lumen_requests_to_gcs
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        request_id,
        LOWER(country)                          AS country,
        sender,
        recipient,
        date_submitted,                         -- already TIMESTAMP, read directly
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at,
        DATE(date_submitted)                    AS measurement_date,
        EXTRACT(YEAR FROM date_submitted)       AS year
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
    WHERE LOWER(country) IN ('kenya', 'ke')
      AND date_submitted >= TIMESTAMP '2023-06-01'
      AND date_submitted <  TIMESTAMP '2025-07-01'
)

SELECT * FROM base