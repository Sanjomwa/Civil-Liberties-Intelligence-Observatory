/* @bruin
name: stg.ooni_tls_observations
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  TLS observation table. Grain: one TLS handshake.

depends:
  - stg.ooni_measurements

materialization:
  type: table
  strategy: create+replace
  # TD-58 (2026-07-06): same treatment as stg.ooni_measurements -- this
  # table inherits the same ad-hoc query shape (filter by test type /
  # date). Costs nothing beyond the rebuild; see that asset for rationale.
  partition_by: measurement_date
  cluster_by:
    - country
    - test_name

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
)

SELECT
  TO_HEX(MD5(CONCAT(
    m.measurement_id, '|tls|',
    CAST(tls_offset AS STRING), '|',
    COALESCE(JSON_VALUE(tls_json, '$.ip'), ''), '|',
    COALESCE(JSON_VALUE(tls_json, '$.port'), ''), '|',
    COALESCE(JSON_VALUE(tls_json, '$.server_name'), JSON_VALUE(tls_json, '$.sni'), ''), '|',
    COALESCE(JSON_VALUE(tls_json, '$.status.failure'), JSON_VALUE(tls_json, '$.failure'), '')
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
  'tls' AS observation_type,
  JSON_VALUE(tls_json, '$.ip') AS ip_address,
  SAFE_CAST(JSON_VALUE(tls_json, '$.port') AS INT64) AS port,
  COALESCE(JSON_VALUE(tls_json, '$.server_name'), JSON_VALUE(tls_json, '$.sni')) AS server_name,
  SAFE_CAST(JSON_VALUE(tls_json, '$.status.success') AS BOOL) AS handshake_success,
  COALESCE(
    JSON_VALUE(tls_json, '$.status.failure'),
    JSON_VALUE(tls_json, '$.failure')
  ) AS tls_failure,
  tls_offset
FROM measurements AS m,
UNNEST(IFNULL(JSON_QUERY_ARRAY(m.raw_test_keys, '$.tls_handshakes'), ARRAY<STRING>[])) AS tls_json
WITH OFFSET AS tls_offset;

