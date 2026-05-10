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
        TIMESTAMP(date_submitted) AS date_submitted,
        reason,
        request_count,
        item_count,
        TIMESTAMP(extracted_at) AS extracted_at

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.lumen_requests`

    WHERE LOWER(country) IN ('ke','kenya')
      AND date_submitted IS NOT NULL
),

normalized AS (

    SELECT
        *,

        DATE(date_submitted) AS measurement_date,

        EXTRACT(YEAR FROM date_submitted) AS year,

        EXTRACT(MONTH FROM date_submitted) AS month,

        FORMAT_DATE('%Y-%m', DATE(date_submitted)) AS year_month,

        CASE
            WHEN EXTRACT(MONTH FROM date_submitted) <= 6
                THEN DATE(EXTRACT(YEAR FROM date_submitted),6,1)
            ELSE DATE(EXTRACT(YEAR FROM date_submitted),12,1)
        END AS period_date

    FROM base
),

final AS (

    SELECT
        request_id,
        country,
        sender,
        recipient,
        date_submitted,

        FORMAT_DATE('%Y-%m', period_date) AS period,

        CASE
            WHEN EXTRACT(MONTH FROM period_date)=6
                THEN CONCAT('Jan-Jun ',CAST(year AS STRING))
            ELSE CONCAT('Jul-Dec ',CAST(year AS STRING))
        END AS half_year_label,

        reason,
        request_count,
        item_count,
        extracted_at,

        measurement_date,
        year,
        month,
        year_month

    FROM normalized
)

SELECT *
FROM final