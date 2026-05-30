/* @bruin
name: int.ooni_experiment_results
type: bq.sql
connection: bigquery-default

tags:
  - int_bq
  - dataset_ooni

description: |
  OONI experiment results derived from protocol observations.
  Grain: one interpreted result per protocol observation.

depends:
  - stg.ooni_dns_observations
  - stg.ooni_tcp_observations
  - stg.ooni_tls_observations
  - stg.ooni_http_observations

materialization:
  type: table
  strategy: create+replace

columns:
  - name: experiment_result_id
    type: string
    checks:
      - name: not_null
      - name: unique
  - name: result_state
    type: string
    checks:
      - name: accepted_values
        value: [BLOCKED, OK, DOWN, UNKNOWN]
@bruin */

WITH dns AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'dns' AS protocol,
    hostname AS observation_target,
    answer AS endpoint_ip,
    CAST(NULL AS INT64) AS endpoint_port,
    dns_failure AS failure_reason,
    CASE
      WHEN REGEXP_CONTAINS(LOWER(COALESCE(answer, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$|::1$|fc|fd|fe80)') THEN 'BLOCKED'
      WHEN LOWER(COALESCE(dns_failure, '')) IN ('nxdomain', 'dns_nxdomain_error') THEN 'DOWN'
      WHEN dns_failure IS NOT NULL THEN 'UNKNOWN'
      WHEN answer IS NOT NULL THEN 'OK'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN REGEXP_CONTAINS(LOWER(COALESCE(answer, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$|::1$|fc|fd|fe80)') THEN 'dns.bogon'
      WHEN LOWER(COALESCE(dns_failure, '')) IN ('nxdomain', 'dns_nxdomain_error') THEN 'dns.nxdomain'
      WHEN dns_failure IS NOT NULL THEN CONCAT('dns.', LOWER(dns_failure))
      WHEN answer IS NOT NULL THEN 'dns.ok'
      ELSE 'dns.no_answer'
    END AS blocking_detail,
    CASE
      WHEN REGEXP_CONTAINS(LOWER(COALESCE(answer, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$|::1$|fc|fd|fe80)') THEN 0.90
      WHEN answer IS NOT NULL THEN 0.70
      ELSE 0.40
    END AS confidence_score
  FROM `{{ var.project_id }}.stg.ooni_dns_observations`
),

tcp AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'tcp' AS protocol,
    ip_address AS observation_target,
    ip_address AS endpoint_ip,
    port AS endpoint_port,
    tcp_failure AS failure_reason,
    CASE
      WHEN connect_success IS TRUE THEN 'OK'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 'BLOCKED'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%timeout%' THEN 'DOWN'
      WHEN tcp_failure IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN connect_success IS TRUE THEN 'tcp.ok'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 'tcp.rst'
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%timeout%' THEN 'tcp.timeout'
      WHEN tcp_failure IS NOT NULL THEN CONCAT('tcp.', LOWER(tcp_failure))
      ELSE 'tcp.unknown'
    END AS blocking_detail,
    CASE
      WHEN LOWER(COALESCE(tcp_failure, '')) LIKE '%reset%' THEN 0.80
      WHEN connect_success IS TRUE THEN 0.70
      ELSE 0.45
    END AS confidence_score
  FROM `{{ var.project_id }}.stg.ooni_tcp_observations`
),

tls AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'tls' AS protocol,
    COALESCE(server_name, ip_address) AS observation_target,
    ip_address AS endpoint_ip,
    port AS endpoint_port,
    tls_failure AS failure_reason,
    CASE
      WHEN handshake_success IS TRUE THEN 'OK'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%reset%' THEN 'BLOCKED'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%timeout%' THEN 'DOWN'
      WHEN handshake_success IS FALSE THEN 'BLOCKED'
      WHEN tls_failure IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN handshake_success IS TRUE THEN 'tls.ok'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%reset%' THEN 'tls.rst'
      WHEN LOWER(COALESCE(tls_failure, '')) LIKE '%timeout%' THEN 'tls.timeout'
      WHEN tls_failure IS NOT NULL THEN CONCAT('tls.', LOWER(tls_failure))
      ELSE 'tls.unknown'
    END AS blocking_detail,
    CASE
      WHEN handshake_success IS FALSE THEN 0.75
      WHEN handshake_success IS TRUE THEN 0.70
      ELSE 0.45
    END AS confidence_score
  FROM `{{ var.project_id }}.stg.ooni_tls_observations`
),

http AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    test_version,
    target,
    measurement_start_time,
    measurement_date,
    'http' AS protocol,
    COALESCE(url, target) AS observation_target,
    CAST(NULL AS STRING) AS endpoint_ip,
    CAST(NULL AS INT64) AS endpoint_port,
    http_failure AS failure_reason,
    CASE
      WHEN status_code = 451 THEN 'BLOCKED'
      WHEN status_code BETWEEN 200 AND 399 THEN 'OK'
      WHEN http_failure IS NOT NULL THEN 'UNKNOWN'
      WHEN status_code IS NOT NULL THEN 'UNKNOWN'
      ELSE 'UNKNOWN'
    END AS result_state,
    CASE
      WHEN status_code = 451 THEN 'http.451'
      WHEN status_code BETWEEN 200 AND 399 THEN 'http.ok'
      WHEN http_failure IS NOT NULL THEN CONCAT('http.', LOWER(http_failure))
      WHEN status_code IS NOT NULL THEN CONCAT('http.status_', CAST(status_code AS STRING))
      ELSE 'http.unknown'
    END AS blocking_detail,
    CASE
      WHEN status_code = 451 THEN 0.90
      WHEN status_code BETWEEN 200 AND 399 THEN 0.70
      ELSE 0.40
    END AS confidence_score
  FROM `{{ var.project_id }}.stg.ooni_http_observations`
),

unioned AS (
  SELECT * FROM dns
  UNION ALL
  SELECT * FROM tcp
  UNION ALL
  SELECT * FROM tls
  UNION ALL
  SELECT * FROM http
)

SELECT
  TO_HEX(MD5(CONCAT(observation_id, '|', result_state, '|', blocking_detail))) AS experiment_result_id,
  *,
  result_state = 'BLOCKED' AS is_blocking_signal,
  CURRENT_TIMESTAMP() AS int_extracted_at
FROM unioned;

