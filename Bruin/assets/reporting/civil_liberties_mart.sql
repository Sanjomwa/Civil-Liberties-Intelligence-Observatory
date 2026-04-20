/* @bruin
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default
description: Cross-source civil liberties analytical spine for Kenya.

materialization:
  type: table
  strategy: create+replace
@bruin */

-- =========================
-- OONI (SAFE BASE)
-- =========================
WITH ooni AS (

    SELECT
        measurement_date AS measurement_date,
        LOWER(country) AS country,

        SUM(ooni_tests) AS ooni_tests,
        SUM(blocked_tests) AS blocked_tests,
        SAFE_DIVIDE(SUM(blocked_tests), NULLIF(SUM(ooni_tests),0)) AS block_rate

    FROM `encoded-joy-485413-k5.marts.fact_network_blocking_daily`
    GROUP BY measurement_date, country
),

-- =========================
-- ACLED (SAFE BASE)
-- =========================
acled AS (

    SELECT
        event_date AS measurement_date,
        LOWER(country) AS country,

        SUM(events) AS conflict_events,
        SUM(fatalities) AS fatalities

    FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
    GROUP BY event_date, country
),

-- =========================
-- TAKEDOWNS
-- =========================
takedowns AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,

        SUM(number_of_requests) AS takedown_requests,
        SUM(COALESCE(item_count,0)) AS items_removed

    FROM `encoded-joy-485413-k5.marts.fact_takedown_trends`
    GROUP BY measurement_date, country
),

-- =========================
-- GOOGLE PRESSURE
-- =========================
pressure AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,

        SUM(number_of_requests) AS google_requests

    FROM `encoded-joy-485413-k5.marts.fact_country_pressure_daily`
    GROUP BY measurement_date, country
),

-- =========================
-- SAFE JOIN BASE (NO USING)
-- =========================
base AS (

    SELECT
        COALESCE(o.measurement_date, a.measurement_date, t.measurement_date, p.measurement_date) AS measurement_date,
        COALESCE(o.country, a.country, t.country, p.country) AS country,

        -- OONI
        COALESCE(o.ooni_tests,0) AS ooni_tests,
        COALESCE(o.blocked_tests,0) AS blocked_tests,
        COALESCE(o.block_rate,0) AS block_rate,

        -- ACLED
        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,

        -- TAKEDOWNS
        COALESCE(t.takedown_requests,0) AS takedown_requests,
        COALESCE(t.items_removed,0) AS items_removed,

        -- GOOGLE
        COALESCE(p.google_requests,0) AS google_requests

    FROM ooni o

    FULL OUTER JOIN acled a
        ON o.measurement_date = a.measurement_date
       AND o.country = a.country

    FULL OUTER JOIN takedowns t
        ON COALESCE(o.measurement_date, a.measurement_date) = t.measurement_date
       AND COALESCE(o.country, a.country) = t.country

    FULL OUTER JOIN pressure p
        ON COALESCE(o.measurement_date, a.measurement_date, t.measurement_date) = p.measurement_date
       AND COALESCE(o.country, a.country, t.country) = p.country
),

-- =========================
-- FEATURES
-- =========================
features AS (

    SELECT
        *,

        SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests,0)) AS block_ratio,

        (blocked_tests > 0) AS has_blocking,
        (conflict_events > 0) AS has_conflict,

        (
            0.5 * SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests,0))
          + 0.3 * LEAST(conflict_events / 10.0, 1.0)
          + 0.2 * LEAST((takedown_requests + google_requests) / 100.0, 1.0)
        ) AS civil_liberties_pressure_index

    FROM base
)

-- =========================
-- FINAL OUTPUT
-- =========================
SELECT
    f.*,

    d.year,
    d.month,
    d.year_month,
    d.day_name,
    d.is_weekend,
    d.political_context_flag

FROM features f

LEFT JOIN `encoded-joy-485413-k5.marts.dim_dates` d
    ON f.measurement_date = d.date_key;