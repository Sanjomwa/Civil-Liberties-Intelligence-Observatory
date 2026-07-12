# CLIO Testing Strategy

Status: Phase 1 deliverable, CLIO Engineering Reset. Replaces the earlier stub written during the Project Zero Review with the specifics gathered during the engineering-first pass.

## Current state — stated plainly

**Updated 2026-07-12 — the paragraph below was stale and has been corrected; see `technical-debt-inventory.md` and `decision-log.md` for the work that overtook it.** The repository now has three test files, not one: `tests/test_contracts.py` (70 lines, 4 tests, `streamlit/core/contracts.py`'s schema-validation helper — the original, still-accurate description of this file alone), `tests/test_acled_pressure_regimes_golden.py` (81 lines, 2 tests, TD-08's Layer B golden-file drift check against materialized ACLED regime output — gated behind `RUN_BIGQUERY_TESTS=1`, so it self-skips rather than running in CI, see "CI integration" below), and `tests/test_ooni_dns_bogon_classification.py` (124 lines, 5 tests, TD-55's regression lock — 4 static SQL-text assertions that do run credential-less, plus 1 live-BigQuery behavioral test gated the same way). Coverage is still real risk: every classification/regime-inference asset besides these two locked cases, every Streamlit service function, and every ingestion script still has zero automated coverage. Priorities 2 through 4 below remain genuinely open, not superseded by this.

## Priority 1 — golden-file regression tests for classification logic

**Partially done.** The ACLED half shipped as TD-08's Layer B (`tests/test_acled_pressure_regimes_golden.py`, fixtures at `tests/fixtures/acled_regimes_golden/`, covering the Finance Bill 2024 and Jan–Feb 2008 windows) — a drift check against already-validated materialized BigQuery output, not a rerun of the classification SQL against frozen inputs (that stronger design, "Layer A," is blocked on TD-39's test-isolation infrastructure gap and deliberately deferred; see `decision-log.md`'s 2026-07-05 entry for the full reasoning). The OONI-side equivalent has a recorded design (Layer B, aggregate-count fixtures over the Finance Bill 2024 window and a quiet control window, per `decision-log.md`'s 2026-07-06 entry) but is not yet built — `test_ooni_dns_bogon_classification.py` locks TD-55's specific dnscheck fix, which is a narrower regression lock, not the general OONI classification golden-file test this priority originally called for.

The original approach recorded here remains correct and is what TD-08 followed: pick a small number of known historical incidents with an already-understood expected outcome (the Finance Bill 2024 window is the obvious first case, since it is already the basis of the flagship report). For each, write a test that runs the relevant asset against a fixed input snapshot — or, per TD-08's Layer B precedent, a drift check against already-verified live output — and assert the result matches a recorded expected value (regime label, confidence value, guardrail flags). This is what would have caught the `upgraded_assets` regression found during the original review (Technical Debt Inventory TD-30, the `methodology_risk_level` condition that can never evaluate true) before it had a chance to be merged back into the canonical asset.

## Priority 2 — a lineage-consistency check

Nothing today verifies that an asset's declared `@bruin` `depends:` header matches what its SQL body actually selects from or joins against. This is exactly the gap that made the Architecture Assessment's central open question (whether `intelligence.acled_pressure_regimes` is consumed by any reporting mart) something that had to be investigated by hand rather than confirmed automatically. A lightweight script comparing declared dependencies against a static scan of `FROM`/`JOIN` references in each asset's SQL body would close this gap and should run in CI alongside `ruff` and `pytest`.

## Priority 3 — contract tests for reporting marts

Extend the existing `contracts.py` pattern (already well-designed and already tested) to cover the four reporting marts that `streamlit/services/marts.py` queries directly, asserting shape and type expectations at that boundary the same way the Streamlit-side validation already does, but checked at the SQL/BigQuery level rather than only after the data reaches Python.

## Priority 4 — a synthetic-data provenance test

**Precondition met, test still not written.** TD-01's `source_authenticity`/`is_synthetic` flag now exists (resolved 2026-07-05, propagated via `LOGICAL_OR` from `stg.lumen_requests` through both consumer branches to `fact_country_pressure_daily` and both reporting marts) — the "once...exists" framing this priority was originally written under no longer applies. No dedicated test asserts the flag survives the pipeline; this remains open exactly as scoped.

## What this strategy does not include, and why

This does not propose full unit-test coverage of every SQL asset immediately, nor a generic testing framework beyond what `pytest` and Bruin's own check mechanism already provide. Given the current near-zero baseline, coverage of the four priorities above — tied to known real incidents and known real risks, not abstract completeness — will catch more actual regressions per hour invested than a broad, generic test-writing pass would.

## CI integration

`.github/workflows/tests.yml` runs `pytest -q` on every push and PR to main, but **no GCP credentials are configured in that workflow** — confirmed directly, not assumed, by reading the workflow file. This means only the credential-less tests actually execute in CI today (`test_contracts.py` in full, plus the static SQL-text assertions in `test_ooni_dns_bogon_classification.py`); both golden-file suites' live-BigQuery assertions are gated behind `RUN_BIGQUERY_TESTS=1` and self-skip in CI, running only when someone remembers to set that variable locally. Wiring Workload Identity Federation into `tests.yml` (the same pattern already proven in `gcp-auth.yml` and `staleness-check.yml`) would close this gap cheaply and is recorded as the recommended near-term fix in `technical-debt-inventory.md`'s TD-39 entry. Priorities 2 and any newly-written OONI golden-file tests (Priority 1) should be added to this same workflow as they are written, rather than introducing a second test-running mechanism.
