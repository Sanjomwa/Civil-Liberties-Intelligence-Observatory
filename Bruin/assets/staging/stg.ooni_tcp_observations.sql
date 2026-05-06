/* @bruin
name: stg.ooni_tcp_observations
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  TCP observation table. Grain: one TCP connect attempt.

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
  FROM `encoded-joy-485413-k5.stg.ooni_measurements`
)

SELECT
  TO_HEX(MD5(CONCAT(
    m.measurement_id, '|tcp|',
    CAST(tcp_offset AS STRING), '|',
    COALESCE(JSON_VALUE(tcp_json, '$.ip'), ''), '|',
    COALESCE(JSON_VALUE(tcp_json, '$.port'), ''), '|',
    COALESCE(JSON_VALUE(tcp_json, '$.status.failure'), JSON_VALUE(tcp_json, '$.failure'), '')
  ))) AS observation_id,
  m.measurement_id,
  m.country,
  m.probe_asn,
  m.probe_network_name,
  m.test_name,
  m.test_version,
  m.input AS target,
  m.measurement_start_time,
  m.measurement_date,
  'tcp' AS observation_type,
  JSON_VALUE(tcp_json, '$.ip') AS ip_address,
  SAFE_CAST(JSON_VALUE(tcp_json, '$.port') AS INT64) AS port,
  SAFE_CAST(JSON_VALUE(tcp_json, '$.status.success') AS BOOL) AS connect_success,
  COALESCE(
    JSON_VALUE(tcp_json, '$.status.failure'),
    JSON_VALUE(tcp_json, '$.failure')
  ) AS tcp_failure,
  tcp_offset
FROM measurements AS m,
UNNEST(IFNULL(JSON_QUERY_ARRAY(m.raw_test_keys, '$.tcp_connect'), ARRAY<STRING>[])) AS tcp_json
WITH OFFSET AS tcp_offset;

