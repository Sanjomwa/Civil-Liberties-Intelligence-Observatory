/* @bruin
tags:
  - stg_bq
  - dataset_ooni_conflict_measurements
name: stg.ooni
type: bq.sql
connection: bigquery-default
description: Cleaned and standardized OONI censorship measurements for Kenya (Jun 2023 – Jun 2025)
owner: civil-liberties-pipeline

depends:
  - load.ooni_to_gcs

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        measurement_id,
        probe_cc AS country,
        asn,
        test_name,
        input,
        start_time,
        status,
        probe_cc,
        probe_asn,
        extracted_at,
        CASE
            -- plausible UNIX seconds range
            WHEN start_time BETWEEN 946684800 AND 4102444800
                THEN TIMESTAMP_SECONDS(start_time)
            -- plausible UNIX milliseconds range
            WHEN start_time BETWEEN 946684800000 AND 4102444800000
                THEN TIMESTAMP_MILLIS(start_time)
            -- plausible UNIX microseconds range
            WHEN start_time BETWEEN 946684800000000 AND 4102444800000000
                THEN TIMESTAMP_MICROS(start_time)
            ELSE NULL
        END AS start_ts
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
    WHERE probe_cc = 'KE'
),

raw AS (
    SELECT
        measurement_id,
        country,
        asn,
        test_name,
        input,
        start_ts AS start_time,
        status,
        probe_cc,
        probe_asn,
        extracted_at,
        DATE(start_ts)                   AS measurement_date,
        EXTRACT(YEAR  FROM start_ts)     AS year,
        EXTRACT(MONTH FROM start_ts)     AS month,
        CASE
            WHEN test_name IN ('web_connectivity', 'dnscheck')
                THEN 'Website/DNS Blocking'
            WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal')
                THEN 'Messaging App Blocking'
            WHEN test_name IN ('tor', 'psiphon')
                THEN 'Circumvention Tool Blocking'
            ELSE 'Other'
        END                              AS test_category
    FROM base
    WHERE start_ts IS NOT NULL
)

SELECT * FROM raw