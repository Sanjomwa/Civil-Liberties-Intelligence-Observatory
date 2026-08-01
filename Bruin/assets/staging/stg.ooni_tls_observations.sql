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
  -- TD-72 (2026-08-01): `$.status.success`/`$.status.failure` are OONI's
  -- TCP-connect data format (df-005-tcpconnect) fields -- genuinely present
  -- in these same four tests' own `tcp_connect[]` arrays (confirmed live:
  -- stg.ooni_tcp_observations' identical JSONPath is non-NULL for 100% of
  -- rows there), but never populated on a TLS handshake object, which has
  -- no nested `status` at all. handshake_success read from that path was
  -- NULL for 100% of this table's rows, always -- a copy-paste of the TCP
  -- extractor onto the wrong shape, not a real signal. OONI's own canonical
  -- TLS model (probe-cli's ArchivalTLSOrQUICHandshakeResult, oonipipeline's
  -- measurement_to_tls_observation) has no boolean success field at all --
  -- only `failure` (null = success). handshake_success is now derived the
  -- same way: no failure string present. Certificate trust is a separate,
  -- deliberately orthogonal concept (see peer_certificate_sha256s below and
  -- int.ooni_experiment_results.presents_known_signal_root_ca) -- a
  -- successful handshake and a trusted certificate are two different
  -- claims, and this column only ever asserts the former. Computed via the
  -- same COALESCE as tls_failure below (not by referencing that alias) so
  -- each column stands on its own; the two are consistent by construction
  -- (handshake_success = tls_failure IS NULL).
  COALESCE(
    JSON_VALUE(tls_json, '$.status.failure'),
    JSON_VALUE(tls_json, '$.failure')
  ) IS NULL AS handshake_success,
  COALESCE(
    JSON_VALUE(tls_json, '$.status.failure'),
    JSON_VALUE(tls_json, '$.failure')
  ) AS tls_failure,
  tls_offset,
  -- TD-69 (2026-08-01): SHA-256 fingerprints of every certificate presented
  -- during this handshake, in DER form (base64-decoded, matching how OONI's
  -- own oonipipeline computes cert identity in oonidata.datautils). Consumed
  -- by int.ooni_experiment_results to recognize Signal's own rotated root CA
  -- and stop misclassifying it as interception. Empty array if the probe
  -- recorded no certificates (failed before the peer sent any, or a non-TLS
  -- failure).
  ARRAY(
    SELECT TO_HEX(SHA256(cert_der))
    FROM UNNEST(IFNULL(JSON_QUERY_ARRAY(tls_json, '$.peer_certificates'), ARRAY<STRING>[])) AS cert_json,
    UNNEST([SAFE.FROM_BASE64(JSON_VALUE(cert_json, '$.data'))]) AS cert_der
    WHERE cert_der IS NOT NULL
  ) AS peer_certificate_sha256s
FROM measurements AS m,
UNNEST(IFNULL(JSON_QUERY_ARRAY(m.raw_test_keys, '$.tls_handshakes'), ARRAY<STRING>[])) AS tls_json
WITH OFFSET AS tls_offset;

