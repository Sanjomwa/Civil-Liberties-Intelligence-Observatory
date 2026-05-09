/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_asn
type: bq.sql
connection: bigquery-default

description: |
  Canonical ASN dimension for Kenyan OONI observability.

  Models:
  - ASN normalization
  - Kenya network relevance
  - network class
  - censorship sensitivity heuristics

  Scope:
  Kenya civil-liberties analysis
  June 2023 → June 2025

depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT DISTINCT
        CAST(probe_asn AS INT64) AS asn_numeric
    FROM `encoded-joy-485413-k5.stg.ooni_measurements`
    WHERE probe_asn IS NOT NULL

)

SELECT
    CONCAT('AS', CAST(asn_numeric AS STRING)) AS asn,
    asn_numeric,

    CASE
        WHEN asn_numeric IN (36926, 37061, 33771)
            THEN 'MAJOR_KENYA_PROVIDER'

        WHEN asn_numeric IN (15399)
            THEN 'SECONDARY_PROVIDER'

        WHEN asn_numeric IN (15169, 8075)
            THEN 'GLOBAL_INFRASTRUCTURE'

        WHEN CAST(asn_numeric AS STRING) LIKE '3%'
            THEN 'REGIONAL_NETWORK'

        ELSE 'OTHER'
    END AS network_class,

    CASE
        WHEN asn_numeric IN (
            36926,
            37061,
            33771,
            15399
        )
        THEN TRUE
        ELSE FALSE
    END AS is_kenya_observability_core,

    CASE
        WHEN asn_numeric IN (36926, 37061)
            THEN 0.95

        WHEN asn_numeric IN (33771, 15399)
            THEN 0.80

        WHEN asn_numeric IN (15169, 8075)
            THEN 0.35

        ELSE 0.50
    END AS censorship_sensitivity_score,

    CURRENT_TIMESTAMP() AS created_at

FROM base
ORDER BY asn_numeric;