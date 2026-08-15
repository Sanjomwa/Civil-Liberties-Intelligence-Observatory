/* @bruin
name: int.ooni_measurement_verdicts
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  TD-87 Phase 2 (2026-08-15). OONI's own real, per-measurement verdict
  vocabulary (OK / CONFIRMED / ANOMALOUS / FAILED), derived from each
  test's own probe-submitted summary field (stg.ooni_measurement_summary,
  Phase 1) -- NOT the same thing as result_state, which stays untouched,
  per-observation, and unconsumed by this asset.

  Grain: one row per measurement_id (OONI's own real grain), deliberately
  different from result_state's per-observation grain in
  int.ooni_experiment_results.sql. This asset has NO CONSUMER YET -- it
  does not feed any existing mart or Streamlit page. Nothing existing
  changes value because of this asset.

  fingerprint_match_id is always NULL this phase (real fingerprint
  matching against ooni/blocking-fingerprints is Phase 5, out of scope
  here) -- the column exists now purely for forward compatibility, and
  because CONFIRMED's three-layer guard (see
  int.ooni_measurement_verdicts_confirmed_guard.sql) needs somewhere
  structurally safe to be built ahead of that real logic landing.

  STRUCTURAL GUARD (layer 1 of 3, see the confirmed_guard asset for layers
  2-3): fingerprint_match_id is populated ONLY inside wc_confirmed below,
  a CTE whose SOURCE is filtered to test_name = 'web_connectivity' --
  never by a bare `CASE WHEN test_name = 'web_connectivity'` predicate
  mixed into a shared, unfiltered CTE. OONI's CONFIRMED state is
  structurally possible only for web_connectivity (fingerprint-matched
  block pages / censorship-associated DNS answers) -- never for Signal,
  WhatsApp, Telegram, Tor, or any other test. Get this right now so
  Phase 5 has one safe, pre-isolated place to add real fingerprint-match
  logic later, rather than requiring a future author to remember to add
  the test_name filter themselves.

  probe_accuracy_gate grounds a real, earlier-measured finding (an audit
  found 80/361 BLOCKED TLS rows and 99/100 residual ssl_* UNKNOWN rows
  carry OONI's own scores.accuracy = 0.0) via
  marts.dim_ooni_probe_version_accuracy -- see that asset's header for the
  sourced discard rule (Signal-specific, ooni/probe#2344) and three
  corrections made to this phase's original design before encoding it
  (compound version+date condition, cross-test test_version collisions,
  no engine_version field). probe_accuracy_gate is reported here but
  deliberately NOT wired into ooni_verdict's own CASE this phase -- that
  is a decision for whichever later phase actually uses this gate (e.g.
  to exclude DISCARDED_BAD_PROBE_VERSION rows from a confidence-weighted
  aggregate), not assumed here.

depends:
  - stg.ooni_measurement_summary
  - marts.dim_ooni_probe_version_accuracy

materialization:
  type: table
  strategy: create+replace

columns:
  - name: measurement_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: ooni_verdict
    type: string
    checks:
      - name: accepted_values
        value: [OK, CONFIRMED, ANOMALOUS, FAILED]
@bruin */

WITH summary AS (
  SELECT *
  FROM `{{ var.project_id }}.stg.ooni_measurement_summary`
),

-- STRUCTURAL GUARD, layer 1: fingerprint_match_id exists ONLY here, and
-- this CTE's own source is filtered to web_connectivity -- see header.
-- Always NULL this phase (Phase 5 builds the real ooni/blocking-
-- fingerprints match here, inside this same filtered CTE, never outside
-- it).
wc_confirmed AS (
  SELECT
    measurement_id,
    CAST(NULL AS STRING) AS fingerprint_match_id
  FROM summary
  WHERE test_name = 'web_connectivity'
),

verdicts AS (
  SELECT
    s.measurement_id,
    s.test_name,
    s.probe_asn,
    s.probe_network_name,
    s.country,
    s.measurement_date,
    s.measurement_start_time,
    s.measurement_failure,

    wc.fingerprint_match_id,

    CASE
      WHEN s.test_name = 'web_connectivity' THEN s.wc_control_failure
      ELSE NULL
    END AS control_failure,

    CASE
      WHEN s.test_name = 'web_connectivity'
        AND s.wc_blocking IS NOT NULL
        AND s.wc_blocking != 'false'
        THEN s.wc_blocking
      ELSE NULL
    END AS web_blocking_type,

    -- test_anomaly_flag: derived per test_name from Phase 1's real,
    -- live-verified field vocabulary (see stg.ooni_measurement_summary's
    -- header for what changed from the original hypothesis). Each arm
    -- defaults to NULL (not FALSE) when its test's own fields are
    -- unexpectedly all-NULL -- defensive; never observed live today
    -- (every real row of every implemented test type has its fields
    -- populated, confirmed in Phase 1's verification), but matches this
    -- project's default-safe-not-default-clean discipline.
    CASE s.test_name
      WHEN 'web_connectivity' THEN CASE
        WHEN s.wc_blocking IS NULL THEN NULL
        WHEN s.wc_blocking = 'false' THEN FALSE
        ELSE TRUE
      END
      WHEN 'signal' THEN CASE
        WHEN s.signal_backend_status = 'blocked' THEN TRUE
        WHEN s.signal_backend_status = 'ok' THEN FALSE
        ELSE NULL
      END
      WHEN 'whatsapp' THEN CASE
        WHEN s.whatsapp_endpoints_status IS NULL
          AND s.whatsapp_web_status IS NULL
          AND s.registration_server_status IS NULL THEN NULL
        WHEN s.whatsapp_endpoints_status = 'blocked'
          OR s.whatsapp_web_status = 'blocked'
          OR s.registration_server_status = 'blocked'
          OR s.whatsapp_endpoints_blocked_count > 0
          OR s.whatsapp_endpoints_dns_inconsistent_count > 0 THEN TRUE
        ELSE FALSE
      END
      WHEN 'telegram' THEN CASE
        WHEN s.telegram_tcp_blocking IS NULL
          AND s.telegram_http_blocking IS NULL
          AND s.telegram_web_status IS NULL THEN NULL
        WHEN s.telegram_tcp_blocking IS TRUE
          OR s.telegram_http_blocking IS TRUE
          OR s.telegram_web_status = 'blocked' THEN TRUE
        ELSE FALSE
      END
      WHEN 'facebook_messenger' THEN CASE
        WHEN s.facebook_dns_blocking IS NULL
          AND s.facebook_tcp_blocking IS NULL THEN NULL
        WHEN s.facebook_dns_blocking IS TRUE
          OR s.facebook_tcp_blocking IS TRUE THEN TRUE
        ELSE FALSE
      END
      WHEN 'psiphon' THEN CASE
        WHEN s.psiphon_failure IS NOT NULL THEN TRUE
        ELSE FALSE
      END
      WHEN 'dnscheck' THEN CASE
        WHEN s.dnscheck_bootstrap_failure IS NOT NULL THEN TRUE
        ELSE FALSE
      END
      -- tor (not implemented this phase) and any future/unrecognized
      -- test_name both fall through to NULL here.
      ELSE NULL
    END AS test_anomaly_flag,

    CASE s.test_name
      WHEN 'web_connectivity' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'signal' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'whatsapp' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'telegram' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'facebook_messenger' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'psiphon' THEN 'PROBE_SUMMARY_FIELD'
      WHEN 'dnscheck' THEN 'PARTIAL_BOOTSTRAP_ONLY'
      ELSE 'NOT_IMPLEMENTED'
    END AS ooni_verdict_source,

    CASE
      WHEN dim.is_known_bad_version IS TRUE THEN 'DISCARDED_BAD_PROBE_VERSION'
      WHEN dim.is_known_bad_version IS FALSE THEN 'SCORED'
      ELSE 'UNKNOWN_VERSION'
    END AS probe_accuracy_gate

  FROM summary AS s
  LEFT JOIN wc_confirmed AS wc
    ON wc.measurement_id = s.measurement_id
  -- Compound key: test_version values collide across test_name families
  -- (e.g. '0.2.0' exists for both signal and telegram, independently
  -- versioned) -- see dim_ooni_probe_version_accuracy's header for how
  -- this was caught before shipping a bare test_version join.
  LEFT JOIN `{{ var.project_id }}.marts.dim_ooni_probe_version_accuracy` AS dim
    ON dim.test_name = s.test_name
    AND dim.test_version = s.test_version
)

SELECT
  *,
  CASE
    WHEN fingerprint_match_id IS NOT NULL THEN 'CONFIRMED'
    WHEN measurement_failure IS NOT NULL OR control_failure IS NOT NULL THEN 'FAILED'
    WHEN test_anomaly_flag IS TRUE THEN 'ANOMALOUS'
    WHEN test_anomaly_flag IS NULL THEN NULL
    ELSE 'OK'
  END AS ooni_verdict,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM verdicts;
