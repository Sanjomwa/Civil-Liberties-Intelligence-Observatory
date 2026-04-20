/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default

description: |
  ASN-level repression index (v3).
  Combines:
    - OONI blocking intensity
    - ACLED conflict pressure
    - Lumen takedown pressure
    - Measurement quality weighting

  Grain: measurement_date × asn

owner: civil-liberties-pipeline

depends:
  - marts.dim_measurement_quality

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH spine AS (

    SELECT
        measurement_date,
        asn,

        ooni_tests,
        blocked_tests,
        block_rate,

        conflict_events,
        takedown_requests

    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events`
),

quality AS (

    SELECT
        weight AS quality_weight
    FROM `encoded-joy-485413-k5.marts.dim_measurement_quality`
    WHERE quality_level = 'MEDIUM'
    LIMIT 1

),

base AS (

    SELECT
        s.*,
        q.quality_weight
    FROM spine s
    CROSS JOIN quality q

),

aggregated AS (

    SELECT
        measurement_date,
        asn,

        SAFE_DIVIDE(blocked_tests, NULLIF(ooni_tests, 0)) * quality_weight AS q_block_rate,

        conflict_events,
        takedown_requests,

        ooni_tests

    FROM base
)

SELECT
    measurement_date,
    asn,

    q_block_rate,

    conflict_events,
    takedown_requests,
    ooni_tests,

    -- normalized components
    LEAST(q_block_rate, 1.0) AS block_norm,
    LEAST(conflict_events / 10.0, 1.0) AS conflict_norm,
    LEAST(takedown_requests / 100.0, 1.0) AS takedown_norm,

    -- final index
    (
        0.60 * LEAST(q_block_rate, 1.0) +
        0.25 * LEAST(conflict_events / 10.0, 1.0) +
        0.15 * LEAST(takedown_requests / 100.0, 1.0)
    ) AS asn_repression_index_v3

FROM aggregated;