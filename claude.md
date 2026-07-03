# CLAUDE.md — CLIO Project Handbook

This file orients any future Claude session working in this folder. Read it first, before opening anything else.

## What CLIO is, in one paragraph

CLIO (Kenya Civil Liberties Intelligence Observatory) fuses internet-censorship measurement (OONI), conflict event data (ACLED), and platform/legal takedown-pressure signals (Google Transparency Report, Lumen Database) into attributed, confidence-qualified findings about civil-liberties pressure in Kenya. It is a Bruin-orchestrated BigQuery pipeline (raw → staging → intermediate → features → intelligence → marts → reporting) with a read-only Streamlit dashboard on top.

## The project has two completed phases behind it — know which one you're in

1. **The Constitution Project** (complete, frozen, historical context only). A philosophical/scientific inquiry into what CLIO's recurring engineering patterns might imply about evidence, uncertainty, and reasoning as a general discipline. Its conclusion, stated plainly by its own final document: CLIO is not currently a general reasoning architecture, most of what looked novel reduces to existing fields (metrology, database provenance theory, psychometrics, epistemology), and further progress requires operational evidence, not more theory. **Do not extend, rewrite, or treat these documents as implementation specifications.** They now live in `clio_constituion_project/` at this folder's root (moved there by the project owner, not by any automated process): the eight `.docx` files from Deliverable 1 through the Executive Summary. Indexed, not duplicated, at `docs/04-research/README.md`.
2. **The CLIO Project Zero Review** (complete). The first implementation-focused review — technical, product, commercial, strategic, and competitive assessment of the actual repository and business documents, plus the `docs/00-06` documentation structure this project now uses. Lives at `CLIO_Project_Zero_Review.docx`, with its commercial/product content split into `docs/01-product/` and `docs/05-business/`.
3. **The CLIO Engineering Reset** (this phase, current). From here forward, CLIO is first and foremost a software engineering project. The Constitution explains why certain ideas exist; it does not dictate what to build. Engineering decisions come from the current codebase, the product goals, and evidence gathered during implementation.

## Where things live

- `docs/00-overview/` — start here for the documentation map; `documentation-plan.md` explains the two different "docs/" folders in this project (this working folder's structure vs. the Bruin repository's own internal `docs/`) and disambiguates them explicitly — read that distinction before assuming any `docs/` reference means the same thing twice.
- `docs/01-product/`, `docs/05-business/` — commercial and product content, from the Project Zero Review.
- `docs/02-architecture/` — the engineering core: `architecture-assessment.md`, `technical-debt-inventory.md`, `methodology-consistency-review.md`, `implementation-roadmap.md`, `decision-log.md` + `adr/`.
- `docs/03-development/` — `coding-standards.md`, `testing-strategy.md`, `documentation-standards.md`. Read before writing any new code or documentation.
- `docs/04-research/` — frozen index to the Constitution and the repository's own canonical research docs. Do not extend.
- `docs/06-operations/` — stub, pending future work.
- `Archive/` — superseded strategy and governance documents, archived (not deleted) with an explanation in `Archive/README.md`.
- `Civil-Liberties-and-Censorship-Analysis-with-Bruin-main.zip` — the actual codebase, as a zip snapshot (no `.git` history — this is a downloaded snapshot, not a clone).
- `upgraded_assets/` — uncommitted variant ACLED SQL, **not safe to merge as-is** (see below).

## Facts every session should know before touching code

- **The single most important open question:** no `reporting/*` asset's declared Bruin dependency references the sophisticated, stateful ACLED regime engine (`intelligence.acled_pressure_regimes`). The dashboard's national pressure score appears to come from a simpler, unguarded legacy path instead. Unconfirmed — verify by reading the SQL bodies directly, not just declared headers, before assuming either way. This is Step 0 of `docs/02-architecture/implementation-roadmap.md` for a reason: everything else depends on the answer.
- **Lumen data is entirely synthetic.** `scripts/lumen_parquet.py` fabricates 5,000 rows with `np.random.seed(42)`. Nothing downstream flags this. Do not treat any Lumen-derived figure as real evidence, and do not let a report cite one, until a provenance flag exists.
- **A confirmed `CROSS JOIN` bug** in `streamlit/services/marts.py`'s `get_finance_bill_incident()` inflates row counts and misattributes ASN data whenever more than one ASN matches `network_class = 'MAJOR_KENYA_PROVIDER'`.
- **Two unreconciled confidence-scoring schemes** coexist (a governed dimension-table scheme vs. inline literals in `int.ooni_experiment_results.sql`) — see ADR-0001.
- **`upgraded_assets/` contains a real regression, not an upgrade.** Its `int.acled_event_classification.sql` variant reintroduces a bug the canonical file's comments describe fixing (`methodology_risk_level` computed from a condition that can never be true). Its `acled_pressure_signals.sql` variant reverts per-family baseline gating, the calendar spine, and a deliberately-corrected `stddev_floor`. Do not merge any file from this folder without diffing it against canonical first.
- Dependency lockfiles disagree: `Bruin/requirements.txt` pins `duckdb==0.10.0`; `pyproject.toml`/`uv.lock` require/resolve `1.5.0`. The devcontainer's Python 3.11 base image contradicts `pyproject.toml`'s `>=3.12.3` requirement.
- The only test file in the repository is `tests/test_contracts.py`, covering the Streamlit contract-validation helper only. The classification and regime-inference logic — the code with the most business and legal risk — has zero behavioral test coverage.

## Engineering principles for this project

Prefer understanding over speed. Prefer architectural consistency over local optimization. Minimize unnecessary complexity; do not introduce an abstraction before at least two concrete cases justify it. Document every significant engineering decision as an ADR. Preserve historical reasoning where useful, but do not let a historical document dictate an implementation choice if better evidence exists now. If an existing design is already good — the OONI evidence/interpretation separation, the ACLED path A confidence/risk split, `streamlit/core/contracts.py` — preserve it and say so; do not rewrite something that already works. If something should change, name exactly why, with a file and line reference, not a general impression.

## Recommended reusable skills for this project

Architecture review (read-only, module-boundary-first, flags open questions rather than assuming answers); methodology/dataset validation (trace a source end to end, rank inconsistencies by severity before proposing fixes); technical debt triage (itemize with location, severity, recommended action); ADR authoring; release preparation adapted to the Bruin/BigQuery deployment model; refactoring-under-test (require a golden-file test before touching classification logic). See `docs/00-overview/documentation-plan.md` for detail on each.

## Before starting implementation work

Read `docs/02-architecture/implementation-roadmap.md` and start at Step 0. It is two verification tasks, not a redesign, and the rest of the roadmap is sequenced on their answers.
