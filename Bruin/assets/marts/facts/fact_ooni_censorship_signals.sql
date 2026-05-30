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
FROM `{{ var.project_id }}.int.ooni_experiment_results`;

