/* @bruin
tags:
  - marts_bq
name: marts.fact_censorship_impact
type: bq.sql
connection: bigquery-default
description: |
  OONI measurements enriched with same-day ACLED conflict context.
  This is the observatory core — answers "did censorship spike on protest days?"

  Uses test-specific normalized blocking fields. The headline metric
  blocked_on_protest_day now uses is_blocked (test-aware) not the old
  generic status flag.

  blocking_confidence distinguishes confirmed blocks from probable/disruption.

owner: civil-liberties-pipeline
depends:
  - marts.fact_censorship_measurements
  - marts.fact_conflict_events
materialization:
  type: table
  strategy: create+replace
@bruin */

WITH daily_conflict_summary AS (
    SELECT
        measurement_date,
        COUNT(*)                                        AS conflict_event_count,
        SUM(event_count)                                AS total_events,
        SUM(fatalities)                                 AS total_fatalities,
        SUM(population_exposure)                        AS total_population_exposure,
        COUNTIF(is_censorship_trigger_event)            AS trigger_event_count,
        STRING_AGG(DISTINCT event_type, ', ')           AS event_types_on_day,
        STRING_AGG(
            DISTINCT county, ', '
            ORDER BY county
            LIMIT 5
        )                                               AS counties_affected
    FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_conflict_events`
    GROUP BY measurement_date
)

SELECT
    -- ── Measurement identity ───────────────────────────────────────────────
    c.measurement_id,
    c.measurement_date,
    c.test_name,
    c.test_category,
    c.is_blocked,
    c.is_confirmed_block,
    c.has_measurement_failure,
    c.blocking_confidence,
    c.blocking_signal_type,
    c.tested_url_or_app,
    c.asn,
    c.probe_asn,
    c.year,
    c.month,
    c.extracted_at,

    -- ── Test-specific flags (carried through for forensic drill-down) ──────
    c.telegram_http_blocking,
    c.telegram_tcp_blocking,
    c.whatsapp_endpoints_blocked,
    c.whatsapp_endpoints_dns_inconsistent,
    c.signal_backend_failure,
    c.tor_or_port_accessible,
    c.psiphon_failure,

    -- ── Same-day conflict context ──────────────────────────────────────────
    d.conflict_event_count,
    d.total_events                                      AS conflict_events_on_day,
    d.total_fatalities                                  AS fatalities_on_day,
    d.trigger_event_count                               AS protest_events_on_day,
    d.event_types_on_day,
    d.counties_affected,
    d.total_population_exposure,

    -- ── Observatory headline metric ────────────────────────────────────────
    CASE
        WHEN c.is_blocked AND d.trigger_event_count > 0 THEN TRUE
        ELSE FALSE
    END                                                 AS blocked_on_protest_day,

    -- ── Suppression confidence tier ────────────────────────────────────────
    -- Distinguishes confirmed blocks on protest days from probable/disruption
    CASE
        WHEN c.is_confirmed_block
             AND COALESCE(d.trigger_event_count, 0) > 0 THEN 'Confirmed Block on Protest Day'
        WHEN c.is_blocked
             AND COALESCE(d.trigger_event_count, 0) > 0 THEN 'Probable Block on Protest Day'
        WHEN c.has_measurement_failure
             AND COALESCE(d.trigger_event_count, 0) > 0 THEN 'Disruption on Protest Day'
        WHEN c.is_confirmed_block                       THEN 'Confirmed Block (non-protest)'
        WHEN c.is_blocked                               THEN 'Probable Block (non-protest)'
        ELSE 'No Suppression Signal'
    END                                                 AS suppression_confidence_type

FROM `encoded-joy-485413-k5.{{ var.bq_dataset }}.fact_censorship_measurements` c
LEFT JOIN daily_conflict_summary d
    ON c.measurement_date = d.measurement_date
