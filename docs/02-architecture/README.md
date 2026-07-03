# 02-architecture

**Why this folder exists:** the canonical technical description of CLIO and
the durable record of why structural decisions were made.

**Who reads it:** developers and technical partners.

**When it's used:** onboarding, and any structural or architectural change.

## Files (planned)

- `architecture-reference.md` — layer map (ingestion → staging →
  intermediate → features → intelligence → marts → dashboard), known critical
  code findings, and the API-endpoint-to-mart mapping. To be migrated and
  condensed from `KCLIO_Master_Platform_Document.docx` and
  `Repo Strategic Technical Analysis.docx`.
- `ai-architecture-principles.md` — the three-layer AI contract (grounded
  retrieval, provenance tagging, hypothesis separation), knowledge artifact
  schemas, and prompt contract rules. To be migrated largely as-is from
  `AI_ARCHITECTURE_PRINCIPLES_md.docx`, which is already mature.
- `data-lineage.md` — the required lineage path (raw → staging → intermediate
  → features → intelligence → mart → report) and what each stage must expose
  (source asset, upstream dependencies, methodology version, reporting
  version).
- `adr/` — Architecture Decision Records. One file per decision: title,
  status, context, decision, consequences. Numbered sequentially. A decision
  is superseded by a later ADR, never edited in place. See
  `docs/03-development/documentation-standards.md` for the template.

## Status

Not yet populated. See `CLIO_Project_Zero_Review.docx` Section 1 (Technical
Assessment) for the independent engineering findings this folder should
incorporate, including two previously unrecorded issues: dependency lockfile
drift (`duckdb` pinned inconsistently between `Bruin/requirements.txt` and
`uv.lock`) and a Python version mismatch between the devcontainer and
`pyproject.toml`. The first ADR written should probably resolve the
confidence-scoring duplication described in that section.
