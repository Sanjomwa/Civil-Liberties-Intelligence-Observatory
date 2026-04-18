/* @bruin
name: fact_ooni_censorship_signals
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

daily AS (

    SELECT

        DATE(start_time) AS event_date,
        country,
        asn,
        probe_asn,

        signal_type,
        blocking_signal_type,

        -- =========================
        -- CORE COUNTS
        -- =========================
        COUNT(*) AS total_measurements,

        SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END) AS blocked_measurements,

        SUM(CASE WHEN has_measurement_failure THEN 1 ELSE 0 END) AS failed_measurements,

        -- =========================
        -- SIGNAL STRENGTH
        -- =========================
        AVG(
            CASE block_confidence
                WHEN 'HIGH' THEN 1.0
                WHEN 'MEDIUM' THEN 0.6
                WHEN 'LOW' THEN 0.3
                ELSE 0.0
            END
        ) AS avg_confidence_score,

        -- =========================
        -- PLATFORM-SPECIFIC FLAGS
        -- =========================
        SUM(CASE WHEN signal_type = 'telegram' AND is_blocked THEN 1 ELSE 0 END) AS telegram_blocks,
        SUM(CASE WHEN signal_type = 'whatsapp' AND is_blocked THEN 1 ELSE 0 END) AS whatsapp_blocks,
        SUM(CASE WHEN signal_type = 'tor' AND is_blocked THEN 1 ELSE 0 END) AS tor_blocks,
        SUM(CASE WHEN signal_type = 'signal' AND is_blocked THEN 1 ELSE 0 END) AS signal_blocks,
        SUM(CASE WHEN signal_type = 'psiphon' AND is_blocked THEN 1 ELSE 0 END) AS psiphon_blocks,

        CURRENT_TIMESTAMP() AS extracted_at

    FROM base

    GROUP BY
        event_date,
        country,
        asn,
        probe_asn,
        signal_type,
        blocking_signal_type
)

SELECT
    *,
    
    -- =========================
    -- DERIVED KPIS
    -- =========================
    SAFE_DIVIDE(blocked_measurements, total_measurements) AS block_rate,
    SAFE_DIVIDE(failed_measurements, total_measurements) AS failure_rate

FROM daily;
