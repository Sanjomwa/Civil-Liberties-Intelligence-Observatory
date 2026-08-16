# ADR-0012: Cascade-safe materialization by wrapper; no scheduled pipeline run

**Status:** Accepted, implemented, live-verified 2026-08-16. `Bruin/scripts/safe_run/safe_materialize.py` is built and verified in this repository's working tree.

## Context

On 2026-08-16, `.github/workflows/staleness-check.yml` (ADR-0005 — a daily CI job comparing Bruin's DAG dependency edges against each table's `__TABLES__` last-modified timestamp, failing on any downstream table older than an upstream it depends on) failed with 6 new violations: `int.google_pressure_periodized`, `marts.dim_country`, `marts.fact_ooni_censorship_signals`, `reporting.mart_pressure_attribution_daily`, and `reporting.mart_pressure_attribution_platform_drivers`, all stale relative to `int.ooni_experiment_results` and/or `stg.google_transparency_requests`.

Root cause, confirmed against live `__TABLES__` timestamps and commit history: the 2026-08-15 TD-80/TD-88/TD-89 fix commit (`365789f`) rematerialized those two upstream tables as part of unrelated bug fixes, but nothing rebuilt what depended on them afterward. No GitHub workflow executes `bruin run` on any schedule — only the staleness check itself runs on cron. Materialization only happens when a human, or an AI coding agent in a relay-prompt fix session, manually runs `bruin run`, and that session only rebuilt the two assets it was actively fixing. A follow-up relay session fixed the immediate problem: it computed the full transitive downstream closure (6 flagged edges expanded to 21 real assets), rebuilt all 21 in topological order, and confirmed the check passes clean.

Two questions followed. First: do we need a daily scheduled full-pipeline `bruin run` to prevent this from recurring? Second, given the answer is no, what actually prevents the same completeness gap from recurring?

The daily-schedule question is answered more decisively than a cost argument alone would suggest. Beyond the existing ~$22/month cost estimate to rebuild the OONI staging chain daily (for data that changes only when a human manually places a new file — no ingestion in this pipeline is live/automated), a design-review pass found that `pipeline.yml`'s already-declared `schedule: "@daily"` is not merely unexecuted, it is **currently unexecutable**: a full-pipeline run with default variables would hit `intelligence.acled_pressure_regimes_precondition_check`'s `ERROR()` guard every single night, because that check requires exactly one ACLED week in scope and the default `target_week=""` puts every Kenya week (1,523) in scope at once.

## Decision

**No scheduled `bruin run` is added.** The daily ADR-0005 staleness workflow stays exactly as it is — one cheap metadata comparison, no data scanned — as a backstop, not the primary defense.

**Instead, every materialization in this repository goes through one script, `Bruin/scripts/safe_run/safe_materialize.py`, which always runs `bruin run --downstream <asset>` and then runs the ADR-0005 staleness check in the same invocation.** A bare `bruin run <asset>` — touching only the asset actually being fixed, not its downstream closure — is no longer a sanctioned command in this repo, for a person or for a relay-prompt agent session. The script computes the affected asset set from `bruin internal parse-pipeline` before invoking Bruin, prints it with a cost estimate, and offers `--dry-run` to see that set without running anything.

It refuses, before executing anything, when the cascade would reach `intelligence.acled_pressure_regimes` — the pipeline's one `strategy: merge` asset, under an execution contract of one country x one new week x one execution. A cascade that reaches it with default vars aborts at the precondition check and leaves everything below it unbuilt — manufacturing exactly the partial-cascade staleness this wrapper exists to prevent. The refusal prints a two-phase remediation: cascade up to `features.acled_pressure_signals` with this script, advance the regime table with its own driver (`run_acled_regime_week.py` for a single new week, or the sequential backfill script for a logic change requiring a full replay), then cascade again from the regime asset.

This requirement is written into `CLAUDE.md`'s "Claude Code prompting standard" alongside the existing no-commit/no-push and `reports.md` rules.

## Consequences

- The cost objection to mandatory cascading does not survive its own numbers. The largest closure in the pipeline (`stg.ooni_measurements` -> 28 assets) is priced at roughly 131 GiB (about $0.80 at $6.25/TiB on-demand) and measured at 3m39s. Mandating the cascade costs pennies and minutes in the worst case that exists today.
- One branch of the DAG stays structurally expensive to fix, and the wrapper makes that visible rather than papering over it. Any change to ACLED staging, intermediate, or features logic cannot be repaired by cascade at all — the regime table advances one week at a time; correcting already-merged weeks against changed upstream logic means a full sequential backfill, not a downstream rebuild.
- A green wrapper run is not a correctness claim. The staleness check compares timestamps, never contents. Rerunning the regime asset out of contract writes silently-degraded persistence state while still bumping `last_modified_time` — the check would report PASS on a corrupted table. The wrapper's own success message says this explicitly and points at `pytest`/`bruin validate` as the separate obligations that actually check content.
- The wrapper inherits the staleness check's blind spots exactly, because it reads the same declared-dependency graph. An asset whose SQL reads a table it doesn't declare in `depends:` is invisible to both, identically.
- Failures in Python, view, or check-only assets are visible only through Bruin's own exit code, since the staleness check monitors only `bq.sql` table materializations.
- The wrapper runs the staleness check even when `bruin run` itself fails, because `create+replace` does not roll back a failed run — a partial cascade is exactly the moment the report is most useful.
- Enforcement is social, backed by a daily check — not fully technical. Nothing prevents a person or an agent from typing a bare `bruin run` directly; the daily CI workflow remains the actual backstop, at up to 24 hours of latency, for anything that bypasses the wrapper.

## Alternatives considered

- A daily scheduled full-pipeline `bruin run` (rejected): does not address the actual failure, which was completeness inside one session, not cadence. Cannot pay for itself (no ingestion is automated), and is not currently even executable (the ACLED precondition fires on the very first night).
- Making the staleness check auto-remediate (rejected): a check that writes is no longer a check — an unattended pipeline run with nobody reviewing what changed, and it would drive the ACLED merge asset straight through its own execution contract with nobody watching.
- A git hook or push-triggered CI check (rejected): warehouse table state is not a function of the commit; a push-triggered failure would blame an unrelated commit for a pre-existing warehouse condition.
- Bruin's `--selector` syntax instead of a wrapper script (not sufficient): cannot be combined with `--downstream` or a positional asset argument, and the wrapper needs the dependency closure computed directly anyway.
- `--exclude-tag` to route around contract-bound ACLED assets automatically (deferred, viable later): no existing tag isolates just the two contract-bound assets without also excluding `features.acled_pressure_signals`, which usually should rebuild.
- Bash rather than Python for the wrapper (rejected): this repo lints Python (`ruff check .`), has no shell-lint workflow, and both existing operational driver scripts are Python.
- An interactive cost-confirmation gate (rejected on the evidence): the worst-case cascade measured today is under a dollar and under four minutes; a confirmation prompt would deadlock non-interactive relay sessions.

## Follow-ups, deliberately deferred, not forgotten

1. A declared-lineage completeness check, comparing each asset's actual SQL table references against its declared `depends:` list.
2. A dedicated tag on the two ACLED contract-bound assets, enabling `--exclude-tag`-based routing instead of a hard refusal.
3. A comment added to `pipeline.yml` recording that `schedule: "@daily"` has no executor and would currently fail the ACLED precondition on the first run.
4. TD-39's CI-credentials gap for the golden-file test suite remains untouched by this ADR.

Explicitly out of scope for this ADR: background/async execution of the wrapper, any interactive cost gate, any auto-remediation, and any change to the daily staleness workflow itself.

## Live verification, 2026-08-16

Built and tested in this repository directly. Step 0 verification confirmed all assumed Bruin CLI flags real on the live install (`--downstream`, `--continue`, `--exclude-tag`, `--var`, `--only`, `--full-refresh`; no `--dry-run` on `bruin run` itself), confirmed `parse-pipeline`'s JSON shape, confirmed no interactive-prompt blocking, and empirically reproduced the ACLED precondition's exact `ERROR()` text by running `intelligence.acled_pressure_regimes_precondition_check` directly with default `target_week=""`.

End-to-end test against `marts.fact_takedown_pressure_daily` (zero downstream consumers, chosen to minimize blast radius) passed in all four modes: `--dry-run` on the small leaf (scope=1); `--dry-run` on an ACLED-branch asset (correctly refused, exit code 3, remediation printed); a real full cascade with the inline staleness check (exit 0, PASS); post-cascade `pytest`/`bruin validate` both held at baseline.
