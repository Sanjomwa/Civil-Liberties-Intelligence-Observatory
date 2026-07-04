/* @bruin
name: intelligence.acled_pressure_regimes_precondition_check
type: bq.sql
connection: bigquery-default
tags:
  - intelligence
  - intelligence_bq
  - dataset_acled
  - acled_intelligence_phase_1

description: |
  TD-04 runtime precondition guard for intelligence.acled_pressure_regimes.

  Enforces the EXECUTION CONTRACT documented in that asset's header:
  exactly one country x one new week x one execution. Runs as an upstream
  Bruin task so a violation fails THIS task and Bruin's dependency
  resolution prevents intelligence.acled_pressure_regimes from executing
  at all -- no MERGE is attempted, so no persisted state can be corrupted.

  Mirrors the exact country/target_week filter used in CTE-02 of
  intelligence.acled_pressure_regimes.sql. If that filter logic ever
  changes, this guard must change with it.

depends:
  - features.acled_pressure_signals
@bruin */

SELECT ERROR(
  FORMAT(
    'TD-04 precondition violation: intelligence.acled_pressure_regimes requires exactly one new week per execution for country %s. Found %d distinct week_start_date value(s) for target_week=%s. Multi-week batches must run as sequential single-week invocations (see backfill_acled_pressure_regimes.py), not a single execution.',
    '{{ var.country }}',
    week_count,
    IF('{{ var.target_week }}' = '', '<unset>', '{{ var.target_week }}')
  )
)
FROM (
  SELECT COUNT(DISTINCT week_start_date) AS week_count
  FROM `{{ var.project_id }}.features.acled_pressure_signals`
  WHERE country = '{{ var.country }}'
    AND (
          '{{ var.target_week }}' = ''
          OR week_start_date = SAFE.PARSE_DATE('%Y-%m-%d', '{{ var.target_week }}')
        )
)
WHERE week_count <> 1
