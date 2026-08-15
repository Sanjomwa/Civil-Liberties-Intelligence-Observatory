/* @bruin
name: int.ooni_measurement_verdicts_confirmed_guard
type: bq.sql
connection: bigquery-default

tags:
  - intermediate
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  TD-87 Phase 2 (2026-08-15) guard, layer 2 of 3 (see
  int.ooni_measurement_verdicts.sql's header for layer 1, the structural
  CTE isolation, and tests/test_ooni_confirmed_guard.py for layer 3, the
  static source-text check). Fails loudly if OONI's CONFIRMED verdict
  ever appears on a row where test_name != 'web_connectivity' -- OONI's
  CONFIRMED state (fingerprint-matched block pages / censorship-
  associated DNS answers) is structurally possible only for
  web_connectivity, never for Signal, WhatsApp, Telegram, Tor, or any
  other test.

  fingerprint_match_id is always NULL this phase (Phase 5 builds real
  fingerprint matching), so this check is trivially, permanently 0-row
  today -- it is insurance for Phase 5, not a check with teeth yet.

  DEVIATION FROM THE ACLED PRECEDENT, DELIBERATE, DOCUMENTED HERE: this
  asset is modeled on intelligence.acled_pressure_regimes_precondition_check's
  ERROR()-on-violation query shape, but is wired in the OPPOSITE
  direction from that precedent. ACLED's guard depends on a genuinely
  separate UPSTREAM asset (features.acled_pressure_signals) and is
  itself listed in intelligence.acled_pressure_regimes's own `depends:`
  -- a real pre-write precondition check on an input, preventing a MERGE
  from ever running against a bad input (needed there because that
  asset persists incrementally; a bad MERGE would corrupt state that
  outlives the run).

  That shape does not transfer here: the condition being checked
  (ooni_verdict = 'CONFIRMED') is a column computed BY
  int.ooni_measurement_verdicts itself -- there is no separate upstream
  table that carries it to pre-check. Wiring this guard into
  int.ooni_measurement_verdicts's own `depends:` (guard upstream of
  verdicts) while also having the guard query verdicts' own output
  would be a literal circular DAG edge (verdicts -> guard -> verdicts),
  which Bruin cannot represent. Instead this guard `depends:` ON
  int.ooni_measurement_verdicts (downstream of it) and runs immediately
  after it materializes -- functionally the same insurance ACLED's
  guard provides (fail loudly, block anything depending on this guard),
  just enforced immediately-after rather than gated-before. This is
  safe specifically because int.ooni_measurement_verdicts is
  `create+replace` (a full overwrite every run), not an incrementally
  merged/stateful table the way ACLED's regime engine is -- there is no
  equivalent risk of a bad row persisting forever the way an unguarded
  MERGE could. See reports.md's TD-87 Phase 1/2 session entry for the
  full reasoning.

depends:
  - int.ooni_measurement_verdicts
@bruin */

SELECT ERROR(
  FORMAT(
    'TD-87 Phase 2 CONFIRMED guard violation: int.ooni_measurement_verdicts has %d row(s) with ooni_verdict = CONFIRMED where test_name != web_connectivity. OONI CONFIRMED is structurally possible only for web_connectivity (fingerprint-matched block pages / censorship-associated DNS). This means fingerprint_match_id leaked outside the web_connectivity-filtered wc_confirmed CTE -- see that asset header before touching Phase 5 fingerprint-matching logic.',
    bad_count
  )
)
FROM (
  SELECT COUNT(*) AS bad_count
  FROM `{{ var.project_id }}.int.ooni_measurement_verdicts`
  WHERE ooni_verdict = 'CONFIRMED'
    AND test_name != 'web_connectivity'
)
WHERE bad_count > 0
