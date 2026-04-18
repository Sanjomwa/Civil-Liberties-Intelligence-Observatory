/* @bruin
name: dim_blocking_signals
type: bq.sql
connection: bigquery-default
description: Canonical blocking signal taxonomy across OONI tests.

materialization:
  type: table
  strategy: create+replace
@bruin */

SELECT *
FROM UNNEST([

    STRUCT('telegram_http' AS signal_code, 'Telegram HTTP Blocking' AS description, 'application' AS category),
    STRUCT('telegram_tcp' AS signal_code, 'Telegram TCP Blocking' AS description, 'network' AS category),

    STRUCT('whatsapp_endpoint' AS signal_code, 'WhatsApp Endpoint Blocking' AS description, 'application' AS category),
    STRUCT('whatsapp_dns' AS signal_code, 'WhatsApp DNS Inconsistency' AS description, 'dns' AS category),

    STRUCT('signal_backend' AS signal_code, 'Signal Backend Failure' AS description, 'application' AS category),

    STRUCT('tor_port' AS signal_code, 'Tor Port Blocking' AS description, 'network' AS category),
    STRUCT('tor_obfs4' AS signal_code, 'Tor Obfs4 Blocking' AS description, 'circumvention' AS category),

    STRUCT('psiphon' AS signal_code, 'Psiphon Blocking' AS description, 'circumvention' AS category)

]);
