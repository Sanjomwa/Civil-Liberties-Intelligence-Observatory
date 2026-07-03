# CLIO Coding Standards

Status: Phase 1 deliverable, CLIO Engineering Reset. These are drawn from patterns already working well in the codebase, not imported from a generic style guide. Where the codebase already does something correctly and consistently, that pattern is written down here as the standard, not replaced with a different preference.

## General principles

- Prefer understanding over speed. Read the surrounding layer before adding to it — most of this codebase's genuine strengths (the OONI evidence/interpretation separation, the ACLED path A confidence split) came from someone taking the time to do this once, well.
- Prefer architectural consistency over local optimization. If a new data source integration does not follow the observation → classified-with-confidence → guarded-feature → inferred-regime shape used by OONI and ACLED path A, that is a decision that should be named and justified, not a default.
- Minimize unnecessary complexity. Do not introduce a shared abstraction (a base class, a generic contract, a plugin system) until at least two concrete cases exist that would use it. The `marts.py` schema-validation triplication (Technical Debt Inventory, general note) is tolerable duplication; a premature abstraction over six query functions with slightly different schemas would likely be worse.
- Every significant engineering decision gets an ADR (see `documentation-standards.md`). "Significant" means: it changes a data contract, changes which of two existing paths is authoritative, or would be expensive to reverse.

## SQL (Bruin assets)

- Every asset's `@bruin` YAML header states `depends:` completely and accurately. Declared dependencies are not currently verified against actual `FROM`/`JOIN` references anywhere in this codebase — until an automated check exists, treat keeping these two things in sync by hand as a required discipline, not a nicety.
- Confidence and risk are separate fields when both are meaningful. `int.acled_event_classification.sql`'s split of `classification_confidence` (how sure) from `methodology_risk_level` (how comparable across contexts) is the standard to match, not a one-off.
- Statistical guardrails (sparse-window, zero-variance, low-sample flags) are evaluated and exposed as explicit columns before any directional or regime classification is attempted, matching the OONI and ACLED path A pattern.
- Methodology version constants (`classification_methodology_version`, `feature_version`, etc.) are stated as literals in the asset for now, consistent with current practice, until the methodology governance layer (Architecture Assessment Section 7) exists. When it does, migrate to reading from that table rather than adding a fourth independent literal.
- Stateful, execution-order-dependent assets (in the style of `intelligence.acled_pressure_regimes`) must document their precondition in the header and, going forward, enforce it at runtime rather than relying on a comment alone (Technical Debt Inventory TD-04).

## Python (Streamlit, scripts, Bruin Python assets)

- Cached query functions in `streamlit/services/` route through `core.contracts.guard_dataframe_schema()` before returning data to a page — this is already universal practice and should stay that way.
- Do not swallow exceptions silently. `bq.py`'s bare `except Exception: return None` in secret parsing (TD-19) is the anti-pattern to avoid: log what was caught even when the function still degrades gracefully.
- Do not surface raw stack traces to end users in the public-facing dashboard (TD-20). Log server-side; show a generic, non-revealing message to the user.
- Deterministic, content-hashed identifiers (the pattern in `stable_measurement_id()`) are the standard for any new ingestion path needing a stable ID with no natural key.
- New local-ingestion scripts should not hardcode a platform-specific path as the only default (TD-11). Make the root path configurable with a documented default per platform, or detect the platform.
- Any script that maintains sync/resume state should persist that state to a file the script reads and updates itself, not a hardcoded literal a human edits before each run (TD-12).

## Streamlit pages specifically

- Match page 3's defensive normalization pattern (`_ensure_*_columns()` back-filling missing columns, safe NaN-tolerant formatting) as the standard for new pages, not the lighter `if df.empty: st.stop()` pattern used by pages 1/2/5/6. Page 3 is the highest-quality page in the set for a reason.
- Use `use_container_width=True` consistently; do not introduce `width="stretch"` or other newer API idioms without updating every page at once (TD-27).
- If a page's data-fetch function does not accept the sidebar date range (as with `get_asn_behavior()`, which queries a dateless snapshot mart), say so explicitly in a comment near the trust-strip call, rather than leaving a reader to wonder whether the omission is a bug.

## Infrastructure

- No long-lived downloadable service-account keys for anything beyond initial local setup (TD-13); prefer Workload Identity Federation or short-lived tokens for anything durable.
- IAM grants are scoped to the specific roles a principal needs, not `roles/editor` (TD-14), including for human admin accounts managed through Terraform.

## What not to do

- Do not rewrite the OONI path or ACLED path A's confidence/guardrail logic — both are already good and are the standard other paths should be brought up to, not changed.
- Do not build a generic "data source connector" abstraction before Google Transparency and Lumen are brought up to the same methodological standard as the two paths above. There are not yet enough well-understood cases to generalize from.
