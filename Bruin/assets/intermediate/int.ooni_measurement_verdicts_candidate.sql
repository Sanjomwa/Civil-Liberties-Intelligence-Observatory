/* @bruin
name: int.ooni_measurement_verdicts_candidate
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  TD-91 (2026-08-16): candidate/publish split for the CONFIRMED guard's
  write-order. This asset holds the REAL computation (previously all of
  int.ooni_measurement_verdicts.sql's own body) -- int.ooni_measurement_
  verdicts.sql is now a trivial `SELECT * FROM this table`, published only
  after int.ooni_measurement_verdicts_confirmed_guard.sql passes against
  THIS candidate table, not the already-published one.

  Why: create+replace does not roll back a failed run -- without this
  split, a CONFIRMED-outside-web_connectivity violation would leave a bad
  table live and queryable (by Streamlit or any direct query) for the
  entire window between the violation landing and a fixed rerun
  succeeding. This closes that exposure the same way
  intelligence.acled_pressure_regimes_precondition_check's check-before-
  write pattern does for ACLED.

  Investigated and confirmed cheap before building, not assumed: this
  table and its upstream (stg.ooni_measurement_summary) are both small,
  scalar-only tables (222 MiB / 197 MiB respectively, live-measured via
  __TABLES__) -- nothing like the 63 GiB raw-JSON-carrying
  stg.ooni_measurements this project's 2026-07-06 cost audit flagged as
  the pipeline's actual expensive-rebuild risk. Materializing this
  candidate and then a trivial passthrough copy costs a small fraction of
  a cent at this project's own $6.25/TiB on-demand pricing -- confirmed
  with real byte counts, not the cost audit's own already-expensive OONI
  observation-CTE shape (which reads raw_test_keys directly; this asset
  does not).

  No naming convention for a "_candidate" pattern existed anywhere else
  in this repo before this fix (checked) -- this establishes one.

  Everything below this point (grain, CONFIRMED's structural guard layer
  1, TD-91's psiphon_failure/probe_accuracy_gate corrections) is
  unchanged from the original int.ooni_measurement_verdicts.sql -- see
  reports.md's 2026-08-16 TD-91 session entry for the original TD-87
  Phase 2 design and this session's three corrections.

  TD-93 (2026-08-15): a fourth correction, found via external validation
  against OONI's own real, published per-measurement classification
  (/api/v1/measurements, matched by report_id) rather than CLIO-internal
  sampling. Signal's test_anomaly_flag overcounted ANOMALOUS by routing
  NXDOMAIN failures against two hostnames outside OONI's own current
  ts-029-signal.md spec into ANOMALOUS; OONI's own backend calls these
  FAILED. Fixed via a new signal_legacy_endpoint_nxdomain_only column
  (stg.ooni_measurement_summary.sql) consumed here ahead of test_anomaly_
  flag, same precedence as psiphon_failure. See this file's ooni_verdict
  CASE and reports.md's 2026-08-15 TD-93 entry for the full finding and
  the matched-pair verification (100% substantive agreement, up from
  78.8%, on the same 66-measurement sample TD-91's own investigation
  used).

  OONI's own real, per-measurement verdict vocabulary (OK / CONFIRMED /
  ANOMALOUS / FAILED), derived from each test's own probe-submitted
  summary field (stg.ooni_measurement_summary, Phase 1) -- NOT the same
  thing as result_state, which stays untouched, per-observation, and
  unconsumed by this asset.

  Grain: one row per measurement_id (OONI's own real grain), deliberately
  different from result_state's per-observation grain in
  int.ooni_experiment_results.sql. Consumed only by
  int.ooni_measurement_verdicts_confirmed_guard.sql and the published
  int.ooni_measurement_verdicts -- no existing mart or Streamlit page
  reads this candidate table directly, and none should (query the
  published table instead).

  measurement_failure (sourced from stg.ooni_measurements.failure, the
  raw measurement envelope's top-level `failure` key) is confirmed
  PERMANENTLY dead -- not just currently zero. Verified against OONI's
  own df-000-base.md spec (no top-level `failure` field defined on the
  base measurement envelope at all) and two live raw measurements
  fetched directly from api.ooni.io (a signal and a dnscheck sample, both
  report_id-matched into CLIO's own ingested tables to rule out
  survivorship bias -- both landed with full raw JSON fidelity). This is
  NOT evidence that failed measurements are being dropped before
  ingestion -- every real per-test failure signal lives at a test-
  specific path inside test_keys, which stg.ooni_measurement_summary
  already extracts and this asset already consumes via test_anomaly_flag.
  See the ooni_verdict CASE below for the one concrete correction this
  finding produced (psiphon_failure moved from ANOMALOUS to FAILED).

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
  corrections made in the original design before encoding it (compound
  version+date condition, cross-test test_version collisions, no
  engine_version field). TD-91 (2026-08-16): probe_accuracy_gate now
  gates ooni_verdict directly (see that CASE) -- confirmed the LEFT JOIN
  to dim_ooni_probe_version_accuracy already existed (the
  ADR-0001/TD-05-shaped "built but never joined" failure this session
  checked for did not recur), only the downstream *use* of its result
  was the still-open decision, resolved this session as exclude-not-flag.

  TD-101 Phase 3 (2026-08-20): dnscheck's FAILED tier is now reachable.
  Previously EVERY non-NULL dnscheck_bootstrap_failure value routed to
  ANOMALOUS in full, and FAILED was structurally unreachable for this
  test type (TD-101's own original finding). Live investigation of the
  full value distribution (9,412 non-NULL rows: dns_bogon_error 4,523,
  dns_nxdomain_error 3,120, generic_timeout_error 1,300, android_dns_
  cache_no_data 407, dns_temporary_failure 46, dns_server_misbehaving 16)
  found dns_bogon_error is the one value with a real, already-validated
  manipulation signature (TD-55: whole-session bogoning of DoH/DoT
  resolver hostnames while messaging-app DNS resolved normally on the
  same network-day, already classified BLOCKED @ 0.90 in int.ooni_
  experiment_results.sql, regression-locked by tests/test_ooni_dns_
  bogon_classification.py) -- it keeps its ANOMALOUS classification,
  unchanged. Every OTHER non-NULL value newly routes to FAILED, having
  been separately investigated and found NOT manipulation-shaped:
  dns_nxdomain_error, the second-largest at 33.1% of the total, is
  dominated by a handful of permanently-dead/typo'd DoH/DoT target
  hostnames in OONI's own dnscheck target list (doh.appliedprivacy.ne --
  almost certainly a typo for appliedprivacy.at -- 0/629 successes
  across this table's entire 2023-06-12 through 2025-03-05 ingestion
  window; draco.plan9-ns2.com and dnses.alekberg.net show the same
  100%-failure, permanently-dead signature), the same probe/test-
  infrastructure-artifact shape TD-47 Phase 1 already established for
  this test type's `lookups`-layer failures. This is a narrow carve-out,
  not a blanket rule -- an earlier design draft that would have routed
  ALL non-NULL values to FAILED was caught by advisory review before any
  code was written, precisely because it would have silently reverted
  TD-55. See the ooni_verdict CASE below for the actual predicate (self-
  contained, excludes dns_bogon_error explicitly rather than relying on
  CASE branch ordering) and reports.md for the full session account,
  including why TD-47 Phase 1/Phase 2a's answers-layer staging tables
  are deliberately not joined here. ooni_verdict_source stays
  'PARTIAL_BOOTSTRAP_ONLY' for dnscheck (no existing consumer of the
  literal's value requires changing it, confirmed by grep across
  streamlit/, Bruin/assets/marts/, Bruin/assets/features/, tests/, and
  Bruin/scripts/agreement_check/) -- the name still accurately describes
  the scope (bootstrap only, never the lookups layer), just with a
  fuller-than-before routing of that one field's real values now that
  FAILED is reachable. This fix's cascade (features.ooni_weekly_signals
  and the Streamlit National Stress Observatory page's dnscheck-
  selectable anomalous_rate series) moves dnscheck's live ANOMALOUS rate
  down materially, expected and correct, not a regression -- see
  reports.md for before/after figures. The tests/fixtures/ooni_weekly_
  golden/finance_bill_2024.json golden fixture's dnscheck ooni_verdict_
  weekly values are re-frozen in the same session, matching TD-93's own
  precedent for the exact same fixture.

  TD-91 (2026-08-16), Task D -- the NULL sentinel split. ooni_verdict
  IS NULL currently has THREE distinguishable causes, not two: (1) tor,
  by design, not implemented this phase -- ooni_verdict_source =
  'NOT_IMPLEMENTED'; (2) a known-bad-probe-version exclusion (Task B's
  new exclude-not-flag decision, signal-only today) -- probe_accuracy_gate
  = 'DISCARDED_BAD_PROBE_VERSION'; (3) a genuine, unexpected per-row
  extraction failure on an otherwise-implemented, otherwise-scored test
  type -- test_anomaly_flag hit its own defensive NULL fallback (e.g.
  signal_backend_status present but neither 'ok' nor 'blocked'). No new
  sentinel column was needed -- (1) and (2) are already fully
  distinguishable via the existing ooni_verdict_source/probe_accuracy_gate
  columns; (3) is simply "NULL and neither of the other two applies."
  The custom_checks entry below (unknown_extraction_failure_rate_is_zero)
  monitors (3) specifically, per test_name -- live rate confirmed 0 for
  every implemented+scored test type as of 2026-08-16 (signal/whatsapp/
  telegram/psiphon/dnscheck all show 0 unexplained-NULL rows; only tor's
  by-design NULLs and signal's known-bad-version exclusions exist today).
  A nonzero rate for any of those five going forward is a real alarm --
  it means a live OONI field shape changed underneath this asset's
  assumptions (e.g. a probe update introducing a new
  signal_backend_status value this CASE doesn't recognize).

  TD-105 (2026-08-21): whatsapp's test_anomaly_flag arm now uses
  whatsapp_web_accessible (stg.ooni_measurement_summary.sql) in place of
  whatsapp_web_status = 'blocked'. An eight-check verification session
  (2026-08-21) found whatsapp_web_status unreliable specifically at probe
  test_version=0.9.0 -- that probe version's own plain-HTTP check against
  http://web.whatsapp.com/ marks the whole web check "failed" whenever the
  response isn't exactly HTTP 302, regardless of whether the HTTPS leg of
  the same URL succeeded, and OONI's own backend scorer never reads this
  field at all. This produced a real, measured false-positive rate (32-
  33/33 matched pairs of this exact shape disagreed with OONI's own live
  classification) concentrated entirely in the obsolete 0.9.0 install
  base (100/100 directly-inspected raw rows carry a Meta-origin response
  signature with a null HTTPS-leg failure -- the HTTPS check succeeded
  every time). Probe 0.11.0 removes the flawed check; confirmed live that
  every 0.11.0 whatsapp_web_status='blocked' row's whatsapp_web_failure
  already matches $.requests[]'s HTTPS-leg failure field exactly (40/40
  sampled), so recomputing from raw data changes nothing for 0.11.0 and
  only reclassifies 0.9.0 rows where the HTTPS leg actually succeeded.
  This bug was confirmed dashboard-facing, not internal-only:
  features.ooni_weekly_signals -> the National Stress Observatory page's
  weekly-signal protocol selector renders whatsapp's anomalous_rate
  directly from this classification chain, live, today. Two other
  conditions in this same OR-chain were investigated in the same
  verification session: registration_server_status = 'blocked' (89%
  genuinely correct against OONI's live classification across both probe
  versions; a small, separate 2/562-row http_request_failed exception
  exists but is too small and different in kind to fold into this fix)
  was found NOT to share this shape and left untouched, while
  whatsapp_endpoints_blocked_count > 0 (real, 1,042 rows, but
  heterogeneous -- a small oracle check split ~50/50 against OONI's own
  judgment) was flagged as needing its own dedicated investigation.

  TD-105 build (2026-08-22): that dedicated investigation happened (two
  follow-up sessions, 2026-08-21 and 2026-08-22) and found
  whatsapp_endpoints_blocked_count > 0 actively wrong, not just
  imprecise -- OONI's own live scorer disables this exact rule in its
  source ("Disabled due to bug in the probe
  https://github.com/ooni/probe-engine/issues/341"), and restricted to
  the population where blocked_count was the ONLY driver, OONI agreed
  with CLIO's ANOMALOUS call 0/131 times across two independent samples.
  Removed from the OR-chain entirely (not thresholded), along with the
  permanently-dead whatsapp_endpoints_dns_inconsistent_count > 0 -- see
  that arm's own inline comment below for the full mechanism (branch
  precedence: OONI's endpoint-accessibility check is only ever reached
  after web/registration checks already pass). See reports.md's
  2026-08-21 and 2026-08-22 TD-105 session entries (verification and
  build) for the full account.

depends:
  - stg.ooni_measurement_summary
  - marts.dim_ooni_probe_version_accuracy

materialization:
  type: table
  strategy: create+replace

custom_checks:
  - name: unknown_extraction_failure_rate_is_zero
    description: |
      TD-91 (2026-08-16). Counts rows where ooni_verdict is NULL for a
      reason OTHER than tor's by-design NOT_IMPLEMENTED or a known-bad
      probe-version exclusion -- i.e. test_anomaly_flag genuinely failed
      to resolve on an implemented, scored test type. Must stay 0; a
      nonzero count means a live OONI field shape changed underneath
      this asset's per-test extraction (see this file's own Task D
      comment above for the three NULL causes and how they're told
      apart).
    query: |
      SELECT COUNT(*)
      FROM `{{ var.project_id }}.int.ooni_measurement_verdicts_candidate`
      WHERE ooni_verdict IS NULL
        AND ooni_verdict_source != 'NOT_IMPLEMENTED'
        AND probe_accuracy_gate != 'DISCARDED_BAD_PROBE_VERSION'
    value: 0

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

    -- TD-91 (2026-08-16): carried through so the final ooni_verdict CASE
    -- can route it to FAILED directly -- see that CASE for why.
    s.psiphon_failure,

    -- TD-93 (2026-08-15): carried through so the final ooni_verdict CASE
    -- can route it to FAILED ahead of test_anomaly_flag -- see that CASE
    -- and stg.ooni_measurement_summary.sql's header for the full finding.
    s.signal_legacy_endpoint_nxdomain_only,

    -- TD-101 Phase 3 (2026-08-20): carried through so the final
    -- ooni_verdict CASE can route dnscheck's non-bogon bootstrap
    -- failures to FAILED, while excepting dns_bogon_error -- see that
    -- CASE and this file's header for the full TD-55/TD-101 reasoning
    -- (an earlier blanket-FAILED design draft was caught by advisory
    -- review before any code was written, precisely to avoid this).
    s.dnscheck_bootstrap_failure,

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
        -- TD-105 (2026-08-21): whatsapp_web_status = 'blocked' replaced
        -- with whatsapp_web_accessible IS FALSE. whatsapp_web_status is
        -- the probe's OWN self-reported field, unreliable at probe
        -- test_version=0.9.0 (a plain-HTTP-leg check against
        -- http://web.whatsapp.com/ that OONI's own backend never reads,
        -- and that fires on ~100% of 0.9.0 traffic regardless of whether
        -- the HTTPS leg of the same URL succeeded -- confirmed via 100/100
        -- directly-inspected raw rows and reproduced in OONI's own live
        -- classification, which disagreed with CLIO's prior verdict on
        -- 32-33/33 matched pairs of this exact shape). whatsapp_web_
        -- accessible (stg.ooni_measurement_summary.sql) recomputes
        -- straight from $.requests[]'s own https://web.whatsapp.com/
        -- entry instead, matching what OONI's own backend actually does.
        -- Deliberately `IS FALSE`, not `= FALSE` or a bare negation: the
        -- NULL case (no matching request entry, confirmed 0/51,394 rows
        -- live today) must NOT count as blocked, the same
        -- inconclusive-not-blocked treatment this file gives missing data
        -- elsewhere. Confirmed additive for already-correct rows: every
        -- test_version=0.11.0 whatsapp_web_status='blocked' row's
        -- whatsapp_web_failure already matches this same $.requests[]
        -- entry's failure field exactly (40/40 sampled) -- 0.11.0's probe
        -- removed the flawed plain-HTTP check entirely, so this
        -- recomputation only changes behavior for test_version=0.9.0 rows
        -- where the HTTPS leg actually succeeded. Two other conditions
        -- investigated the same session and found NOT to share this
        -- shape: registration_server_status (89% genuinely correct; a
        -- small 2/562-row http_request_failed exception exists but is
        -- separate and too small to fold in here), left untouched, and
        -- whatsapp_endpoints_blocked_count > 0, investigated further and
        -- REMOVED below -- see the TD-105 build note.
        --
        -- TD-105 build (2026-08-22): whatsapp_endpoints_blocked_count > 0
        -- and whatsapp_endpoints_dns_inconsistent_count > 0 REMOVED from
        -- this OR-chain, not thresholded. Two follow-up verification
        -- sessions (2026-08-21, 2026-08-22) found the condition actively
        -- wrong, not just imprecise: OONI's own live scorer source
        -- contains this exact endpoint-blocked-count rule, commented out,
        -- with the note "Disabled due to bug in the probe
        -- https://github.com/ooni/probe-engine/issues/341" -- OONI tried
        -- it and abandoned it. Confirmed empirically against OONI's real
        -- classification: restricted to the population where blocked_
        -- count was the ONLY thing driving ANOMALOUS (whatsapp_web_
        -- accessible not FALSE, registration_server_status = 'ok'), OONI
        -- agreed with CLIO's ANOMALOUS call 0/131 times across two
        -- independently-drawn samples, spanning the full blocked_count
        -- range (1-15) and every magnitude bucket (the entire 25-row
        -- 7+ bucket sole-driver population included, twice). The earlier
        -- "high count usually means real interference" read was a
        -- confound: high-blocked_count rows are disproportionately ones
        -- where a web or registration failure ALSO occurred (only 18.4%
        -- of the 7+ bucket is actually isolated from that), and OONI's
        -- own scorer never reaches its endpoint-accessibility check at
        -- all once the web/registration checks have already failed --
        -- confirmed directly via OONI's API `scores.analysis` sub-object,
        -- present only when that branch is reached: 0/151 fetched rows
        -- this session showed `whatsapp_endpoints_accessible = false`,
        -- and every ANOMALOUS row lacking a sole-blocked_count driver
        -- (30/30 sampled) lacked the `analysis` key entirely, i.e. never
        -- reached the endpoint check in the first place. whatsapp_
        -- endpoints_dns_inconsistent_count > 0 is removed alongside it
        -- as dead weight, not on its own merits -- confirmed permanently
        -- 0/51,394 rows live, never populated by the probe. See reports.md's
        -- 2026-08-21 and 2026-08-22 TD-105 session entries for the full
        -- account.
        WHEN s.whatsapp_endpoints_status = 'blocked'
          OR s.whatsapp_web_accessible IS FALSE
          OR s.registration_server_status = 'blocked' THEN TRUE
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
      -- TD-91 (2026-08-16): psiphon_failure no longer feeds
      -- test_anomaly_flag -- moved to the FAILED branch below (see
      -- ooni_verdict's own CASE). psiphon has no other test-provided
      -- anomaly-detection field distinct from "did the probe/tunnel
      -- break," so it always resolves FALSE here; its verdict is
      -- decided by the FAILED check ahead of this flag ever being
      -- consulted for a psiphon_failure row.
      WHEN 'psiphon' THEN FALSE
      -- TD-101 Phase 3 (2026-08-20): narrowed from "any non-NULL
      -- bootstrap failure" to bogon only -- every other non-NULL value
      -- now routes to FAILED instead (see the ooni_verdict CASE below
      -- and this file's header for the full reasoning; this is a narrow
      -- carve-out, not a blanket rule).
      WHEN 'dnscheck' THEN CASE
        WHEN LOWER(COALESCE(s.dnscheck_bootstrap_failure, '')) = 'dns_bogon_error' THEN TRUE
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
    -- TD-91 (2026-08-16): probe_accuracy_gate now gates ooni_verdict
    -- directly. CHOSE: exclude (NULL), not just flag-alongside-a-
    -- computed-verdict. Reasoning: DISCARDED_BAD_PROBE_VERSION mirrors
    -- OONI's own real backend behavior -- the vendored score_signal()
    -- rule this table is built from IS a discard-before-scoring rule
    -- (scores.accuracy = 0.0 before any anomaly detection is attempted),
    -- not a mere confidence markdown. Computing ANOMALOUS/OK from a
    -- signal_backend_status value OONI's own backend would not have
    -- trusted enough to score at all would silently manufacture a
    -- classification with no real epistemic backing. CONFIRMED still
    -- wins ahead of this check -- fingerprint matching is a stronger,
    -- independent signal (structural web content, not behavioral
    -- scoring) that the version-accuracy rule was never about. This NULL
    -- is distinguishable from tor's NOT_IMPLEMENTED NULL via
    -- probe_accuracy_gate itself (tor's ooni_verdict_source stays
    -- NOT_IMPLEMENTED, never DISCARDED_BAD_PROBE_VERSION), so a
    -- downstream consumer can always tell the two apart.
    WHEN probe_accuracy_gate = 'DISCARDED_BAD_PROBE_VERSION' THEN NULL
    -- psiphon_failure added here, moved out of test_anomaly_flag. Live
    -- verification (TD-91 relay session) found CLIO's original
    -- measurement_failure source (the raw measurement envelope's
    -- top-level `failure` key) genuinely does not exist in OONI's real
    -- JSON for any test type -- confirmed against OONI's own
    -- df-000-base.md spec (no such field defined) and two live raw
    -- measurements fetched directly from api.ooni.io (signal, dnscheck),
    -- neither of which has a top-level `failure` sibling to `test_keys`.
    -- Both sampled measurements DO exist in CLIO's own ingested tables
    -- (report_id-matched) with full raw JSON fidelity -- ruling out
    -- survivorship bias; nothing is silently dropped before landing.
    -- The one real, generic, OONI-attached "the probe itself broke"
    -- signal (test_keys.failure / test_keys.failed_operation, present as
    -- a structural key across all 6 test types) is populated live ONLY
    -- for psiphon (863/50,673 rows) -- 0/rows for signal/whatsapp/
    -- telegram/dnscheck/tor, confirmed by direct query, not assumed to
    -- generalize. psiphon_failure's real values ("clientlib: tunnel
    -- establishment timeout", "StartTunnel called multiple times",
    -- "psiphonfeat: not enabled", etc.) are probe/tunnel-level breakage,
    -- matching OONI's own FAILED semantics ("the probe itself broke")
    -- precisely -- not ANOMALOUS ("signs of possible interference"),
    -- which is what this fix corrects: these rows were previously
    -- reachable only via test_anomaly_flag's TRUE branch, folding a
    -- genuine probe failure into the same bucket as a detected block.
    WHEN measurement_failure IS NOT NULL
      OR control_failure IS NOT NULL
      OR psiphon_failure IS NOT NULL THEN 'FAILED'
    -- TD-93 (2026-08-15). External validation against OONI's own real,
    -- published classification (/api/v1/measurements, matched by
    -- report_id) found signal's test_anomaly_flag (keyed only on
    -- signal_backend_status = 'blocked') overcounts ANOMALOUS by routing
    -- NXDOMAIN failures against two hostnames outside OONI's own current
    -- ts-029-signal.md spec -- textsecure-service.whispersystems.org
    -- (dead since 2023-12, confirmed via a clean one-time retirement
    -- signature in live per-month data) and api.directory.signal.org
    -- (dead across CLIO's entire ingestion window, zero successes ever)
    -- -- into ANOMALOUS, when OONI's own real backend calls these FAILED.
    -- This ahead of test_anomaly_flag, same precedence pattern as
    -- psiphon_failure above: FAILED wins over a computed ANOMALOUS,
    -- because it reflects a real, more specific, externally-corroborated
    -- terminal state OONI itself already assigns. signal_legacy_endpoint_
    -- nxdomain_only is already scoped (in stg.ooni_measurement_summary)
    -- to fire ONLY when none of OONI's four current-spec endpoints
    -- (cdsi/chat/sfu.voip/storage.signal.org) also show an nxdomain in
    -- the same measurement, so a genuine current-endpoint block still
    -- reaches ANOMALOUS below, unaffected. A matched-pair sample (66
    -- measurements against OONI's real anomaly/confirmed/failure
    -- booleans) reached 100% substantive agreement with this rule,
    -- versus 78.8% before it -- see reports.md's 2026-08-15 TD-93 entry.
    WHEN signal_legacy_endpoint_nxdomain_only THEN 'FAILED'
    -- TD-101 Phase 3 (2026-08-20). dnscheck's bootstrap layer reports six
    -- distinct non-NULL failure values live (see this file's header for
    -- the full distribution and the investigation each received before
    -- this fix). dns_bogon_error is EXCEPTED from this branch, not
    -- included: TD-55 already established it as a real, sampling-
    -- validated manipulation signal (whole-session bogoning of DoH/DoT
    -- resolver hostnames while messaging-app DNS resolved normally on
    -- the same network-day), already classified BLOCKED @ 0.90 in
    -- int.ooni_experiment_results.sql, and regression-locked by
    -- tests/test_ooni_dns_bogon_classification.py -- routing it here too
    -- would silently and partially revert that finding and produce a
    -- live contradiction between result_state (BLOCKED) and this column
    -- (FAILED) for the same rows. Every OTHER non-NULL value
    -- (dns_nxdomain_error, generic_timeout_error, android_dns_cache_
    -- no_data, dns_temporary_failure, dns_server_misbehaving) was
    -- separately investigated this session and found NOT manipulation-
    -- shaped -- dns_nxdomain_error in particular is dominated by a
    -- handful of permanently-dead/typo'd DoH/DoT target hostnames in
    -- OONI's own dnscheck target list (e.g. doh.appliedprivacy.ne --
    -- almost certainly a typo for appliedprivacy.at -- 0/629 successes
    -- across this table's entire ingestion window, 2023-06-12 through
    -- 2025-03-05), the same probe/test-infrastructure-artifact shape
    -- TD-47 Phase 1 already established for this test type's other
    -- non-bogon failure signals. This predicate is self-contained
    -- (excludes dns_bogon_error explicitly, does not rely on branch
    -- ordering or on test_anomaly_flag's own narrowed dnscheck logic
    -- above) because FAILED already outranks ANOMALOUS in this CASE's
    -- precedence -- a predicate that only tested "IS NOT NULL" here
    -- would silently swallow the bogon rows too. TD-47 Phase 1/Phase 2a's
    -- answers-layer staging tables (stg.ooni_dnscheck_lookups, stg.ooni_
    -- dnscheck_query_answers, stg.ooni_dnscheck_answer_bogon_flags) are
    -- deliberately NOT joined here -- they characterize a structurally
    -- different layer (per-resolver `lookups`, always resolving OONI's
    -- own fixed example.org) than bootstrap (the DoH/DoT provider
    -- hostname itself, resolved via the local system resolver), and
    -- Phase 2a found zero live bogon hits there anyway -- see reports.md
    -- for the full account.
    WHEN dnscheck_bootstrap_failure IS NOT NULL
      AND LOWER(COALESCE(dnscheck_bootstrap_failure, '')) != 'dns_bogon_error'
      THEN 'FAILED'
    WHEN test_anomaly_flag IS TRUE THEN 'ANOMALOUS'
    WHEN test_anomaly_flag IS NULL THEN NULL
    ELSE 'OK'
  END AS ooni_verdict,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM verdicts;
