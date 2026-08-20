/* @bruin
name: stg.udf_dnscheck_query_answers
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements

description: |
  TD-47 Phase 2a: creates (as a permanent BigQuery routine, not a table --
  same check-only-asset shape as stg.udf_dnscheck_lookup_entries.sql) a
  second JS UDF that goes one level deeper than that UDF: for each
  dnscheck lookups[resolver_url] entry, explodes its queries[] array and,
  for each query, its own answers[] array -- the actual resolved DNS
  answer content (IPs, ASN/org, TTL) that Phase 1's extraction never
  captured (see stg.ooni_dnscheck_lookups.sql's "KNOWN GAP" note).

  WHY A SEPARATE UDF, NOT AN EXTENSION OF stg.dnscheck_lookup_entries:
  that UDF's return grain is one row per (resolver_url) -- the lookup
  entry itself. This UDF's return grain is one row per
  (resolver_url, query_index), nested one level deeper, with answers as
  a further-nested repeated STRUCT field. Confirmed live before writing
  this that BigQuery JS UDFs DO support a doubly-nested
  ARRAY<STRUCT<... ARRAY<STRUCT<...>>>> return type (a disposable
  `CREATE TEMP FUNCTION ... RETURNS ARRAY<STRUCT<a STRING, items
  ARRAY<STRUCT<b STRING, c INT64>>>>` round-tripped correctly via `bq
  query` before this asset was written) -- so no flatten-then-
  ARRAY_AGG-back-together workaround was needed. Reuses JSON.parse over
  raw_test_keys, not BigQuery's own PARSE_JSON/JSON_VALUE, for the same
  reason stg.udf_dnscheck_lookup_entries does (see that asset's header):
  PARSE_JSON() fails outright on 6.6% of live dnscheck rows on a float
  round-trip limitation.

  SCHEMA CORRECTION, confirmed against live data before finalizing this
  return type: a prior design assumed a per-query `rcode` field would be
  present (DNS response-code-shaped injection, e.g. spoofed NXDOMAIN,
  showing up here rather than in the top-level `failure` string). Live
  verification across the FULL dnscheck population (1,105,030
  measurements, REGEXP_CONTAINS(raw_test_keys, r'"rcode"')) found
  `rcode` present in ZERO rows -- this field does not exist anywhere in
  this dataset's actual dnscheck schema, live-spec drift from whatever
  version of OONI's experimental dnscheck spec the design assumed. Not
  included in the return type below. Per-query `failure` (already
  captured) is the only outcome signal this data actually carries at
  the query level. Similarly, `answer_type = 'CNAME'` (which would
  populate an answer's `hostname` field) was checked and found in ZERO
  of 1,105,030 measurements -- the field is kept in the return type for
  schema completeness (a future non-example.org target could plausibly
  return a CNAME) but is universally NULL in this dataset today.

depends:
  - stg.ooni_measurements
@bruin */

CREATE OR REPLACE FUNCTION `{{ var.project_id }}.stg.dnscheck_query_answers`(raw_test_keys STRING)
RETURNS ARRAY<STRUCT<
  resolver_url STRING,
  query_index INT64,
  hostname STRING,
  query_type STRING,
  engine STRING,
  query_failure STRING,
  t FLOAT64,
  answers ARRAY<STRUCT<
    answer_type STRING,
    ipv4 STRING,
    ipv6 STRING,
    asn INT64,
    as_org_name STRING,
    hostname STRING,
    ttl INT64
  >>
>>
LANGUAGE js AS """
  // JSON.parse, not BigQuery's own PARSE_JSON -- see this asset's @bruin
  // header, and stg.udf_dnscheck_lookup_entries's header, for the live
  // PARSE_JSON/JSON_KEYS failures that ruled out the native-SQL path.
  try {
    var testKeys = JSON.parse(raw_test_keys);
    if (!testKeys || !testKeys.lookups) {
      return [];
    }
    var out = [];
    for (var resolverUrl in testKeys.lookups) {
      var entry = testKeys.lookups[resolverUrl] || {};
      var queries = entry.queries || [];
      for (var i = 0; i < queries.length; i++) {
        var q = queries[i] || {};
        var rawAnswers = q.answers || [];
        var outAnswers = [];
        for (var j = 0; j < rawAnswers.length; j++) {
          var a = rawAnswers[j] || {};
          outAnswers.push({
            answer_type: a.answer_type || null,
            ipv4: a.ipv4 || null,
            ipv6: a.ipv6 || null,
            asn: (a.asn === undefined || a.asn === null) ? null : a.asn,
            as_org_name: a.as_org_name || null,
            hostname: a.hostname || null,
            ttl: (a.ttl === undefined || a.ttl === null) ? null : a.ttl
          });
        }
        out.push({
          resolver_url: resolverUrl,
          query_index: i,
          hostname: q.hostname || null,
          query_type: q.query_type || null,
          engine: q.engine || null,
          query_failure: q.failure || null,
          t: (q.t === undefined || q.t === null) ? null : q.t,
          answers: outAnswers
        });
      }
    }
    return out;
  } catch (e) {
    return [];
  }
""";
