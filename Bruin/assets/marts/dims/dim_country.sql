/* @bruin
tags:
  - marts_bq
name: marts.dim_country
type: bq.sql
connection: bigquery-default

description: |
  Canonical country dimension for observability analysis.
  Standardizes source country labels into normalized ISO-based geography keys
  and analytical scope classifications.

materialization:
  type: table
  strategy: create+replace

depends:
  - stg.lumen_requests
  - int.ooni_experiment_results
  - stg.acled_conflict_events
  - stg.google_transparency_requests
  - stg.google_transparency_detailed
@bruin */

WITH raw AS (

    SELECT country AS raw_country FROM `stg.lumen_requests`
    UNION DISTINCT
    -- Repointed off int.ooni_signals (retired 2026-07-06, TD-56) to the live
    -- OONI interpretation table; both expose the same country values.
    SELECT country FROM `int.ooni_experiment_results`
    UNION DISTINCT
    SELECT country FROM `stg.acled_conflict_events`
    UNION DISTINCT
    SELECT country FROM `stg.google_transparency_requests`
    UNION DISTINCT
    SELECT country_region FROM `stg.google_transparency_detailed`

),

normalized AS (

    SELECT
        raw_country,

        CASE
            WHEN UPPER(raw_country) IN ('KE', 'KENYA') THEN 'Kenya'
            WHEN UPPER(raw_country) IN ('CD', 'COD', 'DEMOCRATIC REPUBLIC OF CONGO') THEN 'Democratic Republic of the Congo'
            ELSE raw_country
        END AS country_name,

        CASE
            WHEN UPPER(raw_country) IN ('KE', 'KENYA') THEN 'KE'
            WHEN UPPER(raw_country) IN ('CD', 'COD', 'DEMOCRATIC REPUBLIC OF CONGO') THEN 'CD'
            ELSE NULL
        END AS iso2

    FROM raw

)

SELECT
    CONCAT('CTRY_', COALESCE(iso2, 'UNK')) AS country_key,
    raw_country,
    country_name,
    iso2,

    CASE
        WHEN iso2 = 'KE' THEN 'PRIMARY_OBSERVATION_SCOPE'
        WHEN iso2 IS NOT NULL THEN 'REGIONAL_CONTEXT'
        ELSE 'UNCLASSIFIED'
    END AS analytical_scope

FROM normalized