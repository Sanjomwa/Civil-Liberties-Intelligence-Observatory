/* @bruin
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,
        platform,

        COUNT(*) AS total_measurements,
        COUNTIF(is_blocked) AS blocked_count,
        COUNTIF(blocking_confidence = 'HIGH') AS confirmed_blocks,

        SAFE_DIVIDE(COUNTIF(is_blocked), COUNT(*)) AS blocking_rate

    FROM `encoded-joy-485413-k5.int.ooni_signals`
    GROUP BY 1,2,3
),

acled AS (

    SELECT
        event_date AS measurement_date,
        LOWER(country) AS country,

        SUM(event_count) AS conflict_events,
        SUM(fatalities) AS fatalities,
        COUNTIF(event_type = 'Protests') AS protest_events_on_day

    FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
    GROUP BY 1,2
),

takedowns AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,
        platform,

        COUNT(*) AS total_takedown_requests,
        SUM(COALESCE(item_count,1)) AS items_removed

    FROM `encoded-joy-485413-k5.marts.fact_takedown_requests`
    GROUP BY 1,2,3
),

base AS (

    SELECT
        o.measurement_date,
        o.country,
        o.platform,

        o.total_measurements,
        o.blocked_count,
        o.confirmed_blocks,
        o.blocking_rate,

        COALESCE(a.conflict_events,0) AS conflict_events,
        COALESCE(a.fatalities,0) AS fatalities,
        COALESCE(a.protest_events_on_day,0) AS protest_events_on_day,

        COALESCE(t.total_takedown_requests,0) AS total_takedown_requests,
        COALESCE(t.items_removed,0) AS items_removed

    FROM ooni o

    LEFT JOIN acled a
        ON o.measurement_date = a.measurement_date
       AND o.country = a.country

    LEFT JOIN takedowns t
        ON o.measurement_date = t.measurement_date
       AND o.country = t.country
       AND o.platform = t.platform
),

features AS (

    SELECT
        *,

        -- flags
        blocked_count > 0 AS is_blocked,
        confirmed_blocks > 0 AS is_confirmed_block,
        (blocked_count > 0 AND protest_events_on_day > 0) AS blocked_on_protest_day,

        -- intensity score
        (
            0.5 * COALESCE(blocking_rate,0)
          + 0.3 * LEAST(conflict_events / 10.0,1.0)
          + 0.2 * LEAST(total_takedown_requests / 50.0,1.0)
        ) AS censorship_intensity_score

    FROM base
),

windows AS (

    SELECT
        *,

        CASE
            -- 🔥 Finance Bill Crisis (Kenya June 2024)
            WHEN measurement_date BETWEEN '2024-06-15' AND '2024-07-15'
                THEN 'FINANCE_BILL_CRISIS'

            -- Protest aligned
            WHEN protest_events_on_day > 0 AND is_blocked
                THEN 'PROTEST_SUPPRESSION'

            -- High blocking spikes
            WHEN blocking_rate > 0.5
                THEN 'HIGH_BLOCKING'

            -- Legal pressure only
            WHEN total_takedown_requests > 0 AND blocking_rate < 0.1
                THEN 'LEGAL_PRESSURE'

            ELSE 'BASELINE'
        END AS suppression_window_type

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
    ON w.measurement_date = d.date_key
;
