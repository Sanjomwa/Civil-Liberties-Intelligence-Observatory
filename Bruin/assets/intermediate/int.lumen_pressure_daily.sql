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

    FROM `encoded-joy-485413-k5.stg.lumen_requests`
    GROUP BY measurement_date
)

SELECT
    measurement_date,

    request_events,
    request_count,
    item_count,
    platforms_targeted,
    legal_vectors,

    ROUND(
        LOG(
            1
            + request_count
            + item_count
            + (platforms_targeted * 5)
            + (legal_vectors * 8)
        ),
        4
    ) AS lumen_pressure_score

FROM daily
ORDER BY measurement_date