/* @bruin
name: marts.fact_ooni_censorship_signals
type: bq.sql
connection: bigquery-default

tags:
  - marts_bq
  - dataset_ooni

description: |
  OONI censorship signal fact.
  Grain: one protocol-level experiment result.

  ADR-0017 (2026-11-22): rows whose measurement OONI's current scoring code
  gives zero accuracy (int.ooni_experiment_results.ooni_zero_accuracy_rule_id
  IS NOT NULL) are left out here. This is the one shared filter point for
  every asset that counts observations through this table
  (features.protocol_daily_signals, marts.fact_protocol_blocking_summary,
  reporting.mart_pressure_attribution_ooni_daily), so their numerators and
  denominators both drop those rows. The rows stay in
  int.ooni_experiment_results, flagged. features.ooni_weekly_signals reads
  int.ooni_experiment_results directly and applies the same filter itself.

depends:
  - int.ooni_experiment_results

materialization:
  type: table
  strategy: create+replace

columns:
  - name: experiment_result_id
    type: string
    checks:
      - name: not_null
      - name: unique
@bruin */

SELECT
  experiment_result_id,
  observation_id,
  measurement_id,
  country,
  probe_asn,
  probe_network_name,
  test_name,
  test_version,
  target,
  protocol,
  observation_target,
  endpoint_ip,
  endpoint_port,
  measurement_start_time,
  measurement_date,
  result_state,
  is_blocking_signal,
  blocking_detail,
  failure_reason,
  confidence_score,
  int_extracted_at
FROM `{{ var.project_id }}.int.ooni_experiment_results`
WHERE ooni_zero_accuracy_rule_id IS NULL;

