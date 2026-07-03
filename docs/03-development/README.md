# 03-development

**Why this folder exists:** how to set up, contribute to, test, and document
work on CLIO. This is process, not product or architecture content.

**Who reads it:** any contributor, including a future second engineer.

**When it's used:** onboarding, and any new asset, PR, or documentation
change.

## Files (planned)

- `CONTRIBUTING.md` — setup, branching strategy (trunk-based, short-lived
  feature branches), review process, and the "determine ownership before
  writing" rule generalized from documentation to code.
- `testing-strategy.md` — what is tested today (`tests/test_contracts.py`
  only, covering the Streamlit contract-validation helper) and, explicitly,
  what is not (the classification/regime logic in the SQL intelligence
  layer). Should define the golden-file regression test plan tied to known
  historical incidents (e.g. the Finance Bill 2024 window) recommended in
  `CLIO_Project_Zero_Review.docx` Section 6, item 8.
- `documentation-standards.md` — the documentation policy from
  `CLIO_Project_Zero_Review.docx` Section 7: every feature documents
  rationale, implementation, tests, assumptions, limitations, and future
  work; ADR template; experiment record template; retrospective template;
  API-before-release rule; the Methodology Changelog (separate from the
  general code changelog); and the Data/Metric Dictionary.

## Status

Not yet populated.
