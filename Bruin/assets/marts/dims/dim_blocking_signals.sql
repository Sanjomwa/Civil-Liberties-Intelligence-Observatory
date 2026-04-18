/* @bruin
tags:
  - marts_bq
name: marts.dim_blocking_signals
type: bq.sql
connection: bigquery-default

description: |
  Canonical taxonomy of OONI blocking signals used across all observatory facts.
  Standardizes INT-level signal types into analytical categories for cross-source modeling.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT * FROM UNNEST([

    STRUCT(
        'NETWORK_BLOCK' AS signal_type,
        'Network-level IP/port blocking detected' AS description,
        'NETWORK' AS signal_category,
        4 AS severity_score,
        1.0 AS weight
    ),

    STRUCT(
        'DNS_BLOCK' AS signal_type,
        'DNS tampering, poisoning, or resolution inconsistency' AS description,
        'DNS' AS signal_category,
        3 AS severity_score,
        0.8 AS weight
    ),

    STRUCT(
        'APP_BLOCK' AS signal_type,
        'Application-level blocking (WhatsApp, Telegram, Signal)' AS description,
        'APPLICATION' AS signal_category,
        3 AS severity_score,
        0.7 AS weight
    ),

    STRUCT(
        'SERVICE_FAILURE' AS signal_type,
        'Backend or service-level failure (uncertain censorship)' AS description,
        'FAILURE' AS signal_category,
        2 AS severity_score,
        0.4 AS weight
    ),

    STRUCT(
        'WEB_FAILURE' AS signal_type,
        'Web access failure with ambiguous cause' AS description,
        'FAILURE' AS signal_category,
        2 AS severity_score,
        0.5 AS weight
    ),

    STRUCT(
        'CENSORSHIP_INDICATOR' AS signal_type,
        'Circumvention tool disruption or indirect censorship signal' AS description,
        'CIRCUMVENTION' AS signal_category,
        3 AS severity_score,
        0.6 AS weight
    ),

    STRUCT(
        'NO_SIGNAL' AS signal_type,
        'No evidence of blocking detected' AS description,
        'CLEAN' AS signal_category,
        0 AS severity_score,
        0.0 AS weight
    )

]);