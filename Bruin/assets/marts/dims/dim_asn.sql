/* @bruin
tags:
  - marts_bq
name: marts.dim_asn
type: bq.sql
connection: bigquery-default

description: |
  Canonical ASN dimension for Kenya censorship observatory.
  Clean, join-safe representation of ASN extracted from OONI signals.

  Key principle:
    - No heuristic ISP classification
    - No pattern-based assumptions
    - Pure normalization + validity flag

materialization:
  type: table
  strategy: create+replace
@bruin */

WITH base AS (
    SELECT DISTINCT
        asn,
        country
    FROM `encoded-joy-485413-k5.int.ooni_signals`
),

cleaned AS (
    SELECT
        country,

        -- ── canonical ASN key ─────────────────────────────────────────────
        SAFE_CAST(asn AS STRING) AS asn_id,

        -- ── validity flags ────────────────────────────────────────────────
        CASE
            WHEN asn IS NULL THEN FALSE
            WHEN SAFE_CAST(asn AS STRING) IS NULL THEN FALSE
            ELSE TRUE
        END AS is_valid_asn,

        -- ── metadata ──────────────────────────────────────────────────────
        CURRENT_TIMESTAMP() AS extracted_at

    FROM base
)

SELECT *
FROM cleaned;