/* @bruin
tags:
  - marts_bq
name: fact_asn_repression_index
type: bq.sql
connection: bigquery-default
description: |
  ASN-level repression index for Kenya.
  Measures ISP involvement in censorship using cross-source spine signals
  (OONI + ACLED + takedown systems).

  Higher score = stronger association with digital repression environments.

owner: civil-liberties-pipeline

depends:
  - marts.fact_cross_source_censorship_events
  - marts.dim_asn
  - marts.dim_censorship_confidence
  - marts.dim_measurement_quality

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (

    SELECT *
    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events`

),

asn_agg AS (

    SELECT

        asn,

        COUNT(*) AS total_measurements,

        -- =========================
        -- BLOCKING INTENSITY
        -- =========================
        COUNTIF(is_blocked = TRUE) AS blocked_measurements,

        SAFE_DIVIDE(
            COUNTIF(is_blocked = TRUE),
            COUNT(*)
        ) AS blocking_rate,

        AVG(
            CASE
                WHEN blocking_confidence = 'HIGH' THEN 3
                WHEN blocking_confidence = 'MEDIUM' THEN 2
                WHEN blocking_confidence = 'LOW' THEN 1
                ELSE 0
            END
        ) AS avg_blocking_confidence_score,

        -- =========================
        -- PROTEST COUPLING
        -- =========================
        COUNTIF(conflict_events > 0) AS conflict_overlap_events,

        SAFE_DIVIDE(
            COUNTIF(is_blocked = TRUE AND conflict_events > 0),
            NULLIF(COUNTIF(is_blocked = TRUE), 0)
        ) AS protest_block_coupling_rate,

        -- =========================
        -- TAKEDOWN COUPLING
        -- =========================
        SUM(takedown_count) AS total_takedowns,

        SAFE_DIVIDE(
            SUM(takedown_count),
            COUNT(*)
        ) AS takedown_density,

        -- =========================
        -- CROSS-SOURCE SUPPRESSION
        -- =========================
        COUNTIF(event_classification IN (
            'FULL_SUPPRESSION_WINDOW',
            'NETWORK + CIVIL_UNREST',
            'NETWORK + PLATFORM_SUPPRESSION'
        )) AS high_intensity_windows,

        SAFE_DIVIDE(
            COUNTIF(event_classification IN (
                'FULL_SUPPRESSION_WINDOW',
                'NETWORK + CIVIL_UNREST',
                'NETWORK + PLATFORM_SUPPRESSION'
            )),
            COUNT(*)
        ) AS suppression_window_rate

    FROM base
    GROUP BY asn

),

final AS (

    SELECT

        a.asn,

        d.asn_name,
        d.asn_org,
        d.country,

        a.total_measurements,
        a.blocked_measurements,
        a.blocking_rate,
        a.avg_blocking_confidence_score,

        a.conflict_overlap_events,
        a.protest_block_coupling_rate,

        a.total_takedowns,
        a.takedown_density,

        a.high_intensity_windows,
        a.suppression_window_rate,

        -- =========================
        -- FINAL REPRESSION INDEX
        -- =========================
        (
            COALESCE(a.blocking_rate * 0.35, 0)
            + COALESCE(a.protest_block_coupling_rate * 0.25, 0)
            + LEAST(a.takedown_density * 0.2, 0.2)
            + COALESCE(a.suppression_window_rate * 0.2, 0)
        ) AS repression_index_score,

        CASE
            WHEN (
                a.blocking_rate > 0.3
                AND a.protest_block_coupling_rate > 0.2
            ) THEN 'HIGH RISK ISP'

            WHEN (
                a.blocking_rate > 0.15
                OR a.suppression_window_rate > 0.15
            ) THEN 'MEDIUM RISK ISP'

            WHEN a.total_measurements < 50 THEN 'LOW DATA COVERAGE'

            ELSE 'LOW RISK ISP'
        END AS repression_category,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM asn_agg a

    LEFT JOIN `encoded-joy-485413-k5.marts.dim_asn` d
        ON a.asn = d.asn

)

SELECT *
FROM final
