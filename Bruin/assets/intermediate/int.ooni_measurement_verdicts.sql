/* @bruin
name: int.ooni_measurement_verdicts
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni
  - ooni_verdict_phase_2

description: |
  TD-91 (2026-08-16): the published table. A trivial passthrough of
  int.ooni_measurement_verdicts_candidate -- all real computation, every
  column, and full documentation live there now. This file's own
  `depends:` on the confirmed_guard is the actual write-order guarantee:
  Bruin's DAG will not run this SELECT until
  int.ooni_measurement_verdicts_confirmed_guard has already run and
  passed against the candidate, so a CONFIRMED-outside-web_connectivity
  violation blocks this table from ever refreshing -- the previously-
  published (good) data stays live and queryable instead of being
  silently replaced by a violating one.

  Any future consumer of OONI verdict data should query THIS table, not
  the candidate -- the candidate is allowed to (briefly, only ever within
  a single failed/guard-blocked run) contain unvalidated data; this one
  is not.

depends:
  - int.ooni_measurement_verdicts_candidate
  - int.ooni_measurement_verdicts_confirmed_guard

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

SELECT *
FROM `{{ var.project_id }}.int.ooni_measurement_verdicts_candidate`;
