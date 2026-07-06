/* @bruin
name: stg.ooni_http_observations
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  HTTP observation table. Grain: one HTTP transaction.

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
    m.measurement_id, '|http|',
    CAST(request_offset AS STRING), '|',
    COALESCE(JSON_VALUE(request_json, '$.request.url'), JSON_VALUE(request_json, '$.url'), ''), '|',
    COALESCE(JSON_VALUE(request_json, '$.response.code'), JSON_VALUE(request_json, '$.response.status_code'), ''), '|',
    COALESCE(JSON_VALUE(request_json, '$.failure'), JSON_VALUE(request_json, '$.response.failure'), '')
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
  'http' AS observation_type,
  COALESCE(JSON_VALUE(request_json, '$.request.url'), JSON_VALUE(request_json, '$.url')) AS url,
  SAFE_CAST(COALESCE(
    JSON_VALUE(request_json, '$.response.code'),
    JSON_VALUE(request_json, '$.response.status_code'),
    JSON_VALUE(request_json, '$.status_code')
  ) AS INT64) AS status_code,
  COALESCE(
    JSON_VALUE(request_json, '$.failure'),
    JSON_VALUE(request_json, '$.response.failure')
  ) AS http_failure,
  COALESCE(
    SAFE_CAST(JSON_VALUE(request_json, '$.response.body_length') AS INT64),
    SAFE_CAST(JSON_VALUE(request_json, '$.body_length') AS INT64),
    LENGTH(JSON_VALUE(request_json, '$.response.body'))
  ) AS body_length,
  request_offset
FROM measurements AS m,
UNNEST(IFNULL(JSON_QUERY_ARRAY(m.raw_test_keys, '$.requests'), ARRAY<STRING>[])) AS request_json
WITH OFFSET AS request_offset;

