/* @bruin
tags:
  - marts_bq

name: marts.fact_country_pressure_daily
type: bq.sql
connection: bigquery-default

description: |
  Daily Kenya pressure observability fact.

  Blends:
  - ACLED political conflict intensity
  - Lumen legal takedown activity
  - Google transparency pressure

  Rebalanced so political stress dominates severity.

depends:
  - marts.dim_dates
  - stg.acled_conflict_events
  - stg.lumen_requests
  - int.google_pressure_periodized

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH dates AS (

    SELECT date_key AS measurement_date
    FROM `encoded-joy-485413-k5.marts.dim_dates`

),

acled AS (

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

    SELECT *
    FROM `encoded-joy-485413-k5.int.google_pressure_periodized`

),

joined AS (

    SELECT
        d.measurement_date,

        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,

        COALESCE(l.takedown_requests,0) AS takedown_requests,
        COALESCE(l.takedown_items,0) AS takedown_items,

        COALESCE(g.google_requests,0) AS google_requests,
        COALESCE(g.requested_items,0) AS requested_items,
        COALESCE(g.legal_removed,0) AS legal_removed,
        COALESCE(g.policy_removed,0) AS policy_removed,
        COALESCE(g.detailed_total,0) AS detailed_total

    FROM dates d
    LEFT JOIN acled a USING(measurement_date)
    LEFT JOIN lumen l USING(measurement_date)
    LEFT JOIN google g USING(measurement_date)

),

scored AS (

    SELECT
        *,

        ROUND(LOG(1 + conflict_events + (fatalities * 3)),4)
            AS conflict_pressure_score,

        ROUND(LOG(1 + takedown_requests + takedown_items),4)
            AS legal_pressure_score,

        ROUND(LOG(1 + google_requests + detailed_total),4)
            AS platform_pressure_score

    FROM joined

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
    requested_items,
    legal_removed,
    policy_removed,
    detailed_total,

    conflict_pressure_score,
    legal_pressure_score,
    platform_pressure_score,

    ROUND(
          (conflict_pressure_score * 0.60)
        + (legal_pressure_score * 0.25)
        + (platform_pressure_score * 0.15),
        4
    ) AS composite_pressure_score,

    CASE
        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 6.5
            THEN 'SEVERE'

        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 4.0
            THEN 'ELEVATED'

        WHEN (
              (conflict_pressure_score * 0.60)
            + (legal_pressure_score * 0.25)
            + (platform_pressure_score * 0.15)
        ) >= 2.0
            THEN 'MODERATE'

        ELSE 'LOW'
    END AS pressure_level,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM scored
ORDER BY measurement_date