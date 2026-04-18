/* @bruin
tags:
  - marts_bq
name: marts.fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default
@bruin */

WITH ooni_spine AS (

    SELECT
        measurement_date,
        LOWER(country) AS country,
        asn,

        COUNT(*) AS ooni_tests,
        COUNTIF(is_blocked = TRUE) AS blocked_tests,

        SAFE_DIVIDE(COUNTIF(is_blocked = TRUE), COUNT(*)) AS block_rate,

        MAX(CASE WHEN blocking_confidence = 'HIGH' THEN 1 ELSE 0 END)
            AS high_conf_block_present,

        SUM(CASE 
            WHEN blocking_signal_type = 'NETWORK_BLOCK' THEN 1 ELSE 0 
        END) AS network_block_signals

    FROM `encoded-joy-485413-k5.int.ooni_signals`

    GROUP BY 1, 2, 3
),

/* =========================
   ACLED FIX (NO PARSING — DATE ALREADY CLEAN)
   ========================= */
acled_spine AS (

    SELECT
        event_date AS measurement_date,
        LOWER(country) AS country,

        SUM(events) AS conflict_events,
        SUM(fatalities) AS fatalities,
        SUM(population_exposure) AS population_exposure,
        COUNT(DISTINCT event_type) AS event_diversity

    FROM `encoded-joy-485413-k5.stg.acled_conflict_events`

    WHERE event_date IS NOT NULL

    GROUP BY 1, 2
),

/* =========================
   LUMEN (MICROSECOND FIX)
   ========================= */
lumen_normalized AS (

    SELECT
        LOWER(country) AS country,
        request_count,
        item_count,

        DATE(
            TIMESTAMP_MICROS(CAST(date_submitted AS INT64))
        ) AS measurement_date

    FROM `encoded-joy-485413-k5.stg.lumen_requests`

    WHERE date_submitted IS NOT NULL
),

lumen_spine AS (

    SELECT
        measurement_date,
        country,

        SUM(request_count) AS takedown_requests,
        SUM(item_count) AS takedown_items

    FROM lumen_normalized

    GROUP BY 1, 2
),

base_spine AS (

    SELECT
        o.measurement_date,
        o.country,
        o.asn,

        o.ooni_tests,
        o.blocked_tests,
        o.block_rate,
        o.high_conf_block_present,
        o.network_block_signals,

        COALESCE(a.conflict_events, 0) AS conflict_events,
        COALESCE(a.fatalities, 0) AS fatalities,
        COALESCE(a.population_exposure, 0) AS population_exposure,
        COALESCE(a.event_diversity, 0) AS event_diversity,

        COALESCE(l.takedown_requests, 0) AS takedown_requests,
        COALESCE(l.takedown_items, 0) AS takedown_items

    FROM ooni_spine o

    LEFT JOIN acled_spine a
        ON o.measurement_date = a.measurement_date
       AND LOWER(o.country) = a.country

    LEFT JOIN lumen_spine l
        ON o.measurement_date = l.measurement_date
       AND LOWER(o.country) = l.country
)

SELECT
    *,

    (
        COALESCE(block_rate, 0) * 0.5
      + LEAST(conflict_events / 10.0, 0.3)
      + LEAST(takedown_requests / 100.0, 0.2)
    ) AS cross_source_pressure_score,

    CASE
        WHEN block_rate > 0.7
         AND conflict_events > 0
         AND takedown_requests > 0 THEN 'High Multi-Source Suppression'

        WHEN block_rate > 0.7
         AND conflict_events > 0 THEN 'Conflict-Aligned Blocking'

        WHEN block_rate > 0.7 THEN 'Network Blocking Only'

        WHEN conflict_events > 0 THEN 'Conflict Pressure Only'

        WHEN takedown_requests > 0 THEN 'Legal / Platform Pressure Only'

        ELSE 'Baseline'
    END AS repression_state

FROM base_spine;