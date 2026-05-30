/* @bruin
tags:
  - marts_bq

name: marts.fact_takedown_activity
type: bq.sql
connection: bigquery-default

depends:
  - int.google_pressure_periodized
  - stg.lumen_requests
  - int.lumen_pressure_daily

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH google AS (

    SELECT
        'google' AS source,
        'Web Search' AS platform,
        'Unknown' AS reason,

        measurement_date,

        google_requests AS number_of_requests,
        detailed_total AS item_count,
        google_pressure_score AS pressure_score

    FROM `{{ var.project_id }}.int.google_pressure_periodized`
),

lumen AS (

    SELECT
        'lumen' AS source,
        recipient AS platform,
        reason,

        measurement_date,

        request_count AS number_of_requests,
        item_count

    FROM `{{ var.project_id }}.stg.lumen_requests`
),

lumen_scored AS (

    SELECT
        l.source,
        l.platform,
        l.reason,
        l.measurement_date,
        l.number_of_requests,
        l.item_count,
        d.lumen_pressure_score AS pressure_score

    FROM lumen l
    LEFT JOIN
    `{{ var.project_id }}.int.lumen_pressure_daily` d
    USING (measurement_date)
)

SELECT * FROM google
UNION ALL
SELECT * FROM lumen_scored