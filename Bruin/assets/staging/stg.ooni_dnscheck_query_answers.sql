/* @bruin
name: stg.ooni_dnscheck_query_answers
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  TD-47 Phase 2a: dnscheck's per-query answer-content extraction -- the
  KNOWN GAP flagged in stg.ooni_dnscheck_lookups.sql's header. Grain: one
  row per (measurement_id, resolver_url, query_index) -- one row per
  A/AAAA query issued against a specific resolver endpoint within a
  lookups entry, carrying its full answer set as a nested repeated
  field rather than flattened to one-row-per-answer (confirmed live
  before building this that BigQuery JS UDFs support a doubly-nested
  ARRAY<STRUCT<...ARRAY<STRUCT<...>>>> return type -- see
  stg.udf_dnscheck_query_answers.sql's header).

  WHY THIS EXISTS, AND WHY SEPARATE FROM PHASE 1: Phase 1
  (stg.ooni_dnscheck_lookups) captures only the TRANSPORT/REACHABILITY
  tuple per resolver (did the lookup entry itself fail, and how) --
  it has no visibility into what a "successful" lookup's query actually
  resolved to. Confirmed live (Phase 1's own header, reconfirmed here):
  answers[] is populated even when a lookup entry's top-level
  `failure` is null. DNS manipulation classically shows up as a
  resolution that succeeds but returns a wrong/injected answer -- this
  asset is what makes that visible at all.

  TWO HEADLINE HYPOTHESES FROM THE DESIGN CONSULT, BOTH VERIFIED LIVE
  BEFORE BUILDING (see reports.md Task 0 for the full account):
    1. A dnscheck measurement covers exactly ONE resolver SERVICE, not
       several compared within one measurement. CONFIRMED, but only
       after correcting the verification method: grouping distinct
       `lookups` dict keys by raw host string (e.g. "149.112.112.10"
       vs "9.9.9.10") wrongly suggested 2-4 "providers" per measurement,
       because a single service's own bootstrap resolution fans out to
       multiple IPv4/IPv6 endpoints, each becoming its own `lookups` key.
       Grouping instead by `bootstrap.queries[].hostname` (equivalently,
       stg.ooni_measurements.input) -- the actual service under test,
       e.g. "dns.google", "dns11.quad9.net" -- gives exactly 1 distinct
       value in 500/500 sampled measurements, zero exceptions. Provider
       identity for any future cross-provider work should key off
       target/input or bootstrap hostname, never off resolver_url's raw
       host string.
    2. The hostname resolved via `lookups[*].queries[]` is OONI's own
       default test domain, not a censored target site. CONFIRMED
       decisively: `domain = 'example.org'` in 1,105,030/1,105,030
       (100%) of the live dnscheck population (full-table
       REGEXP_CONTAINS scan, not a sample), and every sampled query's
       own `hostname` field matches it with zero exceptions. This
       test type characterizes resolver-level DNS manipulation against
       one fixed, uncensored reference domain -- it cannot by itself
       tell you whether a *specific blocked site* resolves correctly
       through a given resolver. Flagged prominently per this session's
       instructions: this materially changes the payoff calculus for
       any future endpoint-consistency/consensus layer (Layer B/C,
       deliberately deferred, see stg.udf_dnscheck_query_answers.sql
       and reports.md) -- those layers can only ever answer "does this
       resolver treat example.org consistently with its peers," not
       "does this resolver hide a real blocked site."

  SCHEMA CORRECTION vs. this session's originating design: `rcode` was
  assumed present per-query and is NOT -- confirmed absent in all
  1,105,030 live dnscheck measurements (see the UDF asset's header).
  Dropped from this table. `query_failure` (the per-query `failure`
  string) is the only outcome signal this data actually carries at the
  query level; real live values include network_unreachable,
  host_unreachable, ssl_unknown_authority, generic_timeout_error,
  ssl_invalid_certificate, eof_error, and an
  "unknown_failure: doh: server returned error" string -- no
  nxdomain-shaped value observed in query_failure specifically (dnscheck
  bootstrap's own dns_bogon_error/nxdomain vocabulary lives one layer up,
  already captured elsewhere).

  JOIN, NOT INDEPENDENT RE-DERIVATION: joins to Phase 1's
  stg.ooni_dnscheck_lookups on (measurement_id, resolver_url) for all
  passenger/dimension columns (country, probe_asn, target, dates) rather
  than re-deriving them from stg.ooni_measurements a second time -- that
  table's grain is exactly one row per (measurement_id, resolver_url),
  a superset key of this asset's own grain, so the join is 1:1-or-fewer
  by construction (every resolver_url this UDF can emit a query for must
  already have a lookups-entry row). INNER JOIN is safe on that basis;
  confirmed via row-count comparison before finalizing (see reports.md
  Task 1). Phase 1's own table is read-only here -- not modified,
  restructured, or replaced.

  SCOPE, per this session's explicit instructions: additive and
  read-only relative to everything else in the pipeline. Does NOT feed
  int.ooni_measurement_verdicts_candidate.sql or any classification/
  reporting asset. Deliberately NOT cascaded beyond this staging layer
  in this session -- see stg.dnscheck_answer_bogon_flags (TD-47 Phase 2a
  Task 3) for the one derived characterization built on top of this
  table, itself also uncascaded.

depends:
  - stg.ooni_measurements
  - stg.udf_dnscheck_query_answers
  - stg.ooni_dnscheck_lookups

materialization:
  type: table
  strategy: create+replace
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
  - name: resolver_url
    type: string
    checks:
      - name: not_null
  - name: query_index
    type: integer
    checks:
      - name: not_null
@bruin */

WITH measurements AS (
  SELECT measurement_id, raw_test_keys
  FROM `{{ var.project_id }}.stg.ooni_measurements`
  WHERE test_name = 'dnscheck'
),

exploded AS (
  SELECT
    m.measurement_id,
    qa.resolver_url,
    qa.query_index,
    qa.hostname,
    qa.query_type,
    qa.engine,
    qa.query_failure,
    qa.t,
    qa.answers
  FROM measurements AS m,
  UNNEST(`{{ var.project_id }}.stg.dnscheck_query_answers`(m.raw_test_keys)) AS qa
)

SELECT
  TO_HEX(MD5(CONCAT(
    e.measurement_id, '|dnscheck_query_answer|',
    e.resolver_url, '|',
    CAST(e.query_index AS STRING)
  ))) AS observation_id,
  l.measurement_id,
  l.country,
  l.probe_asn,
  l.probe_network_name,
  l.test_name,
  l.test_version,
  l.target,
  l.measurement_start_time,
  l.measurement_date,
  'dnscheck_query_answer' AS observation_type,
  'DNS_RESOLVER' AS probe_target,
  e.resolver_url,
  e.query_index,
  e.hostname,
  e.query_type,
  e.engine,
  e.query_failure,
  e.t AS query_duration_seconds,
  ARRAY_LENGTH(e.answers) AS answer_count,
  ARRAY(
    SELECT DISTINCT IFNULL(a.ipv4, a.ipv6)
    FROM UNNEST(e.answers) AS a
    WHERE a.ipv4 IS NOT NULL OR a.ipv6 IS NOT NULL
    ORDER BY 1
  ) AS ip_list,
  ARRAY(
    SELECT DISTINCT a.asn
    FROM UNNEST(e.answers) AS a
    WHERE a.asn IS NOT NULL
    ORDER BY 1
  ) AS asn_list,
  e.answers
FROM exploded AS e
INNER JOIN `{{ var.project_id }}.stg.ooni_dnscheck_lookups` AS l
  ON e.measurement_id = l.measurement_id
  AND e.resolver_url = l.resolver_url;
