/* @bruin
name: stg.acled_conflict_events
type: bq.sql
connection: bigquery-default
description: Cleaned ACLED conflict events with derived fields for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.acled_conflict_events_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH raw AS (
    SELECT
        id                                                  AS event_id,
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
        centroid_latitude,
        centroid_longitude,
        extracted_at,
        -- ACLED week format is 'DD-MonthName-YYYY', e.g. '01-June-2023'
        PARSE_DATE('%d-%B-%Y', week)                        AS measurement_date,
        EXTRACT(YEAR FROM PARSE_DATE('%d-%B-%Y', week))     AS year
    FROM `encoded-joy-485413-k5.civil_liberties_staging.acled_conflict_events`
    WHERE country = 'Kenya'
)

SELECT * FROM raw
