/* @bruin
tags:
  - marts_bq
name: marts.fact_ooni_censorship_signals
type: bq.sql
connection: bigquery-default
description: |
  Canonical OONI fact table for censorship analysis in Kenya.

  Built from int.ooni_signals (fully normalized layer).
  This table is the ONLY OONI input for downstream marts:
  - cross-source spine
  - platform blocking summary
  - ASN repression index

owner: civil-liberties-pipeline

depends:
  - int.ooni_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
    -- =========================
    -- CORE IDENTIFIERS
    -- =========================
    measurement_id,
    country,
    asn,
    probe_asn,
    test_name,
    input,

    start_time,
    measurement_date,

    year,
    month,
    day,

    extracted_at,

    -- =========================
    -- NORMALIZED SIGNALS (FROM INT LAYER)
    -- =========================
    signal_type,
    blocking_signal_type,

    is_blocked,
    is_confirmed_block,

    block_confidence,
    measurement_quality_score,

    -- =========================
    -- TEST CATEGORY
    -- =========================
    CASE
        WHEN test_name IN ('telegram', 'whatsapp', 'signal') THEN 'messaging'
        WHEN test_name IN ('tor', 'psiphon') THEN 'circumvention'
        ELSE 'web'
    END AS test_category,

    -- =========================
    -- SIMPLE ANALYTICAL FLAGS (NO LOGIC CHANGE)
    -- =========================
    CASE
        WHEN is_confirmed_block THEN 'confirmed'
        WHEN is_blocked THEN 'suspected'
        ELSE 'clean'
    END AS censorship_status

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.int.ooni_signals`;