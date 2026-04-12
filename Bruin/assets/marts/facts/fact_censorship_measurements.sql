/* @bruin
name: fact_censorship_measurements
type: bq.sql
connection: bigquery-default
description: |
  Grain: one row per OONI measurement for Kenya.
  Core fact for the censorship timeline and blocking rate dashboards.
  Joins to dim_dates on measurement_date, dim_test_categories on test_category,
  dim_platforms on test_name.
owner: civil-liberties-pipeline

depends:
  - stg.ooni

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    measurement_id,
    country,
    asn,
    test_name,
    input                                       AS tested_url_or_app,
    start_time,
    status,
    probe_cc,
    probe_asn,
    extracted_at,
    measurement_date,
    test_category,
    year,
    month,

    -- Blocking flag for easy aggregation in Streamlit
    CASE WHEN status IN ('anomaly', 'confirmed', 'failure') THEN TRUE ELSE FALSE END
                                                AS is_blocked,

    -- Confirmed block (higher confidence than anomaly)
    CASE WHEN status = 'confirmed' THEN TRUE ELSE FALSE END
                                                AS is_confirmed_block

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.ooni_measurements`
WHERE probe_cc = 'KE'
