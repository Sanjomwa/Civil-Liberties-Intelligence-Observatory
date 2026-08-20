/* @bruin
name: stg.udf_dnscheck_lookup_entries
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements

description: |
  TD-47 Phase 1: creates (as a permanent BigQuery routine, not a table --
  no materialization: block, same check-only-asset shape as
  int.ooni_measurement_verdicts_confirmed_guard.sql and
  assets/intelligence/acled_pressure_regimes_precondition.sql) the JS UDF
  stg.ooni_dnscheck_lookups.sql depends on to explode dnscheck's raw
  test_keys.lookups object into per-resolver rows.

  WHY A PERMANENT UDF, AND WHY NOT NATIVE SQL -- tested live, not
  assumed, before choosing this design (see stg.ooni_dnscheck_lookups.sql's
  own header for the full account):
    1. A first attempt inlined this as a CREATE TEMP FUNCTION directly
       inside stg.ooni_dnscheck_lookups.sql's own body, ahead of its
       SELECT. `bruin validate` rejected it outright: "Invalid query
       found: Syntax error: Unexpected keyword CREATE at [2:1]" --
       Bruin's own SQL validator parses a bq.sql asset's body as a
       single query, not a multi-statement script, so a leading DDL
       statement ahead of the real SELECT is not accepted for a
       materializing asset.
    2. The two obvious native-SQL alternatives were tried and found
       broken against real live data before falling back to a UDF at
       all: JSON_KEYS(PARSE_JSON(...), 1) returns some keys wrapped in a
       literal, embedded escaped-quote character and others without
       (inconsistent, would silently corrupt resolver_url for an
       unpredictable subset of rows); PARSE_JSON() itself outright FAILS
       ("Input number: 0.026005729 cannot round-trip through string
       representation") on 132/2,000 (6.6%) of a live random dnscheck
       sample, even when scoped to just the $.lookups substring -- a
       genuine BigQuery float-precision limitation hit by real
       network_events timestamps inside lookups entries, not a
       malformed-input edge case that could be filtered out.
    3. A check-only asset (no materialization: block) whose entire body
       is a bare `CREATE OR REPLACE FUNCTION ... LANGUAGE js` DDL
       statement WAS confirmed to validate and run cleanly via
       `bruin validate` and `bruin run` (proven with a disposable scratch
       asset before building this one for real) -- this is that asset.

  This creates a genuinely PERMANENT (not TEMP) BigQuery routine, because
  a TEMP FUNCTION only exists for the lifetime of the single query/script
  that defines it -- it would not be visible to a separate asset's own
  SELECT in a later `bruin run` invocation. This is the first UDF
  (temporary or permanent) anywhere in this repository's assets -- no
  prior precedent -- introduced here because both native-SQL alternatives
  were verified broken, not by preference. A future session should
  revisit whether a native-SQL workaround becomes viable (e.g. if
  BigQuery's PARSE_JSON round-trip behavior changes) before adding a
  second UDF elsewhere in this pipeline for a similar reason.

depends:
  - stg.ooni_measurements
@bruin */

CREATE OR REPLACE FUNCTION `{{ var.project_id }}.stg.dnscheck_lookup_entries`(raw_test_keys STRING)
RETURNS ARRAY<STRUCT<
  resolver_url STRING,
  lookup_failure STRING,
  lookup_failed_operation STRING,
  lookup_agent STRING
>>
LANGUAGE js AS """
  // JSON.parse, not BigQuery's own PARSE_JSON -- see this asset's @bruin
  // header for the two live PARSE_JSON/JSON_KEYS failures that ruled out
  // the native-SQL path entirely.
  try {
    var testKeys = JSON.parse(raw_test_keys);
    if (!testKeys || !testKeys.lookups) {
      return [];
    }
    var out = [];
    for (var resolverUrl in testKeys.lookups) {
      var entry = testKeys.lookups[resolverUrl] || {};
      out.push({
        resolver_url: resolverUrl,
        lookup_failure: entry.failure || null,
        lookup_failed_operation: entry.failed_operation || null,
        lookup_agent: entry.agent || null
      });
    }
    return out;
  } catch (e) {
    return [];
  }
""";
