/* @bruin
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

WITH raw AS (
    SELECT
        measurement_id,
        probe_cc                                        AS country,
        asn,
        test_name,
        input,
        start_time,
        status,
        probe_cc,
        probe_asn,
        extracted_at,
        DATE(start_time)                                AS measurement_date,
        EXTRACT(YEAR  FROM start_time)                  AS year,
        EXTRACT(MONTH FROM start_time)                  AS month,
        CASE
            WHEN test_name IN ('web_connectivity', 'dnscheck')
                THEN 'Website/DNS Blocking'
            WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal')
                THEN 'Messaging App Blocking'
            WHEN test_name IN ('tor', 'psiphon')
                THEN 'Circumvention Tool Blocking'
            ELSE 'Other'
        END                                             AS test_category
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
    WHERE probe_cc = 'KE'
)

SELECT * FROM raw
