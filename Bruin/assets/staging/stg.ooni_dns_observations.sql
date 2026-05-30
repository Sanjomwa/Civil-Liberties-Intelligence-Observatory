/* @bruin
name: stg.ooni_dns_observations
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  DNS observation table. Grain: one DNS query answer or one DNS query failure.

depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace

columns:
  - name: observation_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: measurement_id
    type: string
    checks:
      - name: not_null
@bruin */

WITH measurements AS (
  SELECT *
  FROM `{{ var.project_id }}.stg.ooni_measurements`
),

queries AS (
  SELECT
    m.measurement_id,
    m.country,
    m.probe_asn,
    m.probe_network_name,
    m.test_name,
    m.test_version,
    m.input AS target,
    m.measurement_start_time,
    m.measurement_date,
    query_offset,
    query_json,
    JSON_VALUE(query_json, '$.hostname') AS hostname,
    JSON_VALUE(query_json, '$.query_type') AS query_type,
    JSON_VALUE(query_json, '$.engine') AS resolver_engine,
    JSON_VALUE(query_json, '$.failure') AS dns_failure
  FROM measurements AS m,
  UNNEST(IFNULL(JSON_QUERY_ARRAY(m.raw_test_keys, '$.queries'), ARRAY<STRING>[])) AS query_json
  WITH OFFSET AS query_offset
),

answers AS (
  SELECT
    q.*,
    answer_offset,
    answer_json,
    COALESCE(
      JSON_VALUE(answer_json, '$.ipv4'),
      JSON_VALUE(answer_json, '$.ipv6'),
      JSON_VALUE(answer_json, '$.answer')
    ) AS answer,
    JSON_VALUE(answer_json, '$.answer_type') AS answer_type,
    JSON_VALUE(answer_json, '$.hostname') AS answer_hostname
  FROM queries AS q
  LEFT JOIN UNNEST(
    IFNULL(JSON_QUERY_ARRAY(q.query_json, '$.answers'), [CAST(NULL AS STRING)])
  ) AS answer_json
  WITH OFFSET AS answer_offset
  ON TRUE
)

SELECT
  TO_HEX(MD5(CONCAT(
    measurement_id, '|dns|',
    CAST(query_offset AS STRING), '|',
    CAST(IFNULL(answer_offset, -1) AS STRING), '|',
    COALESCE(answer, ''), '|',
    COALESCE(dns_failure, '')
  ))) AS observation_id,
  measurement_id,
  country,
  probe_asn,
  probe_network_name,
  test_name,
  test_version,
  target,
  measurement_start_time,
  measurement_date,
  'dns' AS observation_type,
  hostname,
  query_type,
  resolver_engine,
  answer,
  answer_type,
  answer_hostname,
  dns_failure,
  query_offset,
  answer_offset
FROM answers;

