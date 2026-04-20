/* @bruin
tags:
  - marts_bq
name: marts.fact_conflict_events
type: bq.sql
connection: bigquery-default
description: One row per ACLED conflict/protest event in Kenya.
owner: civil-liberties-pipeline
depends:
  - stg.acled_conflict_events
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  event_date ,
  country,
  region,
  admin1 AS county,
  event_type,
  sub_event_type,
  disorder_type,
  events AS event_count,
  fatalities,
  population_exposure,
  centroid_latitude,
  centroid_longitude,
  extracted_at,
  year,
  CASE
    WHEN event_type IN ('Protests', 'Riots')
      OR sub_event_type LIKE '%demonstration%'
      OR sub_event_type LIKE '%march%' THEN TRUE
    ELSE FALSE
  END AS is_censorship_trigger_event,
  CASE
    WHEN fatalities > 10 THEN 'High'
    WHEN fatalities > 0 THEN 'Medium'
    ELSE 'Low'
  END AS severity_level
FROM `encoded-joy-485413-k5.stg.acled_conflict_events`
WHERE country = 'Kenya';
