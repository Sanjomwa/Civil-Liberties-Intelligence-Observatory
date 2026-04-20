/* @bruin
tags:
  - staging_bq
name: stg.lumen_requests
type: bq.sql
connection: bigquery-default
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
        date_submitted,           -- now a real TIMESTAMP (no more corruption)
        period,
        half_year_label,
        reason,
        request_count,
        item_count,
        extracted_at
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`
    WHERE LOWER(country) IN ('ke', 'kenya')
      AND date_submitted IS NOT NULL
),

final AS (
    SELECT
        *,
        DATE(date_submitted)                          AS measurement_date,
        EXTRACT(YEAR FROM date_submitted)             AS year,
        FORMAT_DATE('%Y-%m', DATE(date_submitted))    AS year_month
    FROM base
)

SELECT * FROM final;
