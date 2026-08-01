/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_tls_failure_evidence
type: bq.sql
connection: bigquery-default

description: |
  TD-71 (2026-08-01): per-failure-mode confidence weights for TLS handshake
  failures, replacing the flat `ELSE 0.45` collapse in
  int.ooni_experiment_results.sql's `tls` CTE. Joined on `tls_failure`
  (exact string match; no ranged lookup needed, unlike
  marts.dim_censorship_confidence).

  Scope: built only from the tls_failure values actually observed in
  CLIO's live Kenya TLS data as of 2026-08-01 (6 distinct strings across
  stg.ooni_tls_observations, confirmed by direct query, not assumed from
  the general OONI spec's larger failure-string vocabulary). Any
  tls_failure not present here (including one that appears in the future)
  must resolve to the query-side default floor, never inherit an elevated
  tier -- see the fallback COALESCE in int.ooni_experiment_results.sql.

  standalone_confidence is the score used when no additional corroborating
  signal is available. sourced_from_ooni_spec cites the exact wording from
  ooni/spec's df-007-errors.md (data-formats/df-007-errors.md) for the
  evidentiary category (genuine network-level failure vs. artifact),
  fetched directly, not inferred -- this caught a real correction to an
  earlier scoping pass (see connection_aborted's row).

  connection_reset and generic_timeout_error already have dedicated
  state-routing arms (BLOCKED / DOWN respectively) in the tls CTE's
  result_state CASE, unchanged by this table -- this table only supplies
  their confidence_score, so the state-routing logic and the evidentiary
  weighting logic each live in exactly one place.

  Deliberately NOT included: connection_already_closed, interrupted --
  ooni/spec documents both as artifacts (I/O on an already-closed socket;
  client-side context cancellation), not evidence of network interference
  at all, which argues for eventual exclusion_reason routing (the TD-69
  pattern) rather than a confidence value -- but zero rows of either
  string exist in CLIO's current Kenya TLS data, so there is no concrete
  case to build or test that routing against yet. If either ever appears,
  it will silently take the query-side default floor (never elevated,
  per the fallback design), which is safe but not the eventually-correct
  treatment -- flagged as TD-71's own residual scope, not resolved here.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'connection_reset' AS tls_failure,
        'ACTIVE_RESET' AS tier,
        0.60 AS standalone_confidence,
        'ECONNRESET (ooni/spec df-007-errors.md)' AS sourced_from_ooni_spec,
        'RST injection is the classic active-interference signature -- '
        || 'the strongest single-failure-mode evidence in this table. '
        || 'Already routed to result_state = BLOCKED by the tls CTE\'s '
        || 'own LIKE \'%reset%\' arm; this row only raises its confidence '
        || '(was flat 0.45, same as every other failure mode).'
            AS rationale
    ),

    STRUCT(
        'generic_timeout_error' AS tls_failure,
        'TIMEOUT_ATTENUATED' AS tier,
        0.40 AS standalone_confidence,
        'error returned when a timeout expires (ooni/spec df-007-errors.md)'
            AS sourced_from_ooni_spec,
        'Least attributable failure mode -- a captive-portal-style block '
        || 'and ordinary null-routed network unreachability look '
        || 'identical from this vantage point, a documented limitation '
        || 'this table cannot resolve. Already routed to result_state = '
        || 'DOWN by the tls CTE\'s own LIKE \'%timeout%\' arm; lowered '
        || 'from the prior flat 0.45 to reflect this is weaker evidence '
        || 'than an unmapped/unknown failure, not the same as it.'
            AS rationale
    ),

    STRUCT(
        'eof_error' AS tls_failure,
        'AMBIGUOUS_FAILURE' AS tier,
        0.50 AS standalone_confidence,
        'unexpected EOF on connection (ooni/spec df-007-errors.md)'
            AS sourced_from_ooni_spec,
        'Genuine network-level failure per spec, but the spec text itself '
        || 'gives no signature distinguishing SNI-based filtering from '
        || 'ordinary flakiness. Live calibration (2026-08-01): 9 rows, '
        || 'spread across only 2 ASNs and 9 distinct dates -- scattered, '
        || 'not a coordinated multi-ASN burst -- consistent with '
        || 'genuine-but-weak evidence, not scored higher.' AS rationale
    ),

    STRUCT(
        'connection_aborted' AS tls_failure,
        'AMBIGUOUS_FAILURE' AS tier,
        0.50 AS standalone_confidence,
        'ECONNABORTED (ooni/spec df-007-errors.md)' AS sourced_from_ooni_spec,
        'Corrects an earlier scoping pass that grouped this with '
        || 'connection_already_closed/interrupted as a client-side '
        || 'artifact -- checked against ooni/spec directly '
        || '(data-formats/df-007-errors.md) before shipping, which maps '
        || 'connection_aborted to ECONNABORTED, a genuine network-level '
        || 'failure, not an artifact; connection_already_closed and '
        || 'interrupted are the documented artifacts, and neither one '
        || 'occurs anywhere in CLIO\'s current TLS data. Live calibration '
        || '(2026-08-01): 4 rows, each on a distinct ASN and a distinct '
        || 'date -- total scatter, no coordination -- same evidentiary '
        || 'weight as eof_error, not elevated further.' AS rationale
    ),

    STRUCT(
        'ssl_invalid_certificate' AS tls_failure,
        'CERT_UNCORROBORATED' AS tier,
        0.45 AS standalone_confidence,
        'e.g. certificate expired (ooni/spec df-007-errors.md)'
            AS sourced_from_ooni_spec,
        'oonipipeline\'s own web_analysis.py weights this failure family '
        || 'highest among TLS outcomes (0.9) -- but only when a control '
        || 'vantage point corroborates the block; CLIO has no equivalent '
        || 'corroboration signal available (checked live, 2026-08-01: '
        || 'the ingested raw measurement JSON carries no anomaly/blocking '
        || 'field at all -- those are OONI fastpath/API-computed fields, '
        || 'never present in the raw probe measurement CLIO ingests). '
        || 'Kept at the pre-fix floor rather than elevated without that '
        || 'corroboration -- elevating this exact failure family '
        || 'unconditionally is the precise shape of the false-positive '
        || 'this project fixed twice already today (TD-68, TD-69). '
        || 'Deferred, not resolved -- see TD-71\'s technical-debt entry.'
            AS rationale
    ),

    STRUCT(
        'ssl_unknown_authority' AS tls_failure,
        'CERT_UNCORROBORATED' AS tier,
        0.45 AS standalone_confidence,
        'cannot find CA validating certificate (ooni/spec df-007-errors.md)'
            AS sourced_from_ooni_spec,
        'Same corroboration gap as ssl_invalid_certificate, same '
        || 'deferral. The signal-test subset that already has a real, '
        || 'narrower corroboration signal (TD-69\'s known-root-CA '
        || 'certificate match) is excluded via exclusion_reason before '
        || 'ever reaching this default -- this row only governs the '
        || 'residual rows that do not present a recognized Signal root '
        || '(live, 2026-08-01: 739 signal + 1 telegram).' AS rationale
    )

]);
