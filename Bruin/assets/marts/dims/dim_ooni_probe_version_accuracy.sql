/* @bruin
tags:
  - marts_bq
  - canonical_dimensions
  - ooni_verdict_phase_2

name: marts.dim_ooni_probe_version_accuracy
type: bq.sql
connection: bigquery-default

description: |
  TD-87 Phase 2 (2026-08-15). Grounds a real, earlier-measured finding: an
  audit found 80 of 361 BLOCKED TLS rows and 99 of 100 residual `ssl_*`
  UNKNOWN rows carry OONI's own `scores.accuracy = 0.0` in OONI's live API
  response -- meaning OONI's own backend discarded those measurements
  before scoring, on known-bad-probe-version grounds, before any
  classification was even attempted.

  Built via method (1) of this phase's two options (preferred): OONI's own
  published discard rule was found directly, not reinvented or derived
  empirically. Source: ooni/pipeline, af/fastpath/fastpath/core.py,
  score_signal(), commit 09603b720a6303cd017406415b845a2a51649959 (the
  most recent commit to touch that file as of 2026-08-15, fetched live
  from github.com/ooni/pipeline/blob/master/af/fastpath/fastpath/core.py):

      tv = g_or(msm, "test_version", "0.0.0")
      if parse_version(tv) < parse_version("0.2.2"):
          if start_time is None or start_time >= datetime(2022, 10, 19):
              scores["accuracy"] = 0.0

  citing github.com/ooni/probe/issues/2344 in its own comment.

  CORRECTIONS made to this phase's original design before encoding it,
  per this project's "verify before writing the diff" discipline:

  1. **This rule is Signal-specific only.** Grepped every score_* function
     in fastpath/core.py for parse_version usage -- it appears exactly
     once, inside score_signal(). No analogous published version-based
     discard rule exists for whatsapp/telegram/psiphon/tor/dnscheck/
     web_connectivity. This table is NOT a general "known-bad-version"
     list across all OONI tests -- it is Signal's real rule plus a
     scored/reviewed baseline for the other 5 real test types actually in
     CLIO's corpus (see below), each explicitly marked
     is_known_bad_version = FALSE because no published discard condition
     was found for them, not because they were positively verified clean.

  2. **The real rule is compound (version AND date-gated), not a flat
     version cutoff** -- but CLIO's entire Kenya OONI window (2023-06-01
     to 2025-06-30) is uniformly after the 2022-10-19 threshold, so for
     every row CLIO actually has, the date condition is always satisfied
     and the rule collapses to a flat cutoff: test_version < 0.2.2 always
     discards. This simplification is safe ONLY within CLIO's current
     data window -- flagged here so it is not silently assumed to
     generalize if CLIO's OONI ingestion window is ever extended
     backward past 2022-10-19.

  3. **test_version values COLLIDE across test_name families** -- e.g.
     '0.2.0' exists for both signal (8,078 live rows) and telegram (8,125
     live rows), independently versioned by each nettest's own upstream
     repo. A bare test_version join key would have incorrectly flagged
     telegram's unrelated 0.2.0 rows as bad-version discards alongside
     signal's real ones -- caught by checking test_version's cross-test
     distribution live before writing the join. The join key is therefore
     (test_name, test_version), a compound key, not test_version alone.

  4. **No engine_version field exists anywhere in CLIO's raw JSON**
     (checked live, always NULL) -- only test_version (used here) and
     software_version (the OONI Probe app version, a different concept,
     not used here) exist.

  Seeded with every (test_name, test_version) combination observed live
  in Kenya's corpus as of 2026-08-15 (20 combinations across the 6 real
  test types) so the LEFT JOIN in int.ooni_measurement_verdicts.sql can
  distinguish three real states: SCORED (matched, reviewed, not known-bad),
  DISCARDED_BAD_PROBE_VERSION (matched, known-bad), and UNKNOWN_VERSION (no
  match at all -- a test_version this table has never seen, including any
  future OONI probe release, or any web_connectivity/facebook_messenger
  row, since neither test type has any live test_version to seed from).
  An unmatched combination deliberately defaults to UNKNOWN_VERSION, never
  silently to SCORED -- the same default-low-until-reviewed discipline
  already established by marts.dim_tls_failure_evidence /
  marts.dim_tcp_failure_evidence.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    -- signal: TWO separate, sourced discard rules at THIS table's grain --
    -- do not merge them. 0.2.0 (below) is the original, 2026-08-15 rule,
    -- a genuine unconditional version-wide discard (OONI's own published
    -- rule, confirmed version-wide by OONI itself, unlike 0.2.2 below).
    -- 0.2.2's own TD-102 defect (the dead api.directory.signal.org
    -- backend target) is real but, per a second review pass on
    -- 2026-08-22, is NOT version-wide in practice -- only
    -- signal_backend_status='blocked' rows are actually poisoned by it
    -- (~19% of 0.2.2, confirmed below); the other ~81% are genuine,
    -- OONI-agreed 'ok' measurements this table's flat per-version grain
    -- cannot express. That rule is therefore expressed as an inline,
    -- signal_backend_status-gated predicate in
    -- int.ooni_measurement_verdicts_candidate.sql instead -- see that
    -- file's own comment for the full mechanism and the rescoping
    -- history. This row stays FALSE.
    STRUCT('signal' AS test_name, '0.2.0' AS test_version, TRUE AS is_known_bad_version,
      'ooni/pipeline af/fastpath/fastpath/core.py score_signal(), commit 09603b720a6303cd017406415b845a2a51649959 (ooni/probe#2344): test_version < 0.2.2 discarded for measurements on/after 2022-10-19 -- CLIO Kenya window (2023-06-01+) is always past that date, so this collapses to an unconditional discard for this version. 8,078 live rows.' AS sourced_from),
    -- TD-102 (2026-08-22, characterization + build sessions), RESCOPED
    -- (2026-08-22, second build session): this row was briefly TRUE
    -- (version-wide discard) in the first TD-102 build session, then
    -- reverted back to FALSE here once that session's own post-fix
    -- validation found the "poisons every 0.2.2 measurement
    -- unconditionally" premise did not hold against the real population
    -- -- only 415/2,200 (18.9%) of 0.2.2 rows actually show
    -- signal_backend_status='blocked'; the other 1,785 (81.1%) are
    -- 'ok' and independently OONI-agreed 'ok' in a live-API matched-pair
    -- sample (16/16). The underlying defect (a dead
    -- https://api.directory.signal.org/ backend target, tested
    -- unconditionally by 0.2.2, removed in 0.2.3 -- confirmed by
    -- probe-cli source diff and live OONI API data) is real, but does
    -- not poison the whole measurement every time, contrary to the
    -- original source-diff-based reading of Signal's client failure
    -- logic. Correctly scoped rule now lives as an inline
    -- signal_backend_status='blocked' predicate in
    -- int.ooni_measurement_verdicts_candidate.sql's probe_accuracy_gate
    -- CASE (~415 rows), NOT here -- this table's flat per-version grain
    -- cannot express a per-measurement-field condition. See
    -- reports.md's 2026-08-22 TD-102 session entries (characterization,
    -- first build, rescoping build) for the full account.
    STRUCT('signal', '0.2.2', FALSE,
      'TD-102 (2026-08-22, rescoped): a dead Signal backend target (https://api.directory.signal.org/), tested unconditionally by 0.2.2 and removed in 0.2.3, is real but only actually poisons signal_backend_status=blocked measurements (~415/2,200, 18.9%), not the whole version -- the other 1,785 ok-status rows are genuine and OONI-agreed. This row is deliberately FALSE; the narrower, correctly-scoped discard is an inline predicate in int.ooni_measurement_verdicts_candidate.sql keyed on signal_backend_status, since this table has no per-measurement-field grain to express that condition. SEPARATE from the 0.2.0 rule above (a genuine, OONI-confirmed version-wide rule) and from 0.2.3s own, different, date-gated defect. See reports.md 2026-08-22 TD-102 entries.'),
    STRUCT('signal', '0.2.3', FALSE, 'Above the 0.2.2 cutoff -- not discarded by THIS rule (the 0.2.0 version cutoff). See int.ooni_measurement_verdicts_candidate.sql for a SEPARATE, date-gated TD-102 (2026-08-22) discard condition that applies to a subset of 0.2.3s own rows (measurement_start_time > 2023-11-06T16:00:00) -- expressed inline there, not here, since it needs a date grain this table does not have. 6,844 live rows.' AS sourced_from),
    STRUCT('signal', '0.2.4', FALSE, 'Above the 0.2.2 cutoff -- not discarded by the sourced rule. 1,146 live rows.'),
    STRUCT('signal', '0.2.5', FALSE, 'Above the 0.2.2 cutoff -- not discarded by the sourced rule. 32,186 live rows.'),

    -- The other 5 real test types: no published version-based discard
    -- rule was found for any of them (confirmed by grepping every
    -- score_* function in fastpath/core.py for parse_version usage --
    -- signal is the only hit). Seeded as SCORED (not known-bad) so the
    -- LEFT JOIN resolves to a real match rather than UNKNOWN_VERSION,
    -- but this is "no rule found", not "positively verified clean".
    STRUCT('whatsapp', '0.7.0', FALSE, 'No published version-based discard rule found for whatsapp (score_measurement_whatsapp has no parse_version check). 6 live rows.'),
    STRUCT('whatsapp', '0.9.0', FALSE, 'No published version-based discard rule found for whatsapp. 8,098 live rows.'),
    STRUCT('whatsapp', '0.11.0', FALSE, 'No published version-based discard rule found for whatsapp. 43,290 live rows.'),

    STRUCT('telegram', '0.1.0', FALSE, 'No published version-based discard rule found for telegram (score_measurement_telegram has no parse_version check). 7 live rows.'),
    STRUCT('telegram', '0.2.0', FALSE, 'No published version-based discard rule found for telegram. Note: this test_version string collides with signal 0.2.0 -- confirmed unrelated, independently versioned nettest, correctly isolated by the (test_name, test_version) compound key. 8,125 live rows.'),
    STRUCT('telegram', '0.3.0', FALSE, 'No published version-based discard rule found for telegram. 7,796 live rows.'),
    STRUCT('telegram', '0.3.1', FALSE, 'No published version-based discard rule found for telegram. 35,022 live rows.'),

    STRUCT('psiphon', '0.4.0', FALSE, 'No published version-based discard rule found for psiphon (score_psiphon has no parse_version check). 7 live rows.'),
    STRUCT('psiphon', '0.5.0', FALSE, 'No published version-based discard rule found for psiphon. 4 live rows.'),
    STRUCT('psiphon', '0.6.0', FALSE, 'No published version-based discard rule found for psiphon. 50,662 live rows.'),

    STRUCT('dnscheck', '0.9.0', FALSE, 'No published version-based discard rule found for dnscheck (no dedicated score_dnscheck function exists in fastpath/core.py at all). 38,370 live rows.'),
    STRUCT('dnscheck', '0.9.2', FALSE, 'No published version-based discard rule found for dnscheck. 1,066,660 live rows.'),

    STRUCT('tor', '0.1.0', FALSE, 'No published version-based discard rule found for tor (score_tor/score_vanilla_tor have no parse_version check). 7 live rows.'),
    STRUCT('tor', '0.3.0', FALSE, 'No published version-based discard rule found for tor. 4 live rows.'),
    STRUCT('tor', '0.4.0', FALSE, 'No published version-based discard rule found for tor. 46,336 live rows.')

    -- web_connectivity and facebook_messenger: deliberately NOT seeded --
    -- 0 live rows in CLIO's corpus, so there is no real test_version to
    -- calibrate against. Any future row of either test type will
    -- correctly resolve to UNKNOWN_VERSION via the unmatched LEFT JOIN,
    -- not silently SCORED, until this table is updated with real data.

]);
