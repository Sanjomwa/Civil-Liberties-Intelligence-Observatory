/* @bruin
tags:
  - reporting_bq
name: reporting.civil_liberties_mart
type: bq.sql
connection: bigquery-default

description: Final observatory mart for Streamlit (clean + stable).

owner: civil-liberties-pipeline

depends:
  - marts.fact_cross_source_censorship_events
  - marts.fact_asn_repression_index
  - marts.fact_asn_repression_anomalies
  - marts.dim_dates
  - marts.dim_asn

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT
        c.measurement_date,
        c.country,
        c.asn,

        c.ooni_tests,
        c.blocked_tests,
        c.block_rate,

        c.conflict_events,
        c.fatalities,
        c.population_exposure,

        c.takedown_requests,
        c.takedown_items,

        c.cross_source_pressure_score,
        c.repression_state

    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events` c
)

SELECT

    b.*,

    -- date enrichment
    d.year,
    d.month,
    d.day,
    d.year_month,
    d.day_name,
    d.month_name,
    d.is_weekend,
    d.political_context_flag,

    -- ASN enrichment
    a.isp_type,

    -- repression index
    r.asn_repression_index_v3,

    -- anomaly detection
    an.z_score,
    an.anomaly_type,
    an.is_anomaly,

    -- FINAL SCORE
    (
        0.5 * b.block_rate +
        0.3 * LEAST(b.conflict_events / 10.0, 1.0) +
        0.2 * LEAST(b.takedown_requests / 100.0, 1.0)
    ) AS overall_censorship_score

FROM base b

LEFT JOIN `encoded-joy-485413-k5.marts.dim_dates` d
    ON b.measurement_date = d.date_key

LEFT JOIN (
    SELECT
        asn_id,
        isp_type
    FROM `encoded-joy-485413-k5.marts.dim_asn`
) a
ON CAST(b.asn AS STRING) = a.asn_id

LEFT JOIN `encoded-joy-485413-k5.marts.fact_asn_repression_index` r
    ON b.measurement_date = r.measurement_date
   AND b.asn = r.asn

LEFT JOIN `encoded-joy-485413-k5.marts.fact_asn_repression_anomalies` an
    ON b.measurement_date = an.measurement_date
   AND b.asn = an.asn;