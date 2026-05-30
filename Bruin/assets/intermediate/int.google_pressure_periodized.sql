/* @bruin
tags:
  - intermediate
  - google_harmonized

name: int.google_pressure_periodized
type: bq.sql
connection: bigquery-default

description: |
  Harmonizes Google semiannual transparency datasets
  onto shared half-year periods and expands to daily grain.

depends:
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH calendar_bounds AS (

    SELECT
        MIN(date_key) AS min_date,
        MAX(date_key) AS max_date
    FROM `{{ var.project_id }}.marts.dim_dates`
),

-- normalize request snapshots
requests AS (

    SELECT
        period_date AS period_start,

        SUM(number_of_requests) AS google_requests,
        SUM(items_requested_removal) AS requested_items,
        SUM(items_removed_legal) AS legal_removed,
        SUM(items_removed_policy) AS policy_removed

    FROM `{{ var.project_id }}.stg.google_transparency_requests`

    GROUP BY period_start
),

-- normalize detailed snapshots
detailed AS (

    SELECT
        CASE
            WHEN EXTRACT(MONTH FROM period_date)=6
                THEN DATE(EXTRACT(YEAR FROM period_date),6,1)

            WHEN EXTRACT(MONTH FROM period_date)=12
                THEN DATE(EXTRACT(YEAR FROM period_date),12,1)
        END AS period_start,

        SUM(total) AS detailed_total

    FROM `{{ var.project_id }}.stg.google_transparency_detailed`

    GROUP BY period_start
),

combined AS (

    SELECT
        COALESCE(r.period_start,d.period_start) AS period_start,

        COALESCE(google_requests,0) AS google_requests,
        COALESCE(requested_items,0) AS requested_items,
        COALESCE(legal_removed,0) AS legal_removed,
        COALESCE(policy_removed,0) AS policy_removed,
        COALESCE(detailed_total,0) AS detailed_total

    FROM requests r
    FULL OUTER JOIN detailed d
    USING (period_start)
),

periods AS (

    SELECT
        *,
        LEAD(period_start)
            OVER (ORDER BY period_start) AS next_period
    FROM combined
),

expanded AS (

    SELECT
        dd.date_key AS measurement_date,

        p.google_requests,
        p.requested_items,
        p.legal_removed,
        p.policy_removed,
        p.detailed_total

    FROM periods p
    CROSS JOIN calendar_bounds cb

    JOIN `{{ var.project_id }}.marts.dim_dates` dd
      ON dd.date_key >= GREATEST(p.period_start,cb.min_date)
     AND dd.date_key <
        COALESCE(
            p.next_period,
            DATE_ADD(cb.max_date,INTERVAL 1 DAY)
        )
)

SELECT
    measurement_date,

    google_requests,
    requested_items,
    legal_removed,
    policy_removed,
    detailed_total,

    ROUND(
        LOG(
            1
            + google_requests
            + requested_items
            + legal_removed
            + policy_removed
            + detailed_total
        ),
        4
    ) AS google_pressure_score

FROM expanded
ORDER BY measurement_date