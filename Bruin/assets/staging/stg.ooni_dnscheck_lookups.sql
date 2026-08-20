/* @bruin
name: stg.ooni_dnscheck_lookups
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  TD-47 Phase 1: dnscheck's per-resolver lookups extraction. Grain: one row
  per (measurement_id, resolver_url) -- one row per DoH/DoT resolver
  endpoint dnscheck actually queried, tagged probe_target = 'DNS_RESOLVER'.

  WHY THIS EXISTS: dnscheck's raw test_keys carries two structurally
  different sub-objects, both confirmed live before this asset was
  written. `bootstrap` (already extracted, see stg.ooni_measurement_
  summary.sql's dnscheck_bootstrap_failure) is a single system-resolver
  hostname lookup -- did the probe resolve the DoH/DoT SERVICE's own
  hostname at all. `lookups` (this asset, never extracted before now) is
  a dict keyed by resolver URL, one entry per actual DoH/DoT endpoint the
  probe then queried directly -- this is dnscheck's real differentiator,
  the part that tests DNS-manipulation resistance across multiple
  resolvers, not just whether one hostname resolved. A prior
  characterization session (TD-101, 2026-08-20) found real per-resolver
  failures inside `lookups` (a TLS cert validation failure against
  dns12.quad9.net; an IPv6 network-unreachable failure against two
  Cloudflare DoT addresses) that `bootstrap_failure` has zero visibility
  into -- confirmed by direct raw JSON inspection, not inferred.

  `input` (the app-path/bootstrap concept, carried through unchanged as
  `target` below, house style) identifies the DoH/DoT SERVICE being
  tested (e.g. "https://dns.google/dns-query", a hostname-level
  identity). `resolver_url` (new, this asset) identifies the SPECIFIC
  resolved endpoint queried underneath that service (e.g.
  "https://8.8.4.4/dns-query" -- one of dns.google's several A/AAAA
  answers) -- confirmed live: `target`'s hostname resolves to 2-6
  `lookups` entries per measurement (n_keys distribution, full ~1.1M-row
  dnscheck population: 4 keys most common at 475,163 rows, then 2 at
  309,461, 1 at 307,298, 0 at 8,965 -- the resolver's own bootstrap
  lookup itself failed, so `lookups` never ran -- 6 at 3,791, 3 at 349, 5
  at 3).

  EXTRACTION METHOD -- calls stg.udf_dnscheck_lookup_entries's permanent
  JS UDF (`stg.dnscheck_lookup_entries`), not native SQL JSON functions --
  see that asset's own header for the full account of why: an inline
  CREATE TEMP FUNCTION ahead of this asset's own SELECT was tried first
  and rejected outright by `bruin validate` (a bq.sql asset body must be
  a single query, not a multi-statement script), and two native-SQL
  alternatives (JSON_KEYS(PARSE_JSON(...))'s inconsistent key-quoting;
  PARSE_JSON()'s own outright failure on 6.6% of a live sample, a real
  float round-trip limitation, not a malformed-input case) were tried
  and found broken against live data before falling back to a permanent
  UDF at all.

  GRAIN CHOICE -- one row per (measurement_id, resolver_url), not further
  split into one row per protocol sub-layer (tcp_connect/tls_handshakes/
  requests/queries all exist inside a lookups entry, confirmed live).
  failed_operation ('connect'/'tls_handshake'/'quic_handshake'/'resolve',
  confirmed live across a 5,000-row sample) already identifies which
  layer failed when one did, mirroring how the failure/failed_operation
  pair already bubbles up on `bootstrap` and on psiphon_failure (TD-91) --
  no case found live where a resolver's own sub-layer arrays would add
  information failure/failed_operation doesn't already carry. Deeper
  per-layer explosion (tcp_connect[]/tls_handshakes[] arrays, matching
  stg.ooni_tcp_observations.sql/stg.ooni_tls_observations.sql's own
  per-layer grain) is left for a future session if Task 2's
  characterization ever needs it -- not built speculatively here.

  probe_target = 'DNS_RESOLVER' (constant, every row) is a new label,
  deliberately distinct from the implicit "the app's own hostname"
  concept every other dnscheck/bootstrap-derived column carries -- so a
  downstream consumer can never conflate "this specific DNS resolver
  endpoint failed/was blocked" with "the probe couldn't resolve the
  app's own hostname," a different, unrelated failure category.

  SCOPE, per this session's explicit instructions: additive only. Does
  NOT modify, replace, or feed into dnscheck_bootstrap_failure or
  anything in int.ooni_measurement_verdicts_candidate.sql -- that
  classification is completely unchanged by this asset's existence.
  Deliberately NOT cascaded into features/intelligence/marts/reporting
  in this session (matches TD-54's own precedent: a new multi-million-
  row signal reaching the dashboard deserves an explicit measured
  rollout, not a silent side effect of a staging build).

  KNOWN GAP, found via advisory review after this asset was otherwise
  complete (see reports.md Task 2.6 for the full account): this table
  captures each lookup entry's TRANSPORT/REACHABILITY tuple
  (resolver_url, failure, failed_operation, agent) only. It does NOT
  capture entry.queries[].answers[] -- the actual resolved DNS answer
  content (IPs, ASN/org) each query returned. Confirmed live that
  answers[] is populated even on failure = null (a "successful")
  lookups entries, and dns_bogon_error -- the largest single value in
  dnscheck_bootstrap_failure -- has zero presence in this table's own
  lookup_failure vocabulary, suggesting lookups-layer manipulation (if
  present) would show up in answers, not failure. A DNS-manipulation-
  aware routing rule almost certainly needs a second extraction (or a
  finer/nested grain -- the current one-row-per-(measurement_id,
  resolver_url) grain has no room for multiple answers per resolver)
  before it can be built. Not extracted here -- flagged for the next
  session, not built speculatively in this one.

depends:
  - stg.ooni_measurements
  - stg.udf_dnscheck_lookup_entries

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
  - name: probe_target
    type: string
    checks:
      - name: not_null
      - name: accepted_values
        value: [DNS_RESOLVER]
@bruin */

WITH measurements AS (
  SELECT *
  FROM `{{ var.project_id }}.stg.ooni_measurements`
  WHERE test_name = 'dnscheck'
),

exploded AS (
  SELECT
    m.measurement_id,
    m.country,
    m.probe_asn,
    m.probe_network_name,
    m.test_name,
    m.test_version,
    m.input AS target,
    m.measurement_start_time,
    m.measurement_date,
    lookup_offset,
    entry.resolver_url,
    entry.lookup_failure,
    entry.lookup_failed_operation,
    entry.lookup_agent
  FROM measurements AS m,
  UNNEST(`{{ var.project_id }}.stg.dnscheck_lookup_entries`(m.raw_test_keys)) AS entry
  WITH OFFSET AS lookup_offset
)

SELECT
  TO_HEX(MD5(CONCAT(
    measurement_id, '|dnscheck_lookup|',
    CAST(lookup_offset AS STRING), '|',
    resolver_url, '|',
    COALESCE(lookup_failure, '')
  ))) AS observation_id,
  measurement_id,
  country,
  probe_asn,
  probe_network_name,
  test_name,
  test_version,
  target,
  measurement_start_time,
  measurement_date,
  'dnscheck_lookup' AS observation_type,
  'DNS_RESOLVER' AS probe_target,
  resolver_url,
  lookup_failure,
  lookup_failed_operation,
  lookup_agent,
  lookup_offset
FROM exploded;
