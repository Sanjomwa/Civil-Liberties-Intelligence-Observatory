/* @bruin
tags:
  - marts_bq
name: marts.fact_network_blocking_daily
type: bq.sql
connection: bigquery-default
description: OONI network blocking aggregated at country ASN day grain
depends:
  - int.ooni_signals
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT
  measurement_date,
  'Kenya' AS country,
  CAST(asn AS STRING) AS asn,

  COUNT(*) AS ooni_tests,
  COUNTIF(is_blocked = TRUE) AS blocked_tests,
  SAFE_DIVIDE(COUNTIF(is_blocked = TRUE), COUNT(*)) AS block_rate,

  MAX(CASE WHEN blocking_confidence = 'HIGH' THEN 1 ELSE 0 END) AS high_conf_block_present,

  SUM(CASE WHEN blocking_signal_type = 'NETWORK_BLOCK' THEN 1 ELSE 0 END) AS network_block_signals,

  CURRENT_TIMESTAMP() AS snapshot_at

FROM `encoded-joy-485413-k5.int.ooni_signals`
WHERE country = 'KE'

GROUP BY measurement_date, asn;
