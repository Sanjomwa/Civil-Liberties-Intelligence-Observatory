/* @bruin
name: fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default
depends:
  - fact_ooni_censorship_signals
  - fact_takedown_trends
  - fact_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH ooni AS (

    SELECT
        event_date,
        country,
        asn,
        block_rate AS ooni_block_rate,
        block_rate * 100 AS ooni_pressure_score
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_ooni_censorship_signals`
),

legal AS (

    SELECT
        DATE(event_date) AS event_date,
        country,

        -- aggregate legal + platform pressure
        SUM(number_of_requests) AS legal_requests,

        SAFE_DIVIDE(SUM(items_requested_removal), SUM(number_of_requests)) AS avg_request_intensity

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_takedown_trends`
    GROUP BY event_date, country
),

conflict AS (

    SELECT
        DATE(event_date) AS event_date,
        country,

        COUNT(*) AS conflict_events,
        AVG(fatalities) AS avg_fatalities
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_conflict_events`
    GROUP BY event_date, country
),

joined AS (

    SELECT

        COALESCE(o.event_date, l.event_date, c.event_date) AS event_date,
        COALESCE(o.country, l.country, c.country) AS country,
        o.asn,

        -- =========================
        -- SOURCE SIGNALS
        -- =========================
        COALESCE(o.ooni_block_rate, 0) AS ooni_block_rate,
        COALESCE(l.legal_requests, 0) AS legal_request_volume,
        COALESCE(c.conflict_events, 0) AS conflict_event_intensity,

        COALESCE(l.avg_request_intensity, 0) AS legal_intensity,
        COALESCE(c.avg_fatalities, 0) AS avg_fatalities,

        -- =========================
        -- NORMALIZED SCORES
        -- =========================
        (COALESCE(o.ooni_block_rate, 0) * 100) AS ooni_score,
        (LOG(1 + COALESCE(l.legal_requests, 0)) * 20) AS legal_score,
        (LOG(1 + COALESCE(c.conflict_events, 0)) * 15) AS conflict_score

    FROM ooni o
    FULL OUTER JOIN legal l
        ON o.event_date = l.event_date
        AND o.country = l.country

    FULL OUTER JOIN conflict c
        ON COALESCE(o.event_date, l.event_date) = c.event_date
        AND COALESCE(o.country, l.country) = c.country
),

final AS (

    SELECT
        *,
        
        -- =========================
        -- CROSS SOURCE INDEX
        -- =========================
        LEAST(
            100,
            ooni_score * 0.5 +
            legal_score * 0.3 +
            conflict_score * 0.2
        ) AS multi_source_pressure_score,

        CASE
            WHEN ooni_block_rate > 0.3
             AND legal_request_volume > 10 THEN TRUE
            ELSE FALSE
        END AS is_convergent_event,

        CASE
            WHEN ooni_block_rate > 0.4
             AND conflict_event_intensity > 3 THEN TRUE
            ELSE FALSE
        END AS is_escalation_cluster,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM joined
)

SELECT *
FROM final;
