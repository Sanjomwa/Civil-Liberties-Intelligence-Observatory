/* @bruin
name: stg.ooni
type: duckdb.sql
connection: duckdb-parquet

environments:
  staging:
    type: bq.sql
    connection: bigquery-default
  prod:
    type: bq.sql
    connection: bigquery-default

description: Cleaned and standardized OONI censorship measurements for Kenya
owner: civil-liberties-pipeline

materialization:
  type: table
  strategy: create+replace

depends:
  - load.ooni_to_gcs
@bruin */

WITH raw AS (
    SELECT
        measurement_id,
        probe_cc AS country,                    -- standardize naming
        asn,
        test_name,
        input,
        start_time,
        status,
        probe_cc,
        probe_asn,
        extracted_at,
        -- Add useful derived fields
        DATE(start_time) AS measurement_date,
        EXTRACT(YEAR FROM start_time) AS year,
        EXTRACT(MONTH FROM start_time) AS month,
        CASE 
            WHEN test_name IN ('web_connectivity', 'dnscheck') THEN 'Website/DNS Blocking'
            WHEN test_name IN ('whatsapp', 'telegram', 'facebook_messenger', 'signal') THEN 'Messaging App Blocking'
            WHEN test_name IN ('tor', 'psiphon') THEN 'Circumvention Tool Blocking'
            ELSE 'Other'
        END AS test_category
    FROM {{ ref('load.ooni_to_gcs') }}
)

SELECT * FROM raw;
