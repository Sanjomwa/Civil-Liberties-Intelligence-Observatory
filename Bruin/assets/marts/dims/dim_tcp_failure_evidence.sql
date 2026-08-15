/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_tcp_failure_evidence
type: bq.sql
connection: bigquery-default

description: |
  TD-80 (2026-08-15, fixed in this session): per-failure-mode result_state/
  confidence for TCP connect failures, replacing the inline
  `LIKE '%timeout%'` substring match in int.ooni_experiment_results.sql's
  `tcp` CTE, which missed the literal OONI-originated failure string
  `timed_out` (a different string, not a substring of "timeout") -- 16 live
  rows fell through to the generic `UNKNOWN` fallback instead of `DOWN`.
  Modeled directly on marts.dim_tls_failure_evidence (same join shape:
  LEFT JOIN on the exact failure string). Unlike that table, this one also
  supplies result_state and blocking_detail, not just confidence_score --
  TD-80's own recommended fix was to replace the substring-match approach
  entirely with an explicit allowlist, not just re-weight confidence.

  Scope: built only from the tcp_failure values actually observed in
  CLIO's live Kenya TCP data as of 2026-08-15 (7 distinct strings across
  stg.ooni_tcp_observations, confirmed by direct query). Any tcp_failure
  not present here (including one that appears in the future) must resolve
  to the query-side default (UNKNOWN / 0.45), never inherit an elevated
  tier -- see the COALESCE/fallback arms in int.ooni_experiment_results.sql.

  This table intentionally reproduces today's live confidence_score for
  every failure string byte-for-byte (0.45 across the board -- the tcp
  CTE's pre-fix CASE gives every non-reset/non-success row a flat 0.45,
  there is no 0.40 tier in this CTE the way there is in the dns/http
  CTEs) -- the ONLY behavioral change this table introduces is `timed_out`
  moving from result_state=UNKNOWN/blocking_detail='tcp.timed_out' to
  result_state=DOWN/blocking_detail='tcp.timeout' (grouped with
  generic_timeout_error as the same timeout family, so
  features.protocol_daily_signals.tcp_timeout_events picks up these 16
  rows too -- an intended, documented consequence of the fix, not a
  side effect).

  The TCP `BLOCKED` arm (`LIKE '%reset%'`) is confirmed dead code --
  0 matching rows in Kenya's live stg.ooni_tcp_observations, confirmed
  live 2026-08-15 -- and is deliberately left in place in
  int.ooni_experiment_results.sql, unremoved, ahead of this table's join
  (same precedence as before this fix). No evidence it is now safe to
  remove; out of scope for this fix.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'generic_timeout_error' AS tcp_failure,
        'DOWN' AS result_state,
        'tcp.timeout' AS blocking_detail,
        0.45 AS confidence_score,
        'Byte-for-byte unchanged from the pre-fix CASE -- already routed '
        || 'to DOWN/tcp.timeout via the old LIKE \'%timeout%\' arm. '
        || '19,554 live rows.' AS rationale
    ),

    STRUCT(
        'timed_out' AS tcp_failure,
        'DOWN' AS result_state,
        'tcp.timeout' AS blocking_detail,
        0.45 AS confidence_score,
        'TD-80 fix. Real, OONI-originated literal failure string -- '
        || 'verified byte-exact against OONI\'s own raw measurement JSON '
        || '(api.ooni.org, matched by tcp_offset) -- not a CLIO extraction '
        || 'artifact. Grouped into the same timeout family as '
        || 'generic_timeout_error (same result_state, confidence, and '
        || 'blocking_detail label) rather than kept as a separate '
        || '\'tcp.timed_out\' label, since both strings describe the same '
        || 'underlying condition per ooni/spec. 16 live rows, 8 dates '
        || '2023-12-06 to 2025-06-28, whatsapp/telegram only -- previously '
        || 'misclassified UNKNOWN/tcp.timed_out.' AS rationale
    ),

    STRUCT(
        'network_unreachable' AS tcp_failure,
        'UNKNOWN' AS result_state,
        'tcp.network_unreachable' AS blocking_detail,
        0.45 AS confidence_score,
        'Pass-through, unchanged from the pre-fix CASE\'s generic '
        || 'tcp_failure IS NOT NULL -> UNKNOWN fallback. 1,720 live rows.'
            AS rationale
    ),

    STRUCT(
        'connection_refused' AS tcp_failure,
        'UNKNOWN' AS result_state,
        'tcp.connection_refused' AS blocking_detail,
        0.45 AS confidence_score,
        'Pass-through, unchanged from the pre-fix CASE\'s generic '
        || 'tcp_failure IS NOT NULL -> UNKNOWN fallback. 717 live rows.'
            AS rationale
    ),

    STRUCT(
        'host_unreachable' AS tcp_failure,
        'UNKNOWN' AS result_state,
        'tcp.host_unreachable' AS blocking_detail,
        0.45 AS confidence_score,
        'Pass-through, unchanged from the pre-fix CASE\'s generic '
        || 'tcp_failure IS NOT NULL -> UNKNOWN fallback. 222 live rows.'
            AS rationale
    ),

    STRUCT(
        'connection_aborted' AS tcp_failure,
        'UNKNOWN' AS result_state,
        'tcp.connection_aborted' AS blocking_detail,
        0.45 AS confidence_score,
        'Pass-through, unchanged from the pre-fix CASE\'s generic '
        || 'tcp_failure IS NOT NULL -> UNKNOWN fallback. 18 live rows.'
            AS rationale
    ),

    STRUCT(
        'unknown_failure: dial tcp [scrubbed]: connect: cannot allocate memory' AS tcp_failure,
        'UNKNOWN' AS result_state,
        'tcp.unknown_failure: dial tcp [scrubbed]: connect: cannot allocate memory' AS blocking_detail,
        0.45 AS confidence_score,
        'Pass-through, unchanged from the pre-fix CASE\'s generic '
        || 'tcp_failure IS NOT NULL -> UNKNOWN fallback (CONCAT(\'tcp.\', '
        || 'LOWER(tcp_failure))). Only distinct unknown_failure: ... '
        || 'string live in Kenya\'s data as of 2026-08-15. 21 live rows.'
            AS rationale
    )

]);
