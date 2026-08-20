/* @bruin
name: stg.ooni_dnscheck_answer_bogon_flags
type: bq.sql
connection: bigquery-default

tags:
  - staging_bq
  - dataset_ooni_measurements
  - observations

description: |
  TD-47 Phase 2a, Task 3 (Layer A only): bogon/reserved-range IP answer
  detection over stg.ooni_dnscheck_query_answers. Grain: one row per
  (measurement_id, resolver_url, query_index) that has at least one
  answer -- a lightweight derived characterization table, following this
  repo's existing convention of small materialized `table` assets (no
  `view` materialization type exists anywhere else in this pipeline as
  of this session; checked before choosing this shape).

  DETECTION MECHANISM -- REUSED, NOT REIMPLEMENTED: the only actual
  bogon/reserved-range IP check anywhere in this pipeline before this
  session was the answer-string regex in
  int.ooni_experiment_results.sql's `dns_source` CTE (line ~75):
  `answer_type IN ('A','AAAA') AND REGEXP_CONTAINS(LOWER(answer),
  r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$|
  ::1$|fc|fd|fe80)')`. That is the mechanism reused verbatim here
  (applied separately to ipv4/ipv6, since this table keeps them in
  separate columns rather than one coalesced `answer` string). No
  second bogon-range implementation was written. `dns_bogon_error` (the
  probe engine's OWN bogon verdict, a `failure` string rather than a
  literal answer -- see int.ooni_experiment_results.sql's TD-55 note)
  is a structurally different signal, already captured for other test
  types; it was checked against this table's own `query_failure`
  vocabulary and never appears there (see reports.md Task 2/3) -- not
  reproduced here for the same reason.

  FILTERING-PROVIDER EXCEPTIONS -- explicit, not silent. A resolver
  that filters by product design (blocks malware/ads/adult content) can
  legitimately return a sinkhole/NXDOMAIN-equivalent/bogon-shaped
  answer for a domain it intentionally filters -- that is correct
  product behavior, not censorship, and must not be flagged the same
  way an unexpected bogon from a non-filtering resolver would be.
  `is_known_filtering_provider` is TRUE only for `target` values
  confirmed (via the live target/provider distribution in reports.md
  Task 3) to be a resolver's own explicitly-filtered endpoint:
    - Quad9 SECURED endpoints (dns.quad9.net, dns9.quad9.net,
      dns11.quad9.net -- Quad9's own published numbering: the *9/*11
      hostnames and bare dns.quad9.net are the malware-blocking
      variant). Quad9's UNSECURED endpoints (dns10.quad9.net,
      dns12.quad9.net -- also live in this dataset, live counts
      comparable to the secured ones) are deliberately NOT excepted --
      they do not filter by design, so a bogon from one of those would
      be exactly as suspicious as from any non-filtering resolver.
    - AdGuard default (dns.adguard.com, filters ads/trackers/malware
      by design) and AdGuard Family (dns-family.adguard.com, adds
      adult-content filtering).
    - Cloudflare for Families (family.cloudflare-dns.com, malware+
      adult) and Cloudflare malware-only (security.cloudflare-dns.com).
      Cloudflare's own unfiltered default (cloudflare-dns.com,
      1dot1dot1dot1.cloudflare-dns.com, dns.cloudflare.com) is
      deliberately NOT excepted.
    - Mullvad's ad-blocking endpoint (adblock.doh.mullvad.net).
    - DNSWarden's ad-blocking path variant (doh.{eu,asia,us}.dnswarden.
      com/adblock -- the /adblock path is the product's own filtering
      signal, distinct from any unfiltered DNSWarden endpoint).
    - CleanBrowsing (doh.cleanbrowsing.org) -- CleanBrowsing's entire
      product is tiered content filtering; even its base/default
      endpoint applies a filter tier, unlike the resolvers above where
      an unfiltered sibling endpoint coexists in the same dataset.
  Deliberately NOT excepted, having been checked and found to have no
  live evidence of default-on filtering: doh.opendns.com (OpenDNS's
  always-filtered tier is FamilyShield, a different hostname/IP not
  present in this dataset's target list; malware protection on plain
  OpenDNS is account-opt-in, not default), dns.nextdns.io and
  freedns.controld.com (both require a per-user profile/config to
  apply any filtering; the bare default endpoints seen here carry no
  such profile).

  THIS SESSION'S REAL HEADLINE FINDING, reported prominently per this
  session's own instructions (see reports.md Task 3 for the full
  account): the real, live bogon/reserved-range hit rate -- across
  4,701,073 individual answers / 5,697,535 (measurement, resolver,
  query) rows in the full population, non-exception rows included --
  is ZERO. Not "low"; zero. This is the actual decision input for
  whether Layer B (endpoint-consistency) or Layer C (cross-provider
  consensus), both deliberately deferred and NOT built in this session,
  are worth pursuing at all -- and it connects directly to this
  session's Task 0.2 finding that every dnscheck query in this dataset
  resolves the fixed, universally-uncensored `example.org`: no
  filtering OR censoring resolver has any product/political reason to
  intercept that domain, so a zero hit rate here is consistent with
  (not contradicted by) both a working detector and an uninformative
  test target. A future session should not read this table's current
  emptiness as "Layer A doesn't work" without also weighing that
  domain-choice confound.

  SCOPE: characterizes and flags only. NOT wired into
  int.ooni_measurement_verdicts_candidate.sql or any classification/
  reporting asset. Deliberately NOT cascaded beyond this staging layer.

depends:
  - stg.ooni_dnscheck_query_answers

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
  - name: has_bogon_answer
    type: boolean
    checks:
      - name: not_null
  - name: is_known_filtering_provider
    type: boolean
    checks:
      - name: not_null
  - name: is_flagged
    type: boolean
    checks:
      - name: not_null
@bruin */

WITH source AS (
  SELECT
    observation_id,
    measurement_id,
    country,
    probe_asn,
    probe_network_name,
    test_name,
    target,
    measurement_start_time,
    measurement_date,
    resolver_url,
    query_index,
    hostname,
    query_type,
    answer_count,
    answers,
    -- Reused verbatim from int.ooni_experiment_results.sql's dns_source
    -- CTE (see this asset's @bruin header) -- applied per-answer, across
    -- both ipv4/ipv6 columns since this table keeps them separate rather
    -- than coalesced into one `answer` string.
    EXISTS (
      SELECT 1
      FROM UNNEST(answers) AS a
      WHERE a.answer_type IN ('A', 'AAAA')
        AND (
          REGEXP_CONTAINS(LOWER(COALESCE(a.ipv4, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$)')
          OR REGEXP_CONTAINS(LOWER(COALESCE(a.ipv6, '')), r'^(::1$|fc|fd|fe80)')
        )
    ) AS has_bogon_answer,
    ARRAY(
      SELECT IFNULL(a.ipv4, a.ipv6)
      FROM UNNEST(answers) AS a
      WHERE a.answer_type IN ('A', 'AAAA')
        AND (
          REGEXP_CONTAINS(LOWER(COALESCE(a.ipv4, '')), r'^(127\.|10\.|192\.168\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|0\.0\.0\.0$)')
          OR REGEXP_CONTAINS(LOWER(COALESCE(a.ipv6, '')), r'^(::1$|fc|fd|fe80)')
        )
    ) AS bogon_ips,
    -- See this asset's @bruin header for the full, named reasoning
    -- behind each entry and each deliberate exclusion.
    target IN (
      'https://dns.quad9.net/dns-query', 'dot://dns.quad9.net/',
      'https://dns9.quad9.net/dns-query', 'dot://dns9.quad9.net/dns-query',
      'https://dns11.quad9.net/dns-query', 'dot://dns11.quad9.net/dns-query',
      'https://dns.adguard.com/dns-query', 'dot://dns.adguard.com/dns-query',
      'https://dns-family.adguard.com/dns-query', 'dot://dns-family.adguard.com/dns-query',
      'https://family.cloudflare-dns.com/dns-query', 'dot://family.cloudflare-dns.com/dns-query',
      'https://security.cloudflare-dns.com/dns-query', 'dot://security.cloudflare-dns.com/dns-query',
      'https://adblock.doh.mullvad.net/dns-query', 'dot://adblock.doh.mullvad.net/dns-query',
      'https://doh.eu.dnswarden.com/adblock', 'https://doh.asia.dnswarden.com/adblock', 'https://doh.us.dnswarden.com/adblock',
      'dot://doh.cleanbrowsing.org/'
    ) AS is_known_filtering_provider
  FROM `{{ var.project_id }}.stg.ooni_dnscheck_query_answers`
  WHERE answer_count > 0
)

SELECT
  observation_id,
  measurement_id,
  country,
  probe_asn,
  probe_network_name,
  test_name,
  target,
  measurement_start_time,
  measurement_date,
  resolver_url,
  query_index,
  hostname,
  query_type,
  answer_count,
  has_bogon_answer,
  bogon_ips,
  is_known_filtering_provider,
  (has_bogon_answer AND NOT is_known_filtering_provider) AS is_flagged
FROM source;
