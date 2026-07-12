# CLIO Documentation Standards

Status: Phase 1 deliverable, CLIO Engineering Reset. Replaces the earlier stub written during the Project Zero Review. This is a policy — what every future document should contain and where it lives — not a one-time document list.

## Every feature or asset documents six things

Rationale (why it exists), implementation (what it does, in plain language, with a pointer to the code), tests (what is covered and, explicitly, what is not), assumptions, limitations, and future work. For Bruin SQL assets, this maps directly onto the existing `@bruin` YAML description block — use it for all six, not just a one-line summary.

## Architecture Decision Records (ADRs)

Location: `docs/02-architecture/adr/`, one file per decision, numbered sequentially (`0001-`, `0002-`, ...). Format:

```
# ADR-000X: <Title>

Status: Proposed | Accepted | Superseded by ADR-000Y
Date: YYYY-MM-DD

## Context
What situation makes a decision necessary.

## Decision
What was decided.

## Consequences
What becomes easier, harder, or newly possible as a result.
```

A decision is superseded by a later ADR, never edited in place. See `docs/02-architecture/decision-log.md` for the running index, and `adr/0001-unify-confidence-scoring.md` for a worked example addressing Technical Debt Inventory item TD-05.

## Experiment records

Location: `docs/04-research/experiments/`. Format: hypothesis, method, data, result, decision, date, author. This folder is intentionally empty until the Constitution's Research Roadmap programme actually runs something — do not pre-populate it with aspiration.

## Retrospectives

`docs/project_difficulties.md`, inside the repository's own internal `docs/` folder, is already an informal version of this pattern and should be treated as the template to formalize going forward, not replaced or duplicated with a new file.

## APIs

Documented before release, not after: an OpenAPI/Swagger specification committed alongside any new endpoint, reviewed before merge.

## Methodology Changelog

A file separate from any general code changelog, recording every change to a threshold, confidence model, or classification rule with a version and effective date. This is the concrete artifact that makes "versioned methodology" — already a real practice in this codebase (`classification_methodology_version`, `feature_version`, `regime_methodology_version` all exist as literals) — into something a reader can review as a history rather than reconstruct from scattered comments. Recommended location: `docs/02-architecture/methodology-changelog.md`, created when the first methodology change happens under this policy.

## Data and Metric Dictionary

A living document listing every metric the system produces (name, description, owning asset, methodology version, source tables, update frequency, intended use, limitations) — elevating the "Intelligence Metric Registry" already proposed in the product strategy documents from optional to required. Recommended location: `docs/02-architecture/metric-dictionary.md`, populated incrementally rather than all at once.

## Two docs/ folders — always disambiguate

As stated in `docs/00-overview/documentation-plan.md`: this CLIO working folder's `docs/00-07` structure (`docs/07-governance/` was added 2026-07-11 and is in scope of this same distinction) and the Bruin repository's own internal `docs/` folder are different things. Any new document should state, in its first paragraph if there is any room for ambiguity, which one it belongs to.

## Ownership

Each `docs/0X-*/README.md` already states who reads that folder's content and when. New documents should be added to the folder matching their audience, not created ad hoc at the repository root — the loose top-level `.md`/`.docx` sprawl that existed before the Project Zero Review's reorganization is exactly the failure mode this structure exists to prevent.
