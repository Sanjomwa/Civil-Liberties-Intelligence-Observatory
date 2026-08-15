/* @bruin
name: stg.ooni_measurement_summary
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - ooni_verdict_phase_1

description: |
  TD-87 Phase 1 (2026-08-15). Surfaces each OONI test's own summary verdict
  fields (the field the probe itself computes and submits) as typed
  nullable columns. Grain: one row per measurement_id, 1:1 with
  stg.ooni_measurements (this is a wide SELECT, not a filter -- every
  measurement gets a row here regardless of test_name).

  This is strictly additive and has NO CONSUMER YET as of this commit --
  int.ooni_experiment_results.sql, result_state, and every existing
  downstream mart/Streamlit page are untouched. See
  int.ooni_measurement_verdicts.sql (Phase 2) for the first consumer.

  Field vocabulary verified live against Kenya's actual corpus before
  writing this SQL (TD-87 Phase 1/2 relay session, 2026-08-15), not
  assumed -- see reports.md for the full sampling methodology. Real
  findings that changed this asset from the original design hypothesis:

  - Only 6 test_name values exist in CLIO's entire ingested corpus:
    dnscheck, whatsapp, telegram, psiphon, signal, tor. web_connectivity
    and facebook_messenger have ZERO rows -- confirmed absent from both
    this staging layer and the raw landing table
    (civil_liberties_staging.ooni_measurements), not a filtering
    artifact. Their columns below (wc_*, facebook_*) are built for
    structural/forward-compatibility reasons (the CONFIRMED verdict
    concept in Phase 2 is deliberately web_connectivity-only) and are
    verified against OONI's own published spec
    (ooni/spec ts-017-web-connectivity.md, ts-019-facebook-messenger.md,
    fetched live) rather than CLIO's own data, since none exists yet.
  - signal_backend_status / whatsapp_*_status / telegram_web_status take
    exactly two live values, 'ok' or 'blocked' -- no third value, no NULL,
    confirmed by full GROUP BY across each test's entire corpus.
  - whatsapp_endpoints_blocked / whatsapp_endpoints_dns_inconsistent are
    ARRAYS of endpoint hostnames (e.g. ["e11.whatsapp.net", ...]), not
    booleans as originally hypothesized -- extracted here as integer
    array-length counts (dns_inconsistent is always empty, 0/51,394 rows,
    in live Kenya data; blocked ranges 0-16).
  - telegram_tcp_blocking / telegram_http_blocking ARE real booleans
    ("true"/"false" JSON literals), matching the original hypothesis.
  - psiphon has no test-specific failure field distinct from the generic
    test_keys.failure path -- extracted as psiphon_failure, confirmed
    NOT redundant with the top-level `failure` column (see below).
  - dnscheck: the real signal is the top-level convenience field
    $.bootstrap_failure, NOT the nested $.bootstrap.failure (that nested
    path is 100% NULL in live data despite bootstrap_failure itself being
    populated for ~9.4K/1.1M rows) -- a genuine divergence from a naive
    reading of the JSON shape, caught by checking both paths live.
  - The stg.ooni_measurements.failure column (measurement_failure below)
    is confirmed 100% NULL across all 1,354,848 live rows, all 6 test
    types -- genuinely dead, exactly as flagged before this session.
    ooni_raw.py's `obj.get("failure")` never finds a value in the raw
    JSON OONI actually ships for any test type in this corpus.
  - engine_version does not exist as a field anywhere in the raw JSON
    (checked, always NULL) -- only test_version (already typed on
    stg.ooni_measurements) and software_version (the OONI Probe app
    version, a different concept) exist. test_version is carried through
    below since it is required to join marts.dim_ooni_probe_version_accuracy
    in Phase 2.
  - tor's targets and dnscheck's lookups are both dicts keyed by an
    opaque/URL-shaped key (same blocker as TD-47) -- confirmed live,
    genuinely not extractable via a fixed JSONPath. Neither is attempted
    here, per this phase's explicit scope; dnscheck's bootstrap layer
    (not the per-resolver lookups detail) is still extracted.

depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
  partition_by: measurement_date
  cluster_by:
    - country
    - test_name

custom_checks:
  - name: web_connectivity_and_facebook_messenger_still_dormant
    description: |
      TD-91 (2026-08-16), Task E. web_connectivity/facebook_messenger's
      wc_*/facebook_* extraction above was built and verified only
      against OONI's own spec docs (ts-017-web-connectivity.md,
      ts-019-facebook-messenger.md), never against real data -- CLIO's
      corpus has had zero rows of either test type since ingestion began
      (confirmed 2026-08-15, TD-87 Phase 1). This check's own FAILURE
      (either count going nonzero) is itself the actionable signal, not
      a problem to silence: it means one of these test types has started
      arriving for real, and before trusting ANY verdict this asset or
      int.ooni_measurement_verdicts derives for it, re-run the same
      live-sampling verification the 6 real test types got in the
      TD-87 Phase 1 session (per-test-type field presence and real
      values, sampled directly from the new rows) -- do NOT assume the
      spec-derived extraction above is correct until confirmed. Pay
      particular attention to web_connectivity's test_keys.blocking: it
      is polymorphic per OONI's own spec (`optional<string|bool>` -- the
      literal boolean `false` when clean, or one of several strings when
      anomalous), and this asset's wc_blocking extraction has never been
      checked against a real value of either shape.
    query: |
      SELECT COUNTIF(test_name IN ('web_connectivity', 'facebook_messenger'))
      FROM `{{ var.project_id }}.stg.ooni_measurement_summary`
    value: 0

columns:
  - name: measurement_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: test_name
    type: string
    checks:
      - name: not_null
@bruin */

WITH measurements AS (
  SELECT *
  FROM `{{ var.project_id }}.stg.ooni_measurements`
)

SELECT
  measurement_id,
  test_name,
  probe_asn,
  probe_network_name,
  country,
  measurement_date,
  measurement_start_time,
  test_version,
  failure AS measurement_failure,

  -- web_connectivity (ooni/spec ts-017-web-connectivity.md, 2024-02-14-001
  -- -- 0 live rows in CLIO's corpus as of 2026-08-15, verified against
  -- spec rather than live data; blocking is optional<string|bool>: the
  -- literal bool `false` when clean, or a string ('dns'/'tcp_ip'/
  -- 'http-diff'/'http-failure') when anomalous -- extracted as a string
  -- via JSON_VALUE so both shapes land as text ('false' or the reason).
  JSON_VALUE(raw_test_keys, '$.blocking') AS wc_blocking,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.accessible') AS BOOL) AS wc_accessible,
  JSON_VALUE(raw_test_keys, '$.dns_consistency') AS wc_dns_consistency,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.body_proportion') AS FLOAT64) AS wc_body_proportion,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.status_code_match') AS BOOL) AS wc_status_code_match,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.headers_match') AS BOOL) AS wc_headers_match,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.title_match') AS BOOL) AS wc_title_match,
  JSON_VALUE(raw_test_keys, '$.control_failure') AS wc_control_failure,

  -- signal (ts-029-signal.md) -- signal_backend_status in {'ok','blocked'}
  -- only, confirmed live across all 50,454 rows, no NULLs, no third value.
  JSON_VALUE(raw_test_keys, '$.signal_backend_status') AS signal_backend_status,
  JSON_VALUE(raw_test_keys, '$.signal_backend_failure') AS signal_backend_failure,

  -- whatsapp (ts-018-whatsapp.md) -- three status fields, each in
  -- {'ok','blocked'} only, confirmed live. The two "list of affected
  -- endpoints" fields are arrays, not booleans -- extracted as counts;
  -- test_anomaly_flag derivation in int.ooni_measurement_verdicts treats
  -- count > 0 as the boolean signal the original design hypothesized.
  JSON_VALUE(raw_test_keys, '$.whatsapp_endpoints_status') AS whatsapp_endpoints_status,
  JSON_VALUE(raw_test_keys, '$.whatsapp_web_status') AS whatsapp_web_status,
  JSON_VALUE(raw_test_keys, '$.whatsapp_web_failure') AS whatsapp_web_failure,
  JSON_VALUE(raw_test_keys, '$.registration_server_status') AS registration_server_status,
  JSON_VALUE(raw_test_keys, '$.registration_server_failure') AS registration_server_failure,
  ARRAY_LENGTH(IFNULL(JSON_QUERY_ARRAY(raw_test_keys, '$.whatsapp_endpoints_blocked'), ARRAY<STRING>[]))
    AS whatsapp_endpoints_blocked_count,
  ARRAY_LENGTH(IFNULL(JSON_QUERY_ARRAY(raw_test_keys, '$.whatsapp_endpoints_dns_inconsistent'), ARRAY<STRING>[]))
    AS whatsapp_endpoints_dns_inconsistent_count,

  -- telegram (ts-020-telegram.md) -- tcp/http blocking are real JSON
  -- booleans, confirmed live ("true"/"false" literals, not strings).
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.telegram_tcp_blocking') AS BOOL) AS telegram_tcp_blocking,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.telegram_http_blocking') AS BOOL) AS telegram_http_blocking,
  JSON_VALUE(raw_test_keys, '$.telegram_web_status') AS telegram_web_status,
  JSON_VALUE(raw_test_keys, '$.telegram_web_failure') AS telegram_web_failure,

  -- facebook_messenger (ts-019-facebook-messenger.md) -- 0 live rows in
  -- CLIO's corpus, verified against spec only (both optional<bool>).
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.facebook_dns_blocking') AS BOOL) AS facebook_dns_blocking,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.facebook_tcp_blocking') AS BOOL) AS facebook_tcp_blocking,

  -- psiphon (ts-015-psiphon.md) -- $.failure here is psiphon's own
  -- test_keys-level failure path, CONFIRMED NOT redundant with the
  -- (always-NULL) top-level measurement_failure above -- 863/50,673 live
  -- rows are non-NULL here, carrying real failure strings
  -- (unknown_failure:.../generic_timeout_error/eof_error/etc.).
  JSON_VALUE(raw_test_keys, '$.failure') AS psiphon_failure,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.bootstrap_time') AS FLOAT64) AS psiphon_bootstrap_time,
  SAFE_CAST(JSON_VALUE(raw_test_keys, '$.max_runtime') AS FLOAT64) AS psiphon_max_runtime,

  -- dnscheck (ts-028-dnscheck.md), bootstrap layer only -- per-resolver
  -- `lookups` (dict keyed by resolver URL) deliberately not extracted
  -- this phase, same blocker class as TD-47. Real signal is the
  -- top-level $.bootstrap_failure convenience field; the nested
  -- $.bootstrap.failure path is 100% NULL in live data (confirmed by
  -- direct comparison, not assumed) despite bootstrap_failure itself
  -- being populated for ~9.4K/1.1M rows.
  JSON_VALUE(raw_test_keys, '$.bootstrap_failure') AS dnscheck_bootstrap_failure

  -- tor (ts-023-tor.md): no fields extracted this phase -- $.targets is a
  -- dict keyed by opaque "ip:port" target identifiers, same blocker class
  -- as dnscheck's lookups and TD-47, confirmed live. Note for a future
  -- phase: tor also exposes non-dict-keyed top-level summary counters
  -- (or_port_accessible/or_port_total/obfs4_accessible/obfs4_total/
  -- dir_port_accessible/dir_port_total) that could give a simple
  -- aggregate anomaly signal without touching `targets` at all -- not
  -- built here, out of this phase's explicit scope, flagged as a lead.

FROM measurements;
