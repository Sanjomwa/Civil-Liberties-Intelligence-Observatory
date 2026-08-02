# llm_extraction/ — OTF-04 LLM Extraction Prototype

CLIO's first AI/LLM component. Given a real news article about a Kenyan protest, an LLM (OpenAI's `gpt-5.4-mini`) extracts discrete, location-specific events as structured JSON, and a separate, deterministic, non-LLM checker (`grounding_check.py`) verifies every claimed quote actually appears in the source article before it is trusted.

See [`docs/02-architecture/adr/0009-llm-extraction-layer-non-merge.md`](../docs/02-architecture/adr/0009-llm-extraction-layer-non-merge.md) for the full design decision and reasoning.

## Scope — read this before citing anything this component produces

This is a **prototype proving the extraction-and-grounding mechanism works.** It is:

- **Not** a claim that any coverage gap has been closed. That would require a separate, manual audit — not part of this component.
- **Not** a predictive or leading-indicator claim. This project already found it cannot statistically support one, given how few historical crisis windows Kenya has.
- **Not** merged into, or a substitute for, any existing CLIO score. `composite_pressure_score`, `fact_country_pressure_daily`, and the ACLED regime engine's output are all untouched by this component and always will be, unless a future ADR explicitly supersedes ADR-0009.

Every record this component produces carries `llm_derived: true` and lives only in its own dedicated BigQuery dataset (`llm_derived.article_extractions`) — never in any existing CLIO table.

## Governance rules this design follows

Restated in full in ADR-0009 (this repo's `docs/07-governance/` is gitignored, so the ADR is written to be self-contained rather than depend on a file that may not exist in every checkout):

1. **Methodology-conformance** — every AI-generated factual claim must be traceable to a verifiable primary source, or explicitly disclosed as unverifiable.
2. **Disclosure and non-merge** — AI output is its own separate, labeled item (`llm_derived: true`, own dataset), with mandatory verbatim-quote grounding checked programmatically, never trusted from the model. Never joined into an existing CLIO composite without a future ADR.
3. **Scope-discipline** — stays inside CLIO's actual mission: Kenya pilot, evidence fusion, not prediction, not general-purpose, not multi-country.

## How it works

```
source_articles_manifest.json (tracked)      -- provenance + SHA-256, no article body text
source_articles_cache/ (gitignored)           -- actual copyrighted article body text, local only
        |
        v
fetch_articles.py    -- ensures the cache is populated, verifying hash against the manifest
        |
        v
extract_openai.py    -- gpt-5.4-mini, structured outputs (strict JSON schema)
        |
        v
grounding_check.py   -- checks every verbatim_quote (and approx_participants) against
                         the real source text: MATCHED / FUZZY / NOT_FOUND
        |
        v
run_extraction.py    -- orchestrates the above, writes output/otf04_extractions.{jsonl,csv},
                         then appends to BigQuery (llm_derived.article_extractions)
```

`setup_bigquery.py` and `ci_check_no_merge.py` are the two independent halves of the non-merge guarantee: the former keeps this component's only BigQuery footprint in a dataset with no other CLIO consumer; the latter is a CI-enforced grep over every Bruin SQL asset making sure none of them ever reference `llm_derived`.

## Running it

### 1. Install dependencies

```bash
pip install -r llm_extraction/requirements.txt
```

### 2. Run the offline tests first — no API key required

This is real, offline evidence the grounding mechanism itself is sound, independent of whether any live extraction has been run.

```bash
pip install pytest --break-system-packages   # if not already installed
pytest llm_extraction/tests/test_grounding_check.py -v
```

Expect **14/14 passed**. Note: this repo's `pyproject.toml` scopes `pytest -q`'s default discovery to `tests/` only, so `llm_extraction/tests/` is deliberately not picked up by a bare `pytest -q` run at the repo root — this component's tests are isolated from the main app's test contract by design, matching its isolation from the main pipeline. Always invoke with the explicit path shown above.

### 3. Set up the BigQuery destination (once, or safely re-run any time)

```bash
python llm_extraction/setup_bigquery.py
```

Creates `llm_derived.article_extractions` if it doesn't already exist (`exists_ok` semantics — safe to re-run).

### 4. Add your OpenAI API key

Add to this repo's `.env` (already gitignored):

```
OPENAI_API_KEY=sk-...
```

`run_extraction.py` and `extract_openai.py` load it via `python-dotenv`, the same convention `streamlit/core/config.py` already uses (`load_dotenv(REPO_ROOT / ".env")`). Missing key → loud failure, nonzero exit, never a silent no-op.

### 5. Run the extraction

```bash
python llm_extraction/run_extraction.py
```

This will:
- ensure both seed articles are cached (`fetch_articles.py`, only fetches what's missing),
- call `gpt-5.4-mini` once per article,
- ground every claimed quote against the real source text,
- write `llm_extraction/output/otf04_extractions.jsonl` and `.csv` (gitignored — run output, not source),
- append the same records into BigQuery,
- print a grounding summary (MATCHED / FUZZY / NOT_FOUND counts and percentages).

**Never run this via `bruin run`.** It's not a Bruin asset and never will be — see ADR-0009 for why (LLM calls are nondeterministic and billed per invocation; Bruin's rebuild model would silently re-invoke and re-bill them).

## Reviewing output

- `MATCHED` — verbatim quote confirmed present in the source article. Treat as verified.
- `FUZZY` — a high-similarity but non-exact match. `review_status` is set to `pending_human_review`. Never auto-accept.
- `NOT_FOUND` — no defensible match. Treat as a failed extraction, not a fact.

## The non-merge guarantee, concretely

- All output lives in `llm_derived.article_extractions` only — a BigQuery dataset with zero other CLIO consumers.
- `llm_extraction/ci_check_no_merge.py` runs in CI (`.github/workflows/tests.yml`) on every push/PR, grepping every `Bruin/assets/**/*.sql` file for the literal string `llm_derived`. The build fails if any Bruin asset ever references it.
- Any future request to join this output into `composite_pressure_score`, `fact_country_pressure_daily`, or the ACLED regime engine's output requires a new ADR that explicitly supersedes [ADR-0009](../docs/02-architecture/adr/0009-llm-extraction-layer-non-merge.md).
