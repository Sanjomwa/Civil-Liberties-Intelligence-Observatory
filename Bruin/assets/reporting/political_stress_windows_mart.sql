/* @bruin
tags:
  - reporting

name: reporting.mart_political_stress_windows
type: bq.sql
connection: bigquery-default

description: |
  Detects elevated digital suppression windows in Kenya by fusing
  political conflict pressure, legal pressure, platform pressure,
  and network censorship anomalies.

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

        AVG(blocking_rate) AS blocking_rate,

        AVG(confidence_weighted_blocking)
            AS weighted_blocking

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`

    WHERE country = 'KE'

    GROUP BY measurement_date
),

country_pressure AS (

    SELECT
        measurement_date,

        conflict_pressure_score,
        legal_pressure_score,
        platform_pressure_score

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`

    WHERE iso2 = 'KE'
),

base AS (

    SELECT
        d.date_key,

        COALESCE(c.conflict_pressure_score, 0)
            AS conflict_pressure,

        COALESCE(c.legal_pressure_score, 0)
            AS legal_pressure,

        COALESCE(c.platform_pressure_score, 0)
            AS platform_pressure,

        COALESCE(n.blocking_rate, 0)
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
            (
                conflict_pressure * 0.45
                + legal_pressure * 0.25
                + platform_pressure * 0.15
                + blocking_rate * 40
                + weighted_blocking * 30
            ),
            4
        ) AS composite_pressure_score

    FROM base
),

windowed AS (

    SELECT
        *,

        AVG(composite_pressure_score)
        OVER (
            ORDER BY date_key
            ROWS BETWEEN 30 PRECEDING AND 1 PRECEDING
        ) AS rolling_baseline_pressure

    FROM scored
),

finalized AS (

    SELECT
        *,

        ROUND(
            composite_pressure_score
            - rolling_baseline_pressure,
            4
        ) AS pressure_delta,

        ROUND(
            1 / (
                1 + EXP(
                    -(
                        composite_pressure_score
                        - rolling_baseline_pressure
                    )
                )
            ),
            4
        ) AS suppression_window_probability

    FROM windowed
)

SELECT
    date_key,

    conflict_pressure,
    legal_pressure,
    platform_pressure,

    blocking_rate,
    weighted_blocking,

    composite_pressure_score,

    rolling_baseline_pressure,

    pressure_delta,

    suppression_window_probability,

    CASE
        WHEN pressure_delta >= 1.8
            THEN 'CRITICAL_OBSERVABILITY_WINDOW'

        WHEN pressure_delta >= 1.2
            THEN 'HIGH_STRESS_WINDOW'

        WHEN pressure_delta >= 0.6
            THEN 'ELEVATED_PRESSURE'

        ELSE 'NORMAL'
    END AS suppression_window_class,

    CURRENT_TIMESTAMP() AS snapshot_at

FROM finalized

ORDER BY date_key