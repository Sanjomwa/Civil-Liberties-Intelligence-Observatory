name: reporting.civil_liberties_mart
type: sql
materialization: table

description: >
  Country × ASN civil liberties analytical spine combining OONI censorship,
  ACLED conflict, and platform/Google takedown pressure signals.

dependencies:
  - marts.fact_ooni_censorship_signals
  - marts.fact_network_blocking_daily
  - marts.fact_conflict_events
  - marts.fact_country_pressure_daily

query: |
  CREATE OR REPLACE TABLE reporting.civil_liberties_mart AS
  WITH

  ooni AS (
    SELECT
      DATE(measurement_id) AS measurement_date,
      LOWER(country) AS country,
      asn,
      COUNT(1) AS ooni_tests,
      SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END) AS blocked_tests,
      SAFE_DIVIDE(
        SUM(CASE WHEN is_blocked THEN 1 ELSE 0 END),
        COUNT(1)
      ) AS block_rate,
      SUM(blocking_confidence) AS network_block_signals
    FROM marts.fact_ooni_censorship_signals
    GROUP BY 1,2,3
  ),

  network AS (
    SELECT
      DATE(measurement_date) AS measurement_date,
      asn,
      SUM(ooni_tests) AS net_tests,
      SUM(blocked_tests) AS net_blocked,
      AVG(block_rate) AS net_block_rate
    FROM marts.fact_network_blocking_daily
    GROUP BY 1,2
  ),

  conflict AS (
    SELECT
      DATE(event_date) AS measurement_date,
      LOWER(country) AS country,
      SUM(event_count) AS conflict_events,
      SUM(fatalities) AS fatalities
    FROM marts.fact_conflict_events
    GROUP BY 1,2
  ),

  country_pressure AS (
    SELECT
      DATE(measurement_date) AS measurement_date,
      LOWER(country) AS country,
      SUM(takedown_requests) AS takedown_requests,
      SUM(takedown_items) AS items_removed,
      SUM(google_requests) AS google_requests
    FROM marts.fact_country_pressure_daily
    GROUP BY 1,2
  ),

  spine AS (
    SELECT
      o.measurement_date,
      o.country,
      o.asn,
      o.ooni_tests,
      o.blocked_tests,
      o.block_rate,
      o.network_block_signals,
      n.net_tests,
      n.net_blocked,
      n.net_block_rate
    FROM ooni o
    LEFT JOIN network n
      ON o.measurement_date = n.measurement_date
     AND o.asn = n.asn
  ),

  enriched AS (
    SELECT
      s.*,
      c.conflict_events,
      c.fatalities,
      cp.takedown_requests,
      cp.items_removed,
      cp.google_requests
    FROM spine s
    LEFT JOIN conflict c
      ON s.measurement_date = c.measurement_date
     AND s.country = c.country
    LEFT JOIN country_pressure cp
      ON s.measurement_date = cp.measurement_date
     AND s.country = cp.country
  ),

  norm AS (
    SELECT
      *,
      MAX(conflict_events) OVER () AS max_conflict,
      MAX(takedown_requests) OVER () AS max_takedowns
    FROM enriched
  )

  SELECT
    measurement_date,
    country,
    asn,

    ooni_tests,
    blocked_tests,
    block_rate,
    network_block_signals,

    conflict_events,
    fatalities,

    takedown_requests,
    items_removed,
    google_requests,

    CASE WHEN block_rate > 0 THEN TRUE ELSE FALSE END AS has_blocking,
    CASE WHEN conflict_events > 0 THEN TRUE ELSE FALSE END AS has_conflict,

    CASE
      WHEN block_rate > 0 AND conflict_events > 0 THEN TRUE
      ELSE FALSE
    END AS conflict_block_overlap,

    SAFE_DIVIDE(conflict_events, NULLIF(max_conflict, 0)) AS conflict_events_normalized,
    SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0)) AS takedown_pressure_normalized,

    (
      0.5 * block_rate +
      0.3 * SAFE_DIVIDE(conflict_events, NULLIF(max_conflict, 0)) +
      0.2 * SAFE_DIVIDE(takedown_requests, NULLIF(max_takedowns, 0))
    ) AS civil_liberties_pressure_index

  FROM norm;
