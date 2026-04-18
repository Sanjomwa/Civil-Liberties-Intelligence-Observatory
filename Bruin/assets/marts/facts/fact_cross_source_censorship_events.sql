/* @bruin
tags:
  - marts_bq
name: fact_cross_source_censorship_events
type: bq.sql
connection: bigquery-default

description: |
  Master observatory spine combining:
  - OONI censorship signals
  - ACLED conflict events (same-day enrichment)

  Replaces legacy fact_censorship_impact as canonical cross-source model.

owner: civil-liberties-pipeline

depends:
  - fact_censorship_measurements
  - fact_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH daily_conflict_summary AS (

    SELECT
        measurement_date,

        COUNT(*) AS conflict_event_count,
        SUM(event_count) AS total_events,
        SUM(fatalities) AS total_fatalities,
        SUM(population_exposure) AS total_population_exposure,

        COUNTIF(is_censorship_trigger_event) AS trigger_event_count,

        STRING_AGG(DISTINCT event_type, ', ') AS event_types_on_day,

        STRING_AGG(
            DISTINCT county, ', '
            ORDER BY county
        ) AS counties_affected

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_conflict_events`
    GROUP BY measurement_date
),

base AS (

    SELECT
        c.*,
        d.conflict_event_count,
        d.total_events,
        d.total_fatalities,
        d.total_population_exposure,
        d.trigger_event_count,
        d.event_types_on_day,
        d.counties_affected,

        -- =========================
        -- CORE CROSS-SOURCE FLAG
        -- =========================
        CASE
            WHEN c.is_blocked AND COALESCE(d.trigger_event_count, 0) > 0
            THEN TRUE
            ELSE FALSE
        END AS blocked_on_protest_day,

        -- =========================
        -- SUPPRESSION LOGIC (UNCHANGED BUT CLEANED)
        -- =========================
        CASE
            WHEN c.is_confirmed_block
                 AND COALESCE(d.trigger_event_count, 0) > 0
            THEN 'Confirmed Block on Protest Day'

            WHEN c.is_blocked
                 AND COALESCE(d.trigger_event_count, 0) > 0
            THEN 'Probable Block on Protest Day'

            WHEN c.has_measurement_failure
                 AND COALESCE(d.trigger_event_count, 0) > 0
            THEN 'Disruption on Protest Day'

            WHEN c.is_confirmed_block
            THEN 'Confirmed Block (non-protest)'

            WHEN c.is_blocked
            THEN 'Probable Block (non-protest)'

            ELSE 'No Suppression Signal'
        END AS suppression_confidence_type

    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_measurements` c
    LEFT JOIN daily_conflict_summary d
        ON c.measurement_date = d.measurement_date
)

SELECT * FROM base;
