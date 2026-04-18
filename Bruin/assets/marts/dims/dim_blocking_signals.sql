/* @bruin
name: dim_blocking_signals
type: bq.sql
connection: bigquery-default
description: Canonical taxonomy of OONI blocking signal types used across all observatory facts.
materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([
    STRUCT('APP_LAYER_BLOCK' AS signal_type, 'Application Layer Blocking' AS description, 3 AS severity_score),
    STRUCT('DNS_INCONSISTENCY' AS signal_type, 'DNS tampering or poisoning detected' AS description, 3 AS severity_score),
    STRUCT('NETWORK_BLOCK' AS signal_type, 'IP / Port level blocking detected' AS description, 4 AS severity_score),
    STRUCT('WEB_FAILURE' AS signal_type, 'Service-level web failure (uncertain censorship)' AS description, 2 AS severity_score),
    STRUCT('SERVICE_FAILURE' AS signal_type, 'Backend/service failure (low confidence)' AS description, 1 AS severity_score),
    STRUCT('CENSORSHIP_INDICATOR' AS signal_type, 'Circumvention tool disruption indicator' AS description, 3 AS severity_score),
    STRUCT('NO_SIGNAL' AS signal_type, 'No evidence of blocking' AS description, 0 AS severity_score)
])
