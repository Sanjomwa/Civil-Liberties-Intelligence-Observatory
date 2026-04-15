/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_impact
type: bq.sql
connection: bigquery-default
description: OONI measurements enriched with same-day ACLED context.
owner: civil-liberties-pipeline
depends:
  - marts.fact_censorship_measurements
  - marts.fact_conflict_events
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
    STRING_AGG(DISTINCT county, ', ' ORDER BY county LIMIT 5) AS counties_affected
  FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_conflict_events`
  GROUP BY measurement_date
)
SELECT
  c.measurement_id,
  c.measurement_date,
  c.test_name,
  c.test_category,
  c.status AS censorship_status,
  c.is_blocked,
  c.is_confirmed_block,
  c.tested_url_or_app,
  c.asn,
  c.probe_asn,
  c.year,
  c.month,
  c.extracted_at,
  d.conflict_event_count,
  d.total_events,
  d.total_fatalities,
  d.trigger_event_count,
  d.event_types_on_day,
  d.counties_affected,
  d.total_population_exposure,
  CASE
    WHEN c.is_blocked AND d.trigger_event_count > 0 THEN TRUE
    ELSE FALSE
  END AS blocked_on_protest_day
FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_measurements` c
LEFT JOIN daily_conflict_summary d
  ON c.measurement_date = d.measurement_date;
