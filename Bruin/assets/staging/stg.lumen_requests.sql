/* @bruin
tags:
  - staging_bq
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
        LOWER(country) AS country,
        sender,
        recipient,
        SAFE_CAST(date_submitted AS INT64) AS date_submitted,
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
    WHERE LOWER(country) IN ('kenya', 'ke')
),

normalized AS (
    SELECT
        *,
        -- deterministic: nanoseconds → micros
        TIMESTAMP_MICROS(DIV(date_submitted, 1000)) AS submitted_ts
    FROM base
    WHERE date_submitted IS NOT NULL
),

final AS (
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
    FROM normalized
)

SELECT * FROM final;
