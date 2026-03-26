/* @bruin
name: stg.acled
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned ACLED aggregated conflict events
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - raw.acled_conflict_events

columns:
  - name: surrogate_id
    type: INTEGER
    description: Generated unique row identifier
    primary_key: true
    checks:
      - name: not_null
      - name: unique
  - name: week
    type: DATE
    description: Week of aggregation
    checks:
      - name: not_null
  - name: region
    type: STRING
    description: Region of event
  - name: country
    type: STRING
    description: Country of event
    checks:
      - name: not_null
  - name: admin1
    type: STRING
    description: First administrative division
  - name: event_type
    type: STRING
    description: Type of conflict event
  - name: sub_event_type
    type: STRING
    description: Sub-type of conflict event
  - name: events
    type: INTEGER
    description: Number of events
  - name: fatalities
    type: INTEGER
    description: Number of fatalities
  - name: population_exposure
    type: INTEGER
    description: Population exposure
  - name: disorder_type
    type: STRING
    description: Disorder type classification
  - name: id
    type: STRING
    description: ACLED record identifier (may be null or duplicated)
  - name: centroid_latitude
    type: FLOAT
    description: Latitude of centroid
  - name: centroid_longitude
    type: FLOAT
    description: Longitude of centroid
  - name: extracted_at
    type: TIMESTAMP
    description: Pipeline extraction timestamp
@bruin */

WITH raw AS (
    SELECT
        ROW_NUMBER() OVER () AS surrogate_id,
        STRPTIME(week, '%d-%B-%Y') AS week,
        UPPER(region) AS region,
        UPPER(country) AS country,
        admin1,
        event_type,
        sub_event_type,
        CAST(events AS INTEGER) AS events,
        CAST(fatalities AS INTEGER) AS fatalities,
        CAST(population_exposure AS INTEGER) AS population_exposure,
        disorder_type,
        id,
        CAST(centroid_latitude AS DOUBLE) AS centroid_latitude,
        CAST(centroid_longitude AS DOUBLE) AS centroid_longitude,
        extracted_at
    FROM dev_raw.acled_conflict_events
)

SELECT * FROM raw;
