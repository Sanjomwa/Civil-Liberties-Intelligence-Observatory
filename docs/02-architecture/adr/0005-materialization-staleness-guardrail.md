# ADR-0005: Materialization-Staleness Guardrail (CI Check over the Live DAG)

Status: Accepted, implemented (script + allowlist landed 2026-07-05, commit `cdc429a`; this ADR, the scheduled workflow, and TD-56 landed 2026-07-06)
Date: 2026-07-05 (mechanism verified and first run), 2026-07-06 (completed and documented)

## Context

This project has now hit the same failure category three separate times:

- **TD-38**: the steady-state pipeline design would have silently recomputed an upstream's full history on every run, violating the regime engine's execution contract without any signal.
- **TD-40**: a month-old upstream schema rename (`6dbe7ab`) left `fact_country_pressure_daily`'s definition reading an always-`NULL` column — invisible until the next materialization, which would have silently zeroed the composite pressure score.
- **TD-54**: TD-47's dnscheck recovery rematerialized `features.protocol_daily_signals`, but everything downstream deliberately was not — a *correct* decision, but one that until now lived only in prose, with nothing preventing an accidental cascade or detecting the divergence.

The common shape: **an asset is rematerialized with new data or a new definition, but a downstream asset that depends on it is not, leaving the live warehouse internally inconsistent with no signal anywhere.** Bruin's DAG guarantees ordering *within* a run; nothing detects a partial cascade *between* runs. The first run of this check (below) proved the problem is not hypothetical: beyond the known TD-54 hold, it surfaced seven previously-unknown stale edges, some dating to April 2026.

## Decision

A standing CI check, `Bruin/scripts/staleness_check/check_materialization_staleness.py`, enforces:

> For every dependency edge (A depends on B) where both A and B are BigQuery table materializations, if B's `last_modified_time` is newer than A's, then A was built from a version of B that no longer exists — A is stale relative to its own declared input.

Deliberately-accepted gaps live in `staleness_allowlist.json` next to the script; each entry must carry `downstream`, `upstream`, a `td_ref`, and a one-line `reason` (a malformed entry is an operational error, not a silent pass). Allowlisted violations are reported but do not fail the check; **only new, undocumented staleness exits non-zero.** Exit codes: 0 = clean or fully allowlisted, 1 = at least one new stale edge, 2 = operational error (bruin parse failure, BigQuery unreachable, malformed allowlist) — an operational failure is never conflated with a pass.

## Mechanism (each step verified live, 2026-07-05, not assumed)

1. **Dependency graph**: `bruin internal parse-pipeline Bruin/` emits the entire pipeline as JSON in one call, including every asset's `upstreams`, and needs no connection config — so it runs in CI from a bare checkout. `bruin lineage` (the roadmap's first guess) is human-oriented output and was not needed. Because `parse-pipeline` is an *internal* command whose shape could change on a CLI upgrade, the script validates the output shape defensively and exits 2 with a pointer to this ADR if it ever changes.
2. **Timestamps**: each dataset's `__TABLES__` metatable provides `last_modified_time` (epoch millis) for every table, matched to assets by their declared `name:` (`dataset.table`). Two seemingly-nicer alternatives were checked and **do not work here**: `INFORMATION_SCHEMA.TABLES` has no last-modified column at all, and the region-wide `INFORMATION_SCHEMA.TABLE_STORAGE` view is access-denied for this project's accounts. This is exactly the kind of assumed-fact the roadmap said to confirm before building, and the assumption (INFORMATION_SCHEMA) was indeed wrong.
3. **Scope**: only `type: bq.sql` assets with `materialization.type: table` are monitored (42 of 56 assets today). Python assets are skipped because their declared names do not reliably map to BigQuery tables (e.g. `load.ooni_to_gcs` writes to GCS; the `raw.*` assets' declared dataset does not exist — the TD-42 lineage mismatch). Views are skipped because they read live and cannot be data-stale. Check-only assets produce no table to compare.
4. **No tolerance window**: within a single `bruin run`, upstreams finish before downstreams start, so timestamps are correctly ordered; any inversion means the downstream genuinely was not rebuilt after its upstream changed. Accepted caveat: rerunning an upstream with byte-identical output still bumps its timestamp and will flag downstreams — the check cannot cheaply prove output equality; the remedy is to rematerialize the downstream or allowlist with a TD reference.
5. **CI credentials**: the `bruin-ci` service account already used by Workload Identity Federation (`gcp-auth.yml`) holds `roles/bigquery.dataEditor` + `roles/bigquery.jobUser`, verified sufficient for the `__TABLES__` metadata query. No new keys, no new service accounts.

## Cadence and triggers

`.github/workflows/staleness-check.yml`: **daily** (06:00 UTC) plus `workflow_dispatch`, plus a **path-filtered** push trigger covering only `Bruin/scripts/staleness_check/**` and the workflow file itself.

- Daily, not weekly: staleness is introduced by warehouse-side actions (manual `bruin run`s, backfills, ad-hoc rematerializations) that can happen any day, and the check is one metadata query — detection latency of ≤24h costs almost nothing.
- Not on every push to main: a push does not change warehouse state, so a push-triggered failure would blame an unrelated commit for a pre-existing warehouse condition. The path filter exists so that edits to the check or its allowlist are validated at merge time — the one case where a push *does* change what the check will conclude.

## First-run findings (2026-07-05)

Of 65 table-to-table edges checked, 12 were stale — none previously visible anywhere:

- **5 deliberate**: the TD-54/TD-49 hold boundary (4 edges downstream of `features.protocol_daily_signals`) and `int.ooni_signals`'s exclusion from the Tier 1 cascade. These are the allowlist's intended use: each entry cites its TD and the reason the gap is accepted.
- **7 previously unknown**: `marts.dim_platforms`, `marts.dim_reasons` (2 edges), `marts.dim_regions`, `marts.dim_requestors`, `marts.fact_asn_repression_index`, and `marts.fact_network_blocking_daily` — last built between 2026-04-18 and 2026-05-11 while their upstreams were reworked repeatedly (TD-40's fix, ADR-0004's reweighting, the Tier 1 OONI cascade). Logged as **TD-56**, allowlisted with that reference so the check runs clean while their per-asset disposition (rematerialize vs retire) is decided deliberately, not as a side effect. Notably, `marts.dim_regions` predates the `6dbe7ab` schema rename that caused TD-40/TD-41 — it must be checked against the renamed columns before any rebuild.

## Consequences and limitations

- The standing "do not rematerialize the protocol-regimes chain until TD-49 ships" hold is now *enforced by machinery*, not just recorded in prose — an accidental cascade would flip those allowlist entries from matching to orphaned, and a new partial cascade anywhere in the DAG fails CI within a day.
- **Allowlist hygiene is part of resolving a TD**: when a TD referenced by an allowlist entry resolves (i.e., the downstream is rematerialized or retired), the entry stops matching any live violation and the script logs a prune warning. Remove the entry in the same commit that resolves the TD, per the standing same-commit-docs discipline.
- The check inherits the declared lineage's accuracy: an asset whose `depends:` list is wrong (TD-42's category) is checked against its *declared* inputs, not its real ones. Fixing declared lineage remains its own work; this check makes declared lineage more valuable, not less.
- Python-asset and view endpoints are unmonitored by design (see Mechanism §3). If a future python asset materializes a table under its declared name, it can be promoted into scope then — not speculatively now.
- The check compares timestamps, not content: it proves *A was not rebuilt after B changed*, never *A's contents are wrong*. It is a smoke detector for the TD-38/TD-40/TD-54 category, not a data-diff.
