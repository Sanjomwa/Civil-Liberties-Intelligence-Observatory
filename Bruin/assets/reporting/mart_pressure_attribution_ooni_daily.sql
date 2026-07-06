/* @bruin
tags:
  - reporting
  - dataset_ooni

name: reporting.mart_pressure_attribution_ooni_daily
type: bq.sql
connection: bigquery-default

description: |
  Pressure-attribution decomposition, OONI corroboration layer (ADR-0006;
  fulfills Project Zero Review Recommendation #4).

  GRAIN: one row per measurement_date x test_name x protocol -- the daily
  per-app, per-protocol-layer view of what OONI probes directly observed.

  THIS IS CORROBORATING EVIDENCE, NOT A COMPOSITE INPUT -- stated here
  because it is the single easiest thing to misread about CLIO's headline
  number: OONI measurement does NOT feed composite_pressure_score
  arithmetically (verified directly against
  marts.fact_country_pressure_daily for ADR-0006; the composite's
  "platform" term is Google Transparency data, not OONI). What OONI
  provides for an attributed finding is independent, same-day,
  network-layer measurement: whether the apps and protocols civil
  society relies on were measurably interfered with on the date in
  question. It corroborates (or fails to corroborate) a conflict-driven
  reading; it never moves the score.

  test_name is kept as a grouping key deliberately -- do NOT pool
  test families into one share. dnscheck's recovered volume (TD-47) is
  structurally zero-signal today (TD-55) and pooling it into a shared
  denominator dilutes real app-blocking shares (TD-54's measured
  finding, now TD-49's standing requirement). Per-test_name rows keep
  every rate honest: a dnscheck row's rate is dnscheck's own, never
  blended into WhatsApp's.

  Confidence labels come from marts.dim_censorship_confidence via the
  same min_score threshold join canonicalized by ADR-0001 (identical
  pattern to marts.fact_protocol_blocking_summary, which is this asset's
  monthly counterpart -- kept structurally parallel on purpose).

owner: civil-liberties-pipeline

depends:
  - marts.fact_ooni_censorship_signals
  - marts.dim_censorship_confidence

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_date
    type: date
    description: Measurement date (daily grain).
    checks:
      - name: not_null

  - name: test_name
    type: string
    description: |
      OONI test identity (whatsapp, telegram, signal, psiphon, dnscheck).
      Deliberately never pooled across tests (TD-49/TD-54).
    checks:
      - name: not_null

  - name: protocol
    type: string
    description: Protocol layer (dns/tcp/tls/http).
    checks:
      - name: not_null
@bruin */

WITH base AS (

    SELECT
        s.measurement_date,
        s.country,
        s.test_name,
        s.protocol,
        s.result_state,
        s.is_blocking_signal,
        s.blocking_detail,
        s.probe_asn,
        s.measurement_id,
        s.experiment_result_id,

        COALESCE(c.confidence_level, 'NONE') AS confidence_level

    FROM `{{ var.project_id }}.marts.fact_ooni_censorship_signals` AS s
    LEFT JOIN `{{ var.project_id }}.marts.dim_censorship_confidence` AS c
        ON c.min_score IS NOT NULL AND s.confidence_score >= c.min_score
    -- fact_ooni_censorship_signals.country holds ISO2 codes (verified
    -- live: 'KE' on all rows today).
    WHERE s.country = '{{ var.iso2 }}'
    QUALIFY ROW_NUMBER() OVER (
        PARTITION BY s.experiment_result_id
        ORDER BY c.ordinal_rank DESC
    ) = 1

)

SELECT
    measurement_date,
    country,
    test_name,
    protocol,

    COUNT(*) AS total_experiment_results,
    COUNTIF(is_blocking_signal) AS blocking_signal_count,

    COUNTIF(result_state = 'BLOCKED') AS blocked_results,
    COUNTIF(result_state = 'OK') AS ok_results,
    COUNTIF(result_state = 'DOWN') AS down_results,
    COUNTIF(result_state = 'ERROR') AS error_results,

    COUNT(DISTINCT probe_asn) AS distinct_asns,
    COUNT(DISTINCT measurement_id) AS distinct_measurements,

    COUNTIF(confidence_level = 'HIGH') AS high_confidence_events,
    COUNTIF(confidence_level = 'MEDIUM') AS medium_confidence_events,
    COUNTIF(confidence_level IN ('LOW', 'NONE')) AS low_confidence_events,

    -- Per-test_name rate only: this row's own test's rate, never a
    -- pooled cross-test share (TD-49/TD-54).
    SAFE_DIVIDE(COUNTIF(is_blocking_signal), COUNT(*))
        AS blocking_signal_rate,

    'PRESSURE_ATTRIBUTION_V1' AS attribution_methodology_version,
    'pressure_attribution_ooni_daily_v1' AS reporting_version,
    CURRENT_TIMESTAMP() AS snapshot_at

FROM base
GROUP BY
    measurement_date,
    country,
    test_name,
    protocol
ORDER BY measurement_date, test_name, protocol
