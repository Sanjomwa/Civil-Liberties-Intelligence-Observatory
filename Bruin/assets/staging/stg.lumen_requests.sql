/* @bruin
tags:
  - stg_bq
  - dataset_lumen_requests
name: stg.lumen_requests
type: bq.sql
connection: bigquery-default
description: Cleaned Lumen takedown requests for Kenya (Jun 2023 - Jun 2025)
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
        CASE
            WHEN date_submitted BETWEEN 946684800 AND 4102444800
                THEN TIMESTAMP_SECONDS(date_submitted)
            WHEN date_submitted BETWEEN 946684800000 AND 4102444800000
                THEN TIMESTAMP_MILLIS(date_submitted)
            WHEN date_submitted BETWEEN 946684800000000 AND 4102444800000000
                THEN TIMESTAMP_MICROS(date_submitted)
            WHEN date_submitted BETWEEN 946684800000000000 AND 4102444800000000000
                THEN TIMESTAMP_MICROS(DIV(date_submitted, 1000))
            ELSE NULL
        END AS submitted_ts
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
    WHERE country = 'Kenya'
       OR country = 'KE'
),

raw AS (
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
        DATE(submitted_ts) AS measurement_date,
        EXTRACT(YEAR FROM submitted_ts) AS year
    FROM base
    WHERE submitted_ts IS NOT NULL
)

SELECT * FROM raw
