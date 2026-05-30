/* @bruin
tags:
  - intermediate
  - lumen_harmonized

name: int.lumen_pressure_daily
type: bq.sql
connection: bigquery-default

depends:
  - stg.lumen_requests

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH daily AS (

    SELECT
        measurement_date,

        COUNT(*) AS request_events,
        SUM(request_count) AS request_count,
        SUM(item_count) AS item_count,

        COUNT(DISTINCT recipient) AS platforms_targeted,
        COUNT(DISTINCT reason) AS legal_vectors

    FROM `{{ var.project_id }}.stg.lumen_requests`
    GROUP BY measurement_date
),

scored AS (

    SELECT
        *,

        SAFE_DIVIDE(item_count, NULLIF(request_count,0))
            AS items_per_request,

        LOG(
            1
            + request_count
            + item_count
        ) AS base_pressure

    FROM daily
)

SELECT
    measurement_date,

    request_events,
    request_count,
    item_count,
    platforms_targeted,
    legal_vectors,
    items_per_request,

    ROUND(
        base_pressure
        * (1 + (platforms_targeted * 0.08))
        * (1 + (legal_vectors * 0.06)),
        4
    ) AS lumen_pressure_score

FROM scored
ORDER BY measurement_date