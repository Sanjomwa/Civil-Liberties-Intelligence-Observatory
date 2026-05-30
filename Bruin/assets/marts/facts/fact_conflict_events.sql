/* @bruin
tags:
  - marts_bq
  - dataset_acled

name: marts.fact_conflict_events
type: bq.sql
connection: bigquery-default

description: |
  Canonical ACLED political stress fact.

  Grain:
  One normalized ACLED event observation.

  Supports:
  - temporal political stress analysis
  - digital pressure correlation modeling
  - event-window observability analytics

owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH normalized AS (

    SELECT
        event_date,
        country,
        region,
        admin1 AS county,

        event_type,
        sub_event_type,
        disorder_type,

        COALESCE(events, 1) AS event_count,
        COALESCE(fatalities, 0) AS fatalities,
        COALESCE(population_exposure, 0) AS population_exposure,

        centroid_latitude,
        centroid_longitude,

        extracted_at,

        year,
        month,
        day

    FROM `{{ var.project_id }}.stg.acled_conflict_events`

    WHERE event_date IS NOT NULL
),

classified AS (

    SELECT
        *,

        CASE
            WHEN event_type IN ('Protests', 'Riots')
              OR LOWER(sub_event_type) LIKE '%demonstration%'
              OR LOWER(sub_event_type) LIKE '%march%'
            THEN TRUE
            ELSE FALSE
        END AS is_high_political_stress_event,

        ROUND(
            (
                LOG(1 + fatalities) * 0.50
              + LOG(1 + event_count) * 0.30
              + LOG(1 + population_exposure / 1000) * 0.20
            ),
            4
        ) AS political_stress_score

    FROM normalized
),

scored AS (

    SELECT
        *,

        CASE
            WHEN political_stress_score >= 4.0 THEN 'SEVERE'
            WHEN political_stress_score >= 2.5 THEN 'ELEVATED'
            WHEN political_stress_score >= 1.0 THEN 'MODERATE'
            ELSE 'LOW'
        END AS political_stress_level

    FROM classified
)

SELECT
    event_date,

    country,
    region,
    county,

    event_type,
    sub_event_type,
    disorder_type,

    event_count,
    fatalities,
    population_exposure,

    centroid_latitude,
    centroid_longitude,

    extracted_at,

    year,
    month,
    day,

    is_high_political_stress_event,

    political_stress_score,
    political_stress_level

FROM scored;