/* @bruin
tags:
  - staging
name: stg.acled_conflict_events
type: bq.sql
connection: bigquery-default
description: |
  Clean ACLED staging layer.
  Normalizes week string into proper event_date for downstream joins.

owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH parsed AS (

    SELECT
        week,
        region,
        country,
        admin1,

        event_type,
        sub_event_type,

        events,
        fatalities,
        population_exposure,
        disorder_type,

        id,
        centroid_latitude,
        centroid_longitude,

        extracted_at,

        /* -----------------------------
           FIX: convert "23-October-2004"
           ----------------------------- */
        SAFE.PARSE_DATE(
            "%d-%B-%Y",
            week
        ) AS event_date

    FROM `encoded-joy-485413-k5.raw.acled_conflict_events`
)

SELECT
    event_date,
    week,
    region,
    country,
    admin1,

    event_type,
    sub_event_type,

    events,
    fatalities,
    population_exposure,
    disorder_type,

    id,
    centroid_latitude,
    centroid_longitude,

    extracted_at,

    EXTRACT(YEAR FROM event_date) AS year,
    EXTRACT(MONTH FROM event_date) AS month,
    EXTRACT(DAY FROM event_date) AS day

FROM parsed;
