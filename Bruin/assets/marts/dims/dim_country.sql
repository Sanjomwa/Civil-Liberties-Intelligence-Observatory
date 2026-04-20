/* @bruin
tags:
  - marts_bq
name: marts.dim_country
type: bq.sql
connection: bigquery-default
description: |
  Country dimension table derived from various OONI-related datasets.
  Standardizes country names and ISO codes for consistent analysis across marts.
materialization:
  type: table
  strategy: create+replace
depends:
  -  stg.lumen_requests
  -  int.ooni_signals
  -  stg.acled_conflict_events
  -  stg.google_transparency_requests
  -  stg.google_transparency_detailed

@bruin */ 
WITH raw AS (
  SELECT country AS raw_country FROM `stg.lumen_requests`
  UNION DISTINCT
  SELECT country FROM `int.ooni_signals`
  UNION DISTINCT
  SELECT country FROM `stg.acled_conflict_events`
  UNION DISTINCT
  SELECT country FROM `stg.google_transparency_requests`
  UNION DISTINCT
  SELECT country_region FROM `stg.google_transparency_detailed`
)

SELECT
  raw_country,

  CASE
    WHEN raw_country IN ('KE','ke','Kenya','kenya','KENYA') THEN 'Kenya'
    WHEN raw_country = 'Democratic Republic of Congo' THEN 'DRC'
    ELSE INITCAP(raw_country)
  END AS country_name,

  CASE
    WHEN raw_country IN ('KE','ke') THEN 'KE'
    ELSE NULL
  END AS iso2

FROM raw;
