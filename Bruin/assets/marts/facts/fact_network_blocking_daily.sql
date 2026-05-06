/* @bruin
name: marts.fact_network_blocking_daily
type: bq.sql
connection: bigquery-default

tags:
  - marts_bq
  - dataset_ooni

description: |
  Daily OONI network blocking aggregate at country x ASN x protocol grain.

depends:
  - marts.fact_ooni_censorship_signals

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  measurement_date,
  country,
  CAST(probe_asn AS STRING) AS asn,
  protocol,
  COUNT(DISTINCT measurement_id) AS measurement_count,
  COUNT(*) AS observation_count,
  COUNTIF(result_state = 'BLOCKED') AS blocked_events,
  COUNTIF(result_state = 'OK') AS ok_events,
  COUNTIF(result_state = 'DOWN') AS down_events,
  COUNTIF(result_state = 'UNKNOWN') AS unknown_events,
  SAFE_DIVIDE(COUNTIF(result_state = 'BLOCKED'), COUNT(*)) AS blocking_rate,
  AVG(confidence_score) AS avg_confidence_score,
  COUNTIF(blocking_detail = 'dns.bogon') AS dns_bogon_events,
  COUNTIF(blocking_detail = 'tcp.rst') AS tcp_reset_events,
  COUNTIF(blocking_detail = 'tls.rst') AS tls_reset_events,
  COUNTIF(blocking_detail = 'http.451') AS http_451_events,
  CURRENT_TIMESTAMP() AS snapshot_at
FROM `encoded-joy-485413-k5.marts.fact_ooni_censorship_signals`
GROUP BY
  measurement_date,
  country,
  asn,
  protocol;

