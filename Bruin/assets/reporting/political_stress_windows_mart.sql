/* @bruin
tags:
  - reporting

name: reporting.mart_political_stress_windows
type: bq.sql
connection: bigquery-default

description: |
  Detects elevated digital suppression windows in Kenya by fusing
  political conflict pressure, legal takedown activity, platform
  moderation pressure, and network censorship anomalies.

depends:
  - marts.fact_country_pressure_daily
  - marts.fact_network_blocking_daily
  - marts.dim_dates

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH network AS (

    SELECT
        measurement_date,

        AVG(blocking_rate) AS avg_blocking_rate,

        AVG(confidence_weighted_blocking)
            AS weighted_blocking

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country = 'KE'

    GROUP BY measurement_date

),

country_pressure AS (

    SELECT
        measurement_date,

        composite_pressure_score AS country_pressure,

        conflict_pressure_score AS conflict_pressure,

        legal_pressure_score AS legal_pressure,

        platform_pressure_score AS platform_pressure

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`

    WHERE iso2 = 'KE'

),

base AS (

    SELECT
        d.date_key,

        COALESCE(c.country_pressure, 0)
            AS country_pressure,

        COALESCE(c.conflict_pressure, 0)
            AS conflict_pressure,

        COALESCE(c.legal_pressure, 0)
            AS legal_pressure,

        COALESCE(c.platform_pressure, 0)
            AS platform_pressure,

        COALESCE(n.avg_blocking_rate, 0)
            AS blocking_rate,

        COALESCE(n.weighted_blocking, 0)
            AS weighted_blocking

    FROM `encoded-joy-485413-k5.marts.dim_dates` d

    LEFT JOIN country_pressure c
        ON d.date_key = c.measurement_date

    LEFT JOIN network n
        ON d.date_key = n.measurement_date

),

scored AS (

    SELECT
        *,

        ROUND(
            country_pressure
            + (blocking_rate * 5)
            + (weighted_blocking * 4),
            4
        ) AS stress_score

    FROM base

),

windowed AS (

    SELECT
        *,

        AVG(stress_score)
        OVER (
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS baseline

    FROM scored

),

finalized AS (

    SELECT
        *,

        ROUND(
            stress_score - baseline,
            4
        ) AS pressure_delta

    FROM windowed

)

SELECT
    date_key,

    country_pressure,
    conflict_pressure,
    legal_pressure,
    platform_pressure,

    blocking_rate,
    weighted_blocking,

    stress_score,

    pressure_delta,

    baseline,

    CASE
        WHEN pressure_delta >= 2.0
            THEN 'CRITICAL'

        WHEN pressure_delta >= 1.0
            THEN 'HIGH'

        WHEN pressure_delta >= 0.25
            THEN 'ELEVATED'

        ELSE 'NORMAL'
    END AS suppression_window_class,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM finalized

ORDER BY date_key