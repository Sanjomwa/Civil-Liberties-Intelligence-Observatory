/* @bruin
name: fact_asn_repression_index
type: bq.sql
connection: bigquery-default
depends:
  - int.ooni_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT *
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.int_ooni_signals`
),

aggregated AS (

    SELECT

        DATE(start_time) AS event_date,
        country,
        asn,

        COUNT(*) AS total_measurements,

        SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END) AS blocked_measurements,

        -- platform breakdown
        SUM(CASE WHEN signal_type = 'telegram' AND is_blocked THEN 1 ELSE 0 END) AS telegram_blocks,
        SUM(CASE WHEN signal_type = 'whatsapp' AND is_blocked THEN 1 ELSE 0 END) AS whatsapp_blocks,
        SUM(CASE WHEN signal_type = 'tor' AND is_blocked THEN 1 ELSE 0 END) AS tor_blocks,
        SUM(CASE WHEN signal_type = 'signal' AND is_blocked THEN 1 ELSE 0 END) AS signal_blocks,
        SUM(CASE WHEN signal_type = 'psiphon' AND is_blocked THEN 1 ELSE 0 END) AS psiphon_blocks,

        AVG(
            CASE block_confidence
                WHEN 'HIGH' THEN 1.0
                WHEN 'MEDIUM' THEN 0.6
                WHEN 'LOW' THEN 0.3
                ELSE 0.0
            END
        ) AS avg_confidence_score,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
    GROUP BY event_date, country, asn
),

enriched AS (

    SELECT
        *,
        
        SAFE_DIVIDE(blocked_measurements, total_measurements) AS block_rate,

        -- number of platforms affected
        (
            CASE WHEN telegram_blocks > 0 THEN 1 ELSE 0 END +
            CASE WHEN whatsapp_blocks > 0 THEN 1 ELSE 0 END +
            CASE WHEN tor_blocks > 0 THEN 1 ELSE 0 END +
            CASE WHEN signal_blocks > 0 THEN 1 ELSE 0 END +
            CASE WHEN psiphon_blocks > 0 THEN 1 ELSE 0 END
        ) AS affected_platform_count

    FROM aggregated
),

final AS (

    SELECT
        *,
        
        -- =========================
        -- REPRESSION INDEX (0–100)
        -- =========================
        LEAST(
            100,

            (
                (block_rate * 0.5) +
                (affected_platform_count / 5.0 * 0.3) +
                (avg_confidence_score * 0.2)
            ) * 100
        ) AS repression_index

    FROM enriched
)

SELECT *
FROM final;
