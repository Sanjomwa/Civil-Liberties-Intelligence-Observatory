/* @bruin
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default
description: |
  Cross-source civil liberties analytical spine for Kenya.
  Built from curated fact tables only (no raw signals).
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,
        asn,

        SUM(ooni_tests) AS ooni_tests,
        SUM(blocked_tests) AS blocked_tests,
        SAFE_DIVIDE(SUM(blocked_tests), SUM(ooni_tests)) AS block_rate,

        SUM(network_block_signals) AS network_block_signals

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
    GROUP BY 1,2,3
),

acled AS (

    SELECT
        event_date AS measurement_date,
        LOWER(country) AS country,

        SUM(events) AS conflict_events,
        SUM(fatalities) AS fatalities

    FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
    GROUP BY 1,2
),

takedowns AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,

        SUM(total_requests) AS takedown_requests,
        SUM(items_removed) AS items_removed

    FROM `encoded-joy-485413-k5.marts.fact_takedown_trends`
    GROUP BY 1,2
),

pressure AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,

        SUM(takedown_requests) AS google_requests

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
    GROUP BY 1,2
),

base AS (

    SELECT
        COALESCE(o.measurement_date, a.measurement_date, t.measurement_date, p.measurement_date) AS measurement_date,
        COALESCE(o.country, a.country, t.country, p.country) AS country,

        -- OONI
        COALESCE(o.ooni_tests,0) AS ooni_tests,
        COALESCE(o.blocked_tests,0) AS blocked_tests,
        COALESCE(o.block_rate,0) AS block_rate,
        COALESCE(o.network_block_signals,0) AS network_block_signals,

        -- ACLED
        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,

        -- Lumen / takedown trends
        COALESCE(t.takedown_requests,0) AS takedown_requests,
        COALESCE(t.items_removed,0) AS items_removed,

        -- Google / cross-source pressure
        COALESCE(p.google_requests,0) AS google_requests

    FROM ooni o
    FULL OUTER JOIN acled a USING (measurement_date, country)
    FULL OUTER JOIN takedowns t USING (measurement_date, country)
    FULL OUTER JOIN pressure p USING (measurement_date, country)
),

features AS (

    SELECT
        *,

        -- core flags
        blocked_tests > 0 AS has_blocking,
        conflict_events > 0 AS has_conflict,

        (blocked_tests > 0 AND conflict_events > 0) AS conflict_block_overlap,

        -- intensity score (clean + stable)
        (
            0.5 * SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests,0))
          + 0.3 * LEAST(conflict_events / 10.0, 1.0)
          + 0.2 * LEAST((takedown_requests + google_requests) / 100.0, 1.0)
        ) AS civil_liberties_pressure_index

    FROM base
),

windows AS (

    SELECT
        *,

        CASE
            WHEN measurement_date BETWEEN '2024-06-15' AND '2024-07-15'
                THEN 'FINANCE_BILL_CRISIS'

            WHEN conflict_events > 0 AND blocked_tests > 0
                THEN 'ACTIVE_SUPPRESSION'

            WHEN block_rate > 0.5
                THEN 'HIGH_NETWORK_BLOCKING'

            WHEN takedown_requests > 0 OR google_requests > 0
                THEN 'LEGAL_OR_PLATFORM_PRESSURE'

            ELSE 'BASELINE'
        END AS suppression_window

    FROM features
)

SELECT
    w.*,

    d.year,
    d.month,
    d.year_month,
    d.day_name,
    d.is_weekend,
    d.political_context_flag

FROM windows w

LEFT JOIN `encoded-joy-485413-k5.marts.dim_dates` d
    ON w.measurement_date = d.date_key;
