/* @bruin
tags:
  - marts_bq 
name: dim_regions
type: bq.sql
connection: bigquery-default
description: |
  Kenya administrative regions derived from ACLED conflict events.
  Provides county-level (admin1) geographic dimension with centroid
  coordinates for map visualisations in Streamlit.
owner: civil-liberties-pipeline

depends:
  - stg.acled_conflict_events

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT DISTINCT
    -- Surrogate key for joining
    FARM_FINGERPRINT(CONCAT(COALESCE(region, ''), '||', COALESCE(admin1, '')))
                                                AS region_key,
    country,
    region,
    admin1                                      AS county,

    -- Take the average centroid for counties that appear multiple times
    AVG(centroid_latitude)  OVER (PARTITION BY admin1) AS centroid_latitude,
    AVG(centroid_longitude) OVER (PARTITION BY admin1) AS centroid_longitude,

    -- Classify by region type for dashboard filtering
    CASE
        WHEN admin1 = 'Nairobi'                 THEN 'Capital'
        WHEN admin1 IN ('Mombasa','Kisumu','Nakuru','Eldoret')
                                                THEN 'Major Urban'
        WHEN region = 'Coast'                   THEN 'Coast Region'
        WHEN region = 'Rift Valley'             THEN 'Rift Valley'
        WHEN region = 'Nyanza'                  THEN 'Nyanza'
        WHEN region = 'Western'                 THEN 'Western'
        WHEN region = 'Central'                 THEN 'Central'
        WHEN region = 'Eastern'                 THEN 'Eastern'
        WHEN region = 'North Eastern'           THEN 'North Eastern'
        ELSE 'Other'
    END                                         AS region_group

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.acled_conflict_events`
WHERE country = 'Kenya'
  AND admin1 IS NOT NULL
ORDER BY region, admin1
