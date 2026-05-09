/* @bruin
tags:
  - marts_bq
  - canonical_dimensions

name: marts.dim_blocking_signals
type: bq.sql
connection: bigquery-default

description: |
  Canonical v5 OONI blocking signal taxonomy.

  Models censorship and interference observations
  across DNS, TCP, TLS, and application layers.

  Scope:
  Kenya observability analysis
  June 2023 → June 2025

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'NETWORK_BLOCK' AS signal_type,
        'IP or port-level connectivity blocking' AS description,
        'NETWORK' AS signal_category,
        5 AS severity_score,
        1.00 AS weight
    ),

    STRUCT(
        'DNS_INCONSISTENCY' AS signal_type,
        'DNS poisoning, tampering, or resolver inconsistency' AS description,
        'DNS' AS signal_category,
        4 AS severity_score,
        0.85 AS weight
    ),

    STRUCT(
        'TCP_RESET' AS signal_type,
        'Unexpected TCP reset or connection interruption' AS description,
        'TCP' AS signal_category,
        4 AS severity_score,
        0.80 AS weight
    ),

    STRUCT(
        'TLS_ANOMALY' AS signal_type,
        'TLS handshake anomaly or certificate interference' AS description,
        'TLS' AS signal_category,
        4 AS severity_score,
        0.80 AS weight
    ),

    STRUCT(
        'APP_LAYER_BLOCK' AS signal_type,
        'Application-specific service interference detected' AS description,
        'APPLICATION' AS signal_category,
        3 AS severity_score,
        0.70 AS weight
    ),

    STRUCT(
        'SERVICE_FAILURE' AS signal_type,
        'Backend or platform-side service failure' AS description,
        'FAILURE' AS signal_category,
        2 AS severity_score,
        0.40 AS weight
    ),

    STRUCT(
        'WEB_FAILURE' AS signal_type,
        'HTTP/Web-layer failure with ambiguous cause' AS description,
        'FAILURE' AS signal_category,
        2 AS severity_score,
        0.50 AS weight
    ),

    STRUCT(
        'UNKNOWN_FAILURE' AS signal_type,
        'Measurement failure with unresolved cause' AS description,
        'UNCERTAIN' AS signal_category,
        1 AS severity_score,
        0.20 AS weight
    ),

    STRUCT(
        'NO_SIGNAL' AS signal_type,
        'No blocking or interference detected' AS description,
        'BASELINE' AS signal_category,
        0 AS severity_score,
        0.00 AS weight
    )

]);