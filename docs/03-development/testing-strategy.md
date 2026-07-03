# CLIO Testing Strategy

Status: Phase 1 deliverable, CLIO Engineering Reset. Replaces the earlier stub written during the Project Zero Review with the specifics gathered during the engineering-first pass.

## Current state — stated plainly

`tests/test_contracts.py` is the only test file in the repository: roughly seventy lines, four tests, covering only `streamlit/core/contracts.py` (the schema-validation helper). Every other module — every SQL classification and regime-inference asset, every Streamlit service function, every ingestion script — has zero automated test coverage. This is not a judgment on the code's quality (much of it, especially the OONI path and ACLED path A, is genuinely well-designed); it is a statement about what would and would not catch a regression today. Nothing would.

## Priority 1 — golden-file regression tests for classification logic

The highest-risk untested code is the classification and regime-inference logic in `int.acled_event_classification.sql`, `features/acled_pressure_signals.sql`, `intelligence/acled_pressure_regimes.sql`, and the equivalent OONI-path assets. These carry the most business and, given the product's evidentiary claims to legal and journalistic buyers, legal risk of any code in the system.

Approach: pick a small number of known historical incidents with an already-understood expected outcome (the Finance Bill 2024 window is the obvious first case, since it is already the basis of the Minimum Lovable Product). For each, write a test that runs the relevant asset against a fixed input snapshot and asserts the output matches a recorded expected result (regime label, confidence value, guardrail flags). This is what would have caught the `upgraded_assets` regression found during this review (Technical Debt Inventory TD-30, the `methodology_risk_level` condition that can never evaluate true) before it had a chance to be merged back into the canonical asset.

## Priority 2 — a lineage-consistency check

Nothing today verifies that an asset's declared `@bruin` `depends:` header matches what its SQL body actually selects from or joins against. This is exactly the gap that made the Architecture Assessment's central open question (whether `intelligence.acled_pressure_regimes` is consumed by any reporting mart) something that had to be investigated by hand rather than confirmed automatically. A lightweight script comparing declared dependencies against a static scan of `FROM`/`JOIN` references in each asset's SQL body would close this gap and should run in CI alongside `ruff` and `pytest`.

## Priority 3 — contract tests for reporting marts

Extend the existing `contracts.py` pattern (already well-designed and already tested) to cover the four reporting marts that `streamlit/services/marts.py` queries directly, asserting shape and type expectations at that boundary the same way the Streamlit-side validation already does, but checked at the SQL/BigQuery level rather than only after the data reaches Python.

## Priority 4 — a synthetic-data provenance test

Once a `source_authenticity`/`is_synthetic` flag exists for the Lumen path (Technical Debt Inventory TD-01), add a test asserting that flag is never silently dropped between `stg.lumen_requests` and any mart or report that touches Lumen-derived figures.

## What this strategy does not include, and why

This does not propose full unit-test coverage of every SQL asset immediately, nor a generic testing framework beyond what `pytest` and Bruin's own check mechanism already provide. Given the current near-zero baseline, coverage of the four priorities above — tied to known real incidents and known real risks, not abstract completeness — will catch more actual regressions per hour invested than a broad, generic test-writing pass would.

## CI integration

`.github/workflows/tests.yml` already runs `pytest -q` on every push and PR to main. Priorities 1 and 2 above should be added to this same workflow as they are written, rather than introducing a second test-running mechanism.
