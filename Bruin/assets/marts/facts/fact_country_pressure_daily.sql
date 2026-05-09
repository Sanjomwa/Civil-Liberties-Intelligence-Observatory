/* @bruin
tags:
  - marts_bq

name: marts.fact_country_pressure_daily
type: bq.sql
connection: bigquery-default

description: |
  Daily country-level digital pressure observability fact for Kenya.
  Combines political conflict, legal takedown pressure, and platform removal activity.

depends:
  - stg.acled_conflict_events
  - stg.lumen_requests
  - stg.google_transparency_requests
  - stg.google_transparency_detailed

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH acled AS (

    SELECT
        event_date AS measurement_date,
        SUM(events) AS conflict_events,
        SUM(fatalities) AS fatalities
    FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
    WHERE country = 'Kenya'
    GROUP BY event_date
),

lumen AS (

    SELECT
        measurement_date,
        SUM(request_count) AS takedown_requests,
        SUM(item_count) AS takedown_items
    FROM `encoded-joy-485413-k5.stg.lumen_requests`
    GROUP BY measurement_date
),

google AS (

    SELECT
        period_date AS measurement_date,
        SUM(number_of_requests) AS google_requests
    FROM `encoded-joy-485413-k5.stg.google_transparency_requests`
    GROUP BY period_date
),

combined AS (

    SELECT
        COALESCE(a.measurement_date,l.measurement_date,g.measurement_date)
            AS measurement_date,

        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,
        COALESCE(l.takedown_requests,0) AS takedown_requests,
        COALESCE(l.takedown_items,0) AS takedown_items,
        COALESCE(g.google_requests,0) AS google_requests

    FROM acled a
    FULL OUTER JOIN lumen l USING (measurement_date)
    FULL OUTER JOIN google g USING (measurement_date)
)

SELECT
    measurement_date,
    'Kenya' AS country,
    'KE' AS iso2,

    conflict_events,
    fatalities,
    takedown_requests,
    takedown_items,
    google_requests,

    LOG(1 + conflict_events + fatalities) AS conflict_pressure_score,
    LOG(1 + takedown_requests + takedown_items) AS legal_pressure_score,
    LOG(1 + google_requests) AS platform_pressure_score,

    ROUND(
        LOG(1 + conflict_events + fatalities)
      + LOG(1 + takedown_requests + takedown_items)
      + LOG(1 + google_requests),
        4
    ) AS composite_pressure_score

FROM combined
ORDER BY measurement_date