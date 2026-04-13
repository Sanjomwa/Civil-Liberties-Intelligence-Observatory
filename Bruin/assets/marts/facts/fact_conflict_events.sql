/* @bruin
tags:
  - marts_bq 
name: fact_conflict_events
type: bq.sql
connection: bigquery-default
description: |
  Grain: one row per ACLED conflict/protest event in Kenya.
  Drives the conflict timeline and regional unrest map dashboards.
  Joins to dim_dates on measurement_date, dim_regions on admin1,
  dim_event_types on event_type + sub_event_type.
owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    event_id,
    measurement_date,
    region,
    admin1                                      AS county,
    event_type,
    sub_event_type,
    disorder_type,
    events                                      AS event_count,
    fatalities,
    population_exposure,
    centroid_latitude,
    centroid_longitude,
    extracted_at,
    year,

    -- Flag events most likely to trigger censorship responses
    CASE
        WHEN event_type IN ('Protests', 'Riots')
          OR sub_event_type LIKE '%demonstration%'
          OR sub_event_type LIKE '%march%'          THEN TRUE
        ELSE FALSE
    END                                             AS is_censorship_trigger_event,

    -- Severity score for choropleth map weighting
    CASE
        WHEN fatalities > 10                        THEN 'High'
        WHEN fatalities > 0                         THEN 'Medium'
        ELSE 'Low'
    END                                             AS severity_level

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.acled_conflict_events`
WHERE country = 'Kenya'
