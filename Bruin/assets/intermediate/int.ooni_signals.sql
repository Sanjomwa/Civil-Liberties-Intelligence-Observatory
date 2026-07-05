/* @bruin
name: int.ooni_signals
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni

description: |
  Compatibility signal layer built from observation-level OONI experiment
  results. Grain: one interpreted protocol observation.

depends:
  - int.ooni_experiment_results

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  experiment_result_id AS signal_id,
  observation_id,
  measurement_id,
  country,
  probe_asn,
  probe_network_name,
  test_name,
  test_version,
  target AS input,
  protocol,
  observation_target,
  endpoint_ip,
  endpoint_port,
  measurement_start_time AS start_time,
  measurement_date,
  EXTRACT(YEAR FROM measurement_date) AS year,
  EXTRACT(MONTH FROM measurement_date) AS month,
  EXTRACT(DAY FROM measurement_date) AS day,
  result_state,
  is_blocking_signal AS is_blocked,
  blocking_detail AS blocking_signal_type,
  failure_reason,
  confidence_score,
  int_extracted_at
FROM `{{ var.project_id }}.int.ooni_experiment_results`;

