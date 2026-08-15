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
  int.ooni_measurement_verdicts_candidate.sql's header for layer 1, the
  structural CTE isolation, and tests/test_ooni_confirmed_guard.py for
  layer 3, the static source-text check). Fails loudly if OONI's
  CONFIRMED verdict ever appears on a row where
  test_name != 'web_connectivity' -- OONI's CONFIRMED state
  (fingerprint-matched block pages / censorship-associated DNS answers)
  is structurally possible only for web_connectivity, never for Signal,
  WhatsApp, Telegram, Tor, or any other test.

  fingerprint_match_id is always NULL this phase (Phase 5 builds real
  fingerprint matching), so this check is trivially, permanently 0-row
  today -- it is insurance for Phase 5, not a check with teeth yet.

  TD-91 (2026-08-16): RESOLVED the deviation this file previously
  documented from the ACLED precedent. Originally this guard depended on
  (and checked) the already-published int.ooni_measurement_verdicts --
  after that table had already materialized, meaning a violation would
  leave a bad table live and queryable for the whole window between the
  bad run and a fixed rerun (create+replace does not roll back). That
  gap is now closed via a candidate/publish split (see
  int.ooni_measurement_verdicts_candidate.sql's header for the cost
  investigation that confirmed this was cheap -- 222 MiB, not the 63 GiB
  raw-JSON pipeline shape this project's 2026-07-06 cost audit actually
  worried about): this guard now depends on and checks the CANDIDATE
  table, and int.ooni_measurement_verdicts itself is a trivial
  `SELECT * FROM candidate` that only runs (via its own `depends:`) after
  this guard passes. This now genuinely matches ACLED's own
  precondition-check shape: a real, separate upstream table
  (int.ooni_measurement_verdicts_candidate) is checked BEFORE the
  published asset ever materializes, not after.

depends:
  - int.ooni_measurement_verdicts_candidate
@bruin */

SELECT ERROR(
  FORMAT(
    'TD-87 Phase 2 CONFIRMED guard violation: int.ooni_measurement_verdicts_candidate has %d row(s) with ooni_verdict = CONFIRMED where test_name != web_connectivity. OONI CONFIRMED is structurally possible only for web_connectivity (fingerprint-matched block pages / censorship-associated DNS). This means fingerprint_match_id leaked outside the web_connectivity-filtered wc_confirmed CTE -- see that asset header before touching Phase 5 fingerprint-matching logic. The published int.ooni_measurement_verdicts will NOT be refreshed until this passes (TD-91 candidate/publish split).',
    bad_count
  )
)
FROM (
  SELECT COUNT(*) AS bad_count
  FROM `{{ var.project_id }}.int.ooni_measurement_verdicts_candidate`
  WHERE ooni_verdict = 'CONFIRMED'
    AND test_name != 'web_connectivity'
)
WHERE bad_count > 0
