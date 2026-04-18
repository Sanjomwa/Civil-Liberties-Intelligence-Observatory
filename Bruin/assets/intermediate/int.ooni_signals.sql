/* @bruin
name: int.ooni_signals
type: bq.sql
connection: bigquery-default
depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT *
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.stg_ooni_measurements`
)

SELECT

    measurement_id,
    country,
    asn,
    probe_asn,
    test_name,
    input,
    start_time,
    extracted_at,

    -- =========================
    -- SIGNAL NORMALIZATION (ONLY HERE)
    -- =========================

    CASE
        WHEN is_confirmed_block THEN 'confirmed_block'
        WHEN is_blocked THEN 'suspected_block'
        WHEN has_measurement_failure THEN 'network_failure'
        ELSE 'no_evidence'
    END AS blocking_signal_type,

    CASE
        WHEN is_confirmed_block THEN 'HIGH'
        WHEN is_blocked THEN 'MEDIUM'
        WHEN has_measurement_failure THEN 'LOW'
        ELSE 'NONE'
    END AS confidence_level,

    CASE
        WHEN is_blocked OR is_confirmed_block THEN TRUE
        ELSE FALSE
    END AS is_blocked_event,

    -- =========================
    -- SERVICE GROUPING (keep minimal)
    -- =========================

    CASE
        WHEN test_name LIKE '%telegram%' THEN 'telegram'
        WHEN test_name LIKE '%whatsapp%' THEN 'whatsapp'
        WHEN test_name LIKE '%signal%' THEN 'signal'
        WHEN test_name LIKE '%tor%' THEN 'tor'
        WHEN test_name LIKE '%psiphon%' THEN 'psiphon'
        ELSE 'other'
    END AS service_type,

    -- =========================
    -- DERIVED QUALITY SIGNAL
    -- =========================

    (
        CASE WHEN input IS NULL THEN 0 ELSE 0.3 END +
        CASE WHEN test_name IS NULL THEN 0 ELSE 0.3 END +
        CASE WHEN asn IS NULL THEN 0 ELSE 0.4 END
    ) AS measurement_quality_score

FROM base;
