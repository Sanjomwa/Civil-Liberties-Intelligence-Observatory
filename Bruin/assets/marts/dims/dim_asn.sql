/* @bruin
tags:
  - marts_bq
name: dim_asn
type: bq.sql
connection: bigquery-default
description: Canonical ASN dimension for Kenya censorship observatory.

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT DISTINCT
        asn,
        country
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.int_ooni_signals`
),

cleaned AS (

    SELECT
        asn,
        country,

        -- normalize ASN format (defensive)
        CAST(asn AS STRING) AS asn_id,

        -- placeholder enrichment fields (future-safe)
        CASE
            WHEN asn LIKE '32%' THEN 'mobile'
            WHEN asn LIKE '3%' THEN 'fixed'
            ELSE 'unknown'
        END AS isp_type

    FROM base
)

SELECT *
FROM cleaned;
