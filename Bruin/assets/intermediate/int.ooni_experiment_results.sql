/* @bruin
name: int.ooni_experiment_results
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni

description: |
  OONI experiment results derived from protocol observations.
  Grain: one interpreted result per protocol observation.

depends:
  - stg.ooni_dns_observations
  - stg.ooni_tcp_observations
  - stg.ooni_tls_observations
  - stg.ooni_http_observations

materialization:
  type: table
  strategy: create+replace

columns:
  - name: experiment_result_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: result_state
    type: string
    checks:
      - name: accepted_values
        value: [BLOCKED, OK, DOWN, UNKNOWN]
  - name: exclusion_reason
    type: string
    description: |
      TD-68/TD-69 (2026-08-01): nullable. Set when a raw signal that would
      otherwise classify as interference is a confirmed benign artifact
      (a known client-side canary hostname, a known-good rotated TLS root
      CA). result_state/blocking_detail already reflect the corrected
      verdict; this column exists so the original evidence and the reason
      it was excluded stay visible and auditable, rather than silently
      disappearing into 'OK'.
@bruin */

WITH dns_source AS (
  SELECT
    *,
    -- TD-68 (2026-08-01): the previous version of this bogon check matched
    -- on the shape of `answer` alone, with no check of `answer_type` and no
    -- exclusion for known-benign infrastructure. That wrongly classified
    -- uptime.signal.org -- Signal's own intentional client-side canary
    -- hostname, which always resolves to loopback as a benign health check
    -- -- as HIGH-confidence DNS interference (confirmed with OONI's
    -- Signal-test author, hellais, 2026-07-30: "the DNS results with IP
    -- 127.0.0.1 are to be considered normal"). It would also have wrongly
    -- flagged a CNAME target that happened to start with fc/fd/fe80 (the
    -- regex ran against `answer` regardless of record type). Restricting to
    -- answer_type IN ('A','AAAA') fixes the CNAME case; excluding the
    -- canary hostname for the signal test fixes the other. Sampled
    -- whatsapp/telegram DNS observations for an analogous fixed/universal
    -- canary before finalizing this exclusion list -- found no such canary
    -- (no single hostname answers bogon on every session the way
    -- uptime.signal.org does). Regex-bogon-shaped rows do exist for both
    -- apps (353 total, live), but structurally unlike a canary: concentrated
    -- on two dates (2024-02-25/26), ~18 distinct real WhatsApp/Telegram edge
    -- hostnames bogoning simultaneously in the same session -- the
    -- whole-session-at-once signature TD-55 already established as real
    -- interference, not an artifact. Correctly left unexcluded.
    (
      answer_type IN ('A', 'AAAA')
      AND REGEXP_CONTAINS(LOWER(COALESCE(answer, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$|::1$|fc|fd|fe80)')
      AND NOT (test_name = 'signal' AND hostname = 'uptime.signal.org')
    ) AS is_answer_bogon
  FROM `{{ var.project_id }}.stg.ooni_dns_observations`
),

dns AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'dns' AS protocol,
    hostname AS observation_target,
    answer AS endpoint_ip,
    CAST(NULL AS INT64) AS endpoint_port,
    dns_failure AS failure_reason,
    -- TD-55 (2026-07-06): 'dns_bogon_error' is the probe engine's OWN
    -- bogon verdict -- it detected bogon answers, discarded them, and
    -- reported only this failure string (verified in raw JSON: answers is
    -- null on every such row, so the answer-field regex below can never
    -- fire). Live evidence established these are real interference
    -- signatures, not artifacts: all 9,046 rows are dnscheck bootstrap
    -- lookups of public DoH/DoT resolver hostnames where EVERY resolver
    -- domain in the session bogoned at once (4,523/4,523 measurements,
    -- zero mixed) while messaging apps' DNS on the same network-days
    -- resolved normally (whatsapp 24,553 OK vs 2 DOWN) -- the selective
    -- anti-encrypted-DNS enforcement signature, exactly what dnscheck
    -- exists to detect. Kept as a distinct blocking_detail
    -- ('dns.bogon_probe_reported' vs the regex path's 'dns.bogon') to
    -- preserve verdict provenance; downstream counts both. Untouched by
    -- TD-68 -- a different signal, not the answer-regex path.
    CASE
      WHEN is_answer_bogon THEN 'BLOCKED'
      WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 'BLOCKED'
      WHEN LOWER(COALESCE(dns_failure, '')) IN ('nxdomain', 'dns_nxdomain_error') THEN 'DOWN'
      WHEN dns_failure IS NOT NULL THEN 'UNKNOWN'
      WHEN answer IS NOT NULL THEN 'OK'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN is_answer_bogon THEN 'dns.bogon'
      WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 'dns.bogon_probe_reported'
      WHEN LOWER(COALESCE(dns_failure, '')) IN ('nxdomain', 'dns_nxdomain_error') THEN 'dns.nxdomain'
      WHEN dns_failure IS NOT NULL THEN CONCAT('dns.', LOWER(dns_failure))
      WHEN answer IS NOT NULL THEN 'dns.ok'
      ELSE 'dns.no_answer'
    END AS blocking_detail,
    CASE
      WHEN is_answer_bogon THEN 0.90
      -- Probe-engine bogon verdict: same strength as the regex path.
      WHEN LOWER(COALESCE(dns_failure, '')) = 'dns_bogon_error' THEN 0.90
      WHEN answer IS NOT NULL THEN 0.70
      ELSE 0.40
    END AS confidence_score,
    CAST(NULL AS STRING) AS exclusion_reason
  FROM dns_source
),

tcp AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'tcp' AS protocol,
    ip_address AS observation_target,
    ip_address AS endpoint_ip,
    port AS endpoint_port,
    tcp_failure AS failure_reason,
    CASE
      WHEN connect_success IS TRUE THEN 'OK'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 'BLOCKED'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%timeout%' THEN 'DOWN'
      WHEN tcp_failure IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN connect_success IS TRUE THEN 'tcp.ok'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 'tcp.rst'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%timeout%' THEN 'tcp.timeout'
      WHEN tcp_failure IS NOT NULL THEN CONCAT('tcp.', LOWER(tcp_failure))
      ELSE 'tcp.unknown'
    END AS blocking_detail,
    CASE
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 0.80
      WHEN connect_success IS TRUE THEN 0.70
      ELSE 0.45
    END AS confidence_score,
    CAST(NULL AS STRING) AS exclusion_reason
  FROM `{{ var.project_id }}.stg.ooni_tcp_observations`
),

tls_source AS (
  SELECT
    *,
    -- TD-72 item (d) / TD-69 (2026-08-01): Signal rotated its TLS root CA
    -- in 2022 (old "TextSecure"/Open Whisper Systems root -> new "Signal
    -- Messenger, LLC" root). Older OONI probe versions have broken
    -- certificate-verification logic against the new root and report
    -- ssl_unknown_authority against Signal's real, legitimate backend
    -- servers -- a known, expected client-side artifact, confirmed
    -- directly with OONI's Signal-test author (hellais, 2026-07-30), who
    -- pointed at oonipipeline's own SignalTransformer
    -- (oonipipeline/src/oonipipeline/transforms/nettests/signal.py) as the
    -- reference implementation. That file's two-certificate PEM trust
    -- store was fetched directly from ooni/data's main branch (not
    -- retyped) and its fingerprints independently re-derived here via
    -- SHA-256 over the DER bytes -- both matched byte-for-byte against the
    -- live June 25 2024 flagged measurement's presented certificate before
    -- this was written. Correction made during this same fix, before
    -- shipping: the originally-assumed "before" state (these rows classify
    -- BLOCKED, per `WHEN handshake_success IS FALSE THEN 'BLOCKED'`) does
    -- not hold against this table's actual data -- `handshake_success` was
    -- NULL for every row here at the time, not just Signal's (TD-72, fixed
    -- 2026-08-01 -- see stg.ooni_tls_observations.sql; handshake_success
    -- now derives from `tls_failure IS NULL` instead of the wrong
    -- `$.status.*` path). These rows' real prior result_state was
    -- 'UNKNOWN', not 'BLOCKED'. This fix still correctly moves them to
    -- 'OK', which remains the right verdict -- Signal's real backend,
    -- reachable -- just under a corrected description of what it fixes.
    EXISTS (
      SELECT 1
      FROM UNNEST(peer_certificate_sha256s) AS fp
      WHERE fp IN (
        -- Old root ("TextSecure", Open Whisper Systems), expired
        -- 2023-03-23 -- already expired before this project's OONI
        -- ingestion window starts (2023-06-01), included for completeness.
        '098fd5403f63fef89fba4cb4b98135ca2e73dc42c0ed03a377e8383f2d1fe9ea',
        -- New root ("Signal Messenger, LLC"), issued 2022-01-26.
        'ddb0f92bb95c8d6fd202ea6e8cc5ccd182b544f8cd696f47d580659ddc9df65a'
      )
    ) AS presents_known_signal_root_ca
  FROM `{{ var.project_id }}.stg.ooni_tls_observations`
),

tls AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'tls' AS protocol,
    COALESCE(server_name, ip_address) AS observation_target,
    ip_address AS endpoint_ip,
    port AS endpoint_port,
    tls_failure AS failure_reason,
    -- All three cert-match arms below (result_state, blocking_detail,
    -- confidence_score) are gated on tls_failure = 'ssl_unknown_authority'
    -- specifically, NOT on the broader `test_name = 'signal' AND
    -- presents_known_signal_root_ca` this fix originally used. Caught in a
    -- third review pass, after the exclusion_reason gate fix above: the
    -- broader condition also matched ~166K rows with tls_failure IS NULL
    -- (already-successful handshakes -- TD-72's bug, not this one's, and
    -- flipping them here would have silently done half of TD-72's job for
    -- `signal` only, leaving whatsapp/telegram/psiphon's equally-affected
    -- successful rows still misclassified UNKNOWN -- an inconsistency
    -- across apps this fix never intended to create) and, separately,
    -- would have taken priority over the connection_reset/timeout arms
    -- below for any row that happened to present a recognized cert AND
    -- fail for an unrelated reason, masking a real interference signal.
    -- Narrowing to the exact confirmed artifact (ssl_unknown_authority)
    -- fixes both: TD-72 stays entirely unfixed and uniform across all four
    -- apps as intended, and reset/timeout rows keep falling through to
    -- their real verdicts regardless of which certificate they presented.
    -- TD-72 (2026-08-01): handshake_success now genuinely reflects success
    -- (tls_failure IS NULL, fixed at the staging layer). Deliberately NOT
    -- restoring a `WHEN handshake_success IS FALSE THEN 'BLOCKED'` arm here
    -- -- that arm existed before this fix but was permanently dead code
    -- (handshake_success was always NULL), so it never actually ran; had it
    -- been left in place, turning handshake_success on would have made it
    -- fire for real for the first time, silently reclassifying every
    -- TLS failure mode not already caught by the reset/timeout/cert-
    -- exclusion arms above (ssl_invalid_hostname, connection_aborted,
    -- eof_error, etc.) from 'UNKNOWN' to 'BLOCKED' -- a real classification
    -- change with no review behind it, and squarely TD-71's still-open
    -- question (per-failure-mode confidence/verdict), not this fix's. Any
    -- row with a failure the earlier arms don't name still falls through
    -- to the explicit `tls_failure IS NOT NULL THEN 'UNKNOWN'` arm below,
    -- byte-for-byte the same behavior as before this fix -- this CASE only
    -- changes what happens to rows where tls_failure IS NULL (genuine
    -- successes), which is the entire scope of TD-72.
    CASE
      WHEN handshake_success IS TRUE THEN 'OK'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%reset%' THEN 'BLOCKED'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%timeout%' THEN 'DOWN'
      WHEN tls_failure = 'ssl_unknown_authority' AND test_name = 'signal' AND presents_known_signal_root_ca THEN 'OK'
      WHEN tls_failure IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    -- Deliberately reused 'tls.ok' rather than a new label here (not
    -- 'tls.known_signal_root_ca') -- features.protocol_daily_signals'
    -- tls_handshake_failure_events counter is `STARTS_WITH(blocking_detail,
    -- 'tls.') AND blocking_detail NOT IN ('tls.ok', 'tls.rst')`, which would
    -- have silently miscounted a new label as a failure event despite
    -- result_state = 'OK'. exclusion_reason below carries the distinct
    -- provenance instead; tls_failure ('ssl_unknown_authority') stays
    -- visible unchanged in failure_reason.
    CASE
      WHEN handshake_success IS TRUE THEN 'tls.ok'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%reset%' THEN 'tls.rst'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%timeout%' THEN 'tls.timeout'
      WHEN tls_failure = 'ssl_unknown_authority' AND test_name = 'signal' AND presents_known_signal_root_ca THEN 'tls.ok'
      WHEN tls_failure IS NOT NULL THEN CONCAT('tls.', LOWER(tls_failure))
      ELSE 'tls.unknown'
    END AS blocking_detail,
    -- Same reasoning as result_state above: no `handshake_success IS FALSE
    -- THEN 0.75` arm here either. That arm predates this fix and was
    -- likewise permanently dead (handshake_success was always NULL); had
    -- it come alive alongside this fix, every non-reset/timeout/cert-
    -- exclusion failure row's confidence_score would have jumped from 0.45
    -- to 0.75 with no per-failure-mode review behind that specific number
    -- -- again TD-71's question, not this one's. Failure rows keep their
    -- pre-fix confidence_score (ELSE 0.45) unchanged; only genuine
    -- successes move (0.45 UNKNOWN -> 0.70 OK), matching result_state's
    -- own scope exactly.
    CASE
      WHEN tls_failure = 'ssl_unknown_authority' AND test_name = 'signal' AND presents_known_signal_root_ca THEN 0.70
      WHEN handshake_success IS TRUE THEN 0.70
      ELSE 0.45
    END AS confidence_score,
    -- Gated identically to the three arms above (tls_failure =
    -- 'ssl_unknown_authority' AND test_name = 'signal' AND
    -- presents_known_signal_root_ca) -- three review passes got this gate
    -- to its final shape, not one. Pass 1: gating on handshake_success IS
    -- FALSE (matching this CTE's other BLOCKED-arm convention) looked
    -- right but was checked against live data before shipping and found
    -- to always evaluate false, because `handshake_success` is NULL for
    -- 100% of rows in this table, for every test_name -- a separate,
    -- larger, pre-existing bug, logged as TD-72, not fixed here. Pass 2:
    -- gating on `tls_failure IS NOT NULL` fixed that, but was still too
    -- broad -- it also caught the connection_reset/timeout arms' rows if
    -- they happened to present a recognized cert, which would have masked
    -- a real interference signal, and disagreed with the (correctly
    -- narrower) result_state/blocking_detail/confidence_score arms above,
    -- which by then had already been tightened. Pass 3 (this one): exact
    -- match to `tls_failure = 'ssl_unknown_authority'`, so this column's
    -- population always agrees with why the other three columns actually
    -- changed value -- exactly 34,146 rows, the ones whose raw tls_failure
    -- would otherwise have left them at 'UNKNOWN' (not 'BLOCKED' -- TD-69's
    -- original framing that these were BLOCKED was itself wrong, corrected
    -- once TD-72 was found). Deliberately excludes the further ~166K
    -- already-tls_failure-IS-NULL rows that also present a recognized
    -- Signal cert -- those were never a false-BLOCKED (or false-UNKNOWN)
    -- signal this fix set out to correct; they are TD-72's bug, not TD-69's,
    -- and now correctly remain UNKNOWN, uniform with whatsapp/telegram/
    -- psiphon's equally-affected (but unfixed-here) successful rows.
    CASE
      WHEN tls_failure = 'ssl_unknown_authority' AND test_name = 'signal' AND presents_known_signal_root_ca
        THEN 'KNOWN_SIGNAL_ROOT_CA'
      ELSE NULL
    END AS exclusion_reason
  FROM tls_source
),

http AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'http' AS protocol,
    COALESCE(url, target) AS observation_target,
    CAST(NULL AS STRING) AS endpoint_ip,
    CAST(NULL AS INT64) AS endpoint_port,
    http_failure AS failure_reason,
    CASE
      WHEN status_code = 451 THEN 'BLOCKED'
      WHEN status_code BETWEEN 200 AND 399 THEN 'OK'
      WHEN http_failure IS NOT NULL THEN 'UNKNOWN'
      WHEN status_code IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN status_code = 451 THEN 'http.451'
      WHEN status_code BETWEEN 200 AND 399 THEN 'http.ok'
      WHEN http_failure IS NOT NULL THEN CONCAT('http.', LOWER(http_failure))
      WHEN status_code IS NOT NULL THEN CONCAT('http.status_', CAST(status_code AS STRING))
      ELSE 'http.unknown'
    END AS blocking_detail,
    CASE
      WHEN status_code = 451 THEN 0.90
      WHEN status_code BETWEEN 200 AND 399 THEN 0.70
      ELSE 0.40
    END AS confidence_score,
    CAST(NULL AS STRING) AS exclusion_reason
  FROM `{{ var.project_id }}.stg.ooni_http_observations`
),

unioned AS (
  SELECT * FROM dns
  UNION ALL
  SELECT * FROM tcp
  UNION ALL
  SELECT * FROM tls
  UNION ALL
  SELECT * FROM http
)

SELECT
  TO_HEX(MD5(CONCAT(observation_id, '|', result_state, '|', blocking_detail))) AS experiment_result_id,
  *,
  result_state = 'BLOCKED' AS is_blocking_signal,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM unioned;

