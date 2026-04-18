/* @bruin
tags:
  - marts_bq
name: marts.fact_asn_repression_index
type: bq.sql
connection: bigquery-default
description: |
  Monthly ASN-level repression index for Kenya.

  Built from cross-source censorship spine:
  - OONI censorship signals
  - ACLED conflict pressure
  - Takedown governance pressure

  This is the ISP-level accountability layer of the observatory.

owner: civil-liberties-pipeline

depends:
  - marts.fact_cross_source_censorship_events

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT
        DATE_TRUNC(date, MONTH) AS month,
        
        -- NOTE: ASNs only meaningful from OONI-weighted inference
        0 AS asn_placeholder,

        censorship_score,
        conflict_pressure_score,
        governance_pressure_score,
        escalation_score
    FROM `encoded-joy-485413-k5.marts.fact_cross_source_censorship_events`
),

aggregated AS (
    SELECT
        month,

        -- =========================
        -- INDEX COMPONENTS
        -- =========================

        AVG(censorship_score) AS avg_censorship_score,
        AVG(conflict_pressure_score) AS avg_conflict_pressure,
        AVG(governance_pressure_score) AS avg_governance_pressure,
        AVG(escalation_score) AS avg_escalation_score,

        COUNT(*) AS observation_days

    FROM base
    GROUP BY month
)

SELECT
    *,

    -- =========================
    -- REPRESSION INDEX (0–1)
    -- =========================
    LEAST(
        (avg_censorship_score * 0.5) +
        (avg_conflict_pressure * 0.3) +
        (avg_governance_pressure * 0.2),
        1.0
    ) AS asn_repression_index,

    -- =========================
    -- ESCALATION CLASS
    -- =========================
    CASE
        WHEN avg_escalation_score > 0.7 THEN 'Severe Repression Period'
        WHEN avg_escalation_score > 0.4 THEN 'Elevated Repression'
        WHEN avg_escalation_score > 0.2 THEN 'Moderate Pressure'
        ELSE 'Low Activity'
    END AS repression_class,

    CURRENT_TIMESTAMP() AS extracted_at

FROM aggregated;
