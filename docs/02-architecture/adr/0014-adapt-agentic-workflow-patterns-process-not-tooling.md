# ADR-0014: Adapt selected agentic-workflow patterns at the process level, not the tooling level

- **Status:** Accepted (2026-09-16); pattern 2 refined the same day to add a Cowork-side grounding mechanism — see the addendum at the end of Option 2 below
- **Date:** 2026-09-13
- **Deciders:** Sam (sole owner)
- **Supersedes / Superseded by:** none
- **Related:** ADR-0007 (licensing/compliance register), `docs/07-governance/ai-output-governance.md` (TD-69), TD-08 (golden-file tests), the no-autonomous-commit-or-push standing rule and the model-routing policy, both in `CLAUDE.md`

---

## Context

Sam watched a YouTube walkthrough by Kun Chen (ex-Meta/Microsoft/Atlassian L8, now building open-source "agentic engineering" tooling) demonstrating a personal multi-agent development workflow, and asked whether CLIO should adopt it. The tooling is real and was verified directly against `github.com/kunchenguid` rather than taken from the video's narration: all four projects exist, are MIT-licensed, and are actively maintained with real release histories and contributor counts.

- **firstmate** (Shell) — an "agent distro" rather than an app. You clone it, launch a supported coding-agent harness inside it, and that session becomes your sole point of contact (the "first mate"). It dispatches "crewmates" — autonomous agent sessions, each in its own disposable git worktree via a bundled worktree manager ("treehouse") — supervises them to completion with an event-driven zero-token watcher, and reports back finished PRs, approved local merges, or standalone investigation reports ("scout" vs. "ship" tasks). Larger portfolios can add persistent "secondmates": domain-owning sub-first-mates, optionally on a separate always-on machine. Each project declares a trust tier (`no-mistakes`, `direct-PR`, `local-only`) with an optional `+yolo` flag permitting the first mate to merge on its own judgment. Built-in skills include `/bearings` (a bounded digest of fleet state: shipped, underway, waiting on you) and `/ahoy` (recap since your last message, then walk through open decisions one at a time in agent-judged impact order). An opt-in "Relay" answers public @-mentions on Discord/X through the same request lifecycle as chat.
- **no-mistakes** (Go, 153 releases, 72 contributors) — a local git proxy. `git push no-mistakes` instead of `git push origin`: disposable worktree, AI-driven validation pipeline (review → test → docs → lint), safe mechanical fixes applied automatically, anything touching author intent escalated to a human TUI decision, and only once fully green does it forward the branch to the real remote and open the PR itself.
- **quota-axi** (TypeScript) — exposes remaining LLM subscription quota windows to an agent, so dispatch can route work to whichever vendor has spare capacity.
- **lavish-axi** (JavaScript, "HTML is the new markdown") — an interactive HTML artifact format for human review: a crewmate that produced several visual prototype variants renders them into one comparison board with previews and a recommendation; the human clicks a choice, which returns to the crewmate as feedback.

**The decisive context is not the tooling's quality — it is that the demo's economics are the inverse of CLIO's.** Kun operates ~36 mostly personal/open-source projects across several simultaneous paid model subscriptions (Claude, Codex, Cursor, Grok), running 7+ concurrent agent sessions and routing work to whichever vendor has quota left. In that setting quota is a *renewable, use-it-or-lose-it* resource per window, parallelism is nearly free, and a ~2000-person Discord supplies a steady inbound stream of work worth automating.

CLIO's position on every one of those axes is the opposite:

1. **Budget is depleting, not renewing.** The Fable 5.1 allocation is a scarce budget on a countdown, not a rolling window, and Anthropic usage generally is grant money on a solo project — there is no second vendor subscription to spill into. The correct policy for a depleting budget is *deliberate scarcity*; the correct policy for a renewing window is *opportunistic exhaustion*. Tooling built for the second is actively wrong for the first.
2. **The funder polices scope.** OTF checks workload plausibility for a solo researcher and redirects oversized fellowship scope into a worse-funded grant path. CLIO has already used this constraint once, to reject "three countries in parallel" in favour of "swap one in." A workflow whose central affordance is "run more agents at once" cuts against the project's funding incentives, not merely its wallet.
3. **The bottleneck is Sam's review attention, not agent capacity.** Work is essentially sequential: one repository, one live Codespace session at a time, one reviewer. Because the commit/push step is a mandatory human act (see 4), added parallelism raises work-in-progress and review queue depth without raising throughput.
4. **The commit/push policy is fixed and is not in scope for this ADR.** No Claude session — Cowork or live Codespace — runs `git commit` or `git push`, or drafts suggested commit-message text. The live session's job ends at making changes, verifying them, and reporting factually; Sam commits and pushes by hand, every time. This is a deliberate legitimacy decision about whose hand is on the mechanism of record, not a technical default awaiting a convenient exception. It is not about concealing AI assistance, which is openly disclosed via the AI-output-governance contract.
5. **There is no community to serve.** No Discord, no public bug inbox, no outside contributors. All external communication is already governed by its own standing practice (gracious/human tone, first-person singular, an AI-proofing pass before anything goes out).
6. **CLIO already has two bespoke, proven verification rituals — unnamed.** The golden-file fixtures guarding the ACLED regime classifier (TD-08), and the docx-editing ritual used to correct a date in the methodology whitepaper (unzip, merge runs, `str.count()==1` assertion before replacement, rezip, XSD/paragraph-count validation, PDF render, `pdftotext` to locate the page, page-to-image render, visual confirmation). Both work. Neither is written down as a general rule, so there is no stated answer to "which artifacts get this treatment and which don't" — it gets re-derived, or forgotten, each time.

So the question this ADR answers is not "is this workflow good?" — it evidently is, for its author's situation — but "which of its *patterns* survive translation into a one-person, review-bound, depleting-budget project, and which of its *mechanisms* must be refused even where the pattern is kept?"

## Decision

CLIO adopts a small number of these ideas **at the process level and rejects them at the tooling level.** No new dependency (firstmate, no-mistakes, quota-axi, lavish-axi) is installed; nothing is added to the repo's dependency surface, devcontainer, or CI. What is adopted is expressed as markdown policy, a dispatch template, and one on-demand digest ritual, built on infrastructure CLIO already has (the Cowork/Codespace split, relay prompts, `reports.md`, and the three tracking documents).

Specifically: the single-liaison + bounded-dispatch pattern is formalized as CLIO's own named practice; a `/bearings`-equivalent decision digest is added because it is net-new value and costs nothing; the verification-rigor tiers CLIO already practises de facto are written down as explicit policy; and `no-mistakes`'s staged review→test→docs→lint *shape* is adopted as a pre-handback checklist. **The auto-forward / auto-PR / auto-merge tail of `no-mistakes`, and firstmate's `+yolo` trust tier, are rejected permanently and categorically** — the verification logic is welcome, the push action stays a human act. Quota-driven routing, multi-machine fleets, public-mention relay, and interactive HTML review boards are rejected with reasons recorded below, so that a future session can re-open them on changed facts rather than rediscover them.

## Options Considered

### 1. Single-liaison + bounded dispatch — **Adopt (name and formalize what already exists)**

CLIO already runs firstmate's core shape without the name: the Cowork session is the continuous context-holder and sole thing Sam talks to; the Agent tool's model-override parameter dispatches bounded advisory/synthesis "crewmates" (this ADR draft is one); the live Codespace Claude Code session is the one agent permitted to touch the repository. The gap is that this is tacit, so its invariants are not checkable.

Adopt by naming the three roles, their permitted actions, and — the part worth borrowing most — firstmate's insistence on **bounded state**. CLIO's fleet state is not in a daemon; it is `decision-log.md`, `technical-debt-inventory.md`, `implementation-roadmap.md`, and the durable planning-side `reports.md`. Saying so explicitly is what makes pattern 2 possible.

**One refinement beyond the source material, flagged for Sam's decision rather than decided here.** The genuinely valuable mechanism in treehouse/crewmates is *isolation*: a speculative change lives in its own worktree and never contaminates the tree you review. CLIO has no equivalent — a half-finished or abandoned Codespace change sits in the same working tree Sam must review, mixed with the work he actually wants. Plain `git worktree` is a git builtin, needs no new tooling, and creates no commit and no push — so it is not obviously in tension with the standing rule. It does create a branch ref, which is a repo-state mutation, so this should be Sam's call, not an agent's inference from the rule's wording. **Recommendation: ask, don't assume**; if approved, it is a one-line addition to the relay-prompt template for high-blast-radius or speculative work only.

### 2. Relay-prompt template (dispatch *boilerplate*, not dispatch *automation*) — **Adopt; highest expected value of anything here**

Not in the preliminary sort, and it should be. firstmate automates dispatch; CLIO hand-drafts every relay prompt, and that hand-drafting has already failed in a recorded way: the "overwrite `reports.md`, don't append" instruction was missing for several sessions running, and the live-session-can't-see-planning-files lesson had to be learned the hard way on the TD-66 prompt. Both are boilerplate-omission failures, not reasoning failures.

The fix is a template — a Cowork-side skill or checklist emitting the invariant scaffolding every relay prompt needs: no commit, no push, no drafted commit message; overwrite `reports.md` at the start and add it to `.gitignore`; advisor consults in the live environment call **Opus 4.8**, not Opus 5; restate inline anything living only in the planning workspace; update `decision-log.md` / `technical-debt-inventory.md` / the relevant ADR in the same change as the fix. Zero infrastructure, and it closes an already-observed, already-repeated defect.

**Addendum, 2026-09-16: the same boilerplate-omission failure exists on the Cowork side, not only in relay prompts to the live Codespace, and pattern 2 is extended to cover it.** Found while comparing CLIO's practice against an external "context graph" pattern (Astronomer's decision-tracing architecture for AI agents, reviewed the same day): before that pattern's agent drafts a new response, it calls a tool that retrieves prior human decisions and their stated reasoning on similar past cases. CLIO has no structural equivalent — when this planning environment dispatches an Agent-tool advisory consult (Opus or Fable) asking it to decide, design, or diagnose something, nothing requires the dispatch to first check `decision-log.md`/`technical-debt-inventory.md` for directly relevant prior entries and hand them to the advisor. CLAUDE.md already says to check those files "before assuming a question hasn't been thought through," but that instruction is self-reported and has already failed silently at least twice on record: the "Facts every session should know" section going stale, and a same-day mix-up where a relay prompt named "Opus 5" when the correct, already-written answer for the live environment was "Opus 4.8," caught only because Sam happened to notice.

Verified via an Opus 5 advisory dispatch (design only, applied by Sonnet after independent verification, per this project's own advisory discipline). The mechanism, now part of pattern 2's scope:

- **Trigger.** Not every dispatch — most consults (AI-tell passes, proofreading, cold external research) have no relevant history to ground against. Mandatory grounding applies when a dispatch asks the advisor to *decide, design, or diagnose* — as opposed to verify a fact or polish prose — **and** the topic touches an existing TD number, ADR number, or a named CLIO concept with recorded history (path A/B, Extension A, model routing, the commit/push rule, a guardrail/oracle mechanism, `reports.md`, etc.), or could plausibly produce a recommendation contradicting something already settled.
- **The check.** Three targeted greps, no new files: `technical-debt-inventory.md`'s severity tables (already a one-line-per-TD index) filtered by topic keyword, read the matched `## TD-NN` sections only; `decision-log.md`'s ADR index table (cheap, ~20 rows, read whole every time) plus a keyword grep over its dated `###` narrative headings, read the matched entries only; `implementation-roadmap.md` only if the topic is sequencing.
- **How it reaches the advisor.** Quoted inline in the dispatch prompt, with file and line numbers — not a path handed to the advisor to go Read itself, since that reproduces the exact initiative-dependence this mechanism exists to remove, and quoting a few entries is cheaper than a cold subagent re-reading a multi-thousand-line file.
- **What makes it stick, where the existing prose instruction didn't.** Every such dispatch prompt carries a mandatory three-state field: `Prior decisions checked: [quoted below] / [checked, none found] / [not checked — reason]`. Three states, not two — "nothing was there" and "nobody looked" must be distinguishable or the field is decorative. The dispatch prompt instructs the advisor to flag a missing or "not checked" block in its first sentence and answer anyway, so a skipped step surfaces in the text Sam actually reads rather than disappearing silently. When the consult is logged to `decision-log.md` afterward (already standard practice for every consult), that entry names which prior entries were handed over, making a skipped step findable after the fact too.
- **No new durable artifact.** The grep is run fresh each time; no persisted "topics and their prior decisions" index is created, consistent with pattern 3's restriction against a fourth derived file competing with the three authoritative ones.
- **Scope note.** This governs Cowork-side Agent-tool dispatches specifically. The live-Codespace-facing half of pattern 2 (no-commit/no-push, `reports.md` overwrite, Opus 4.8 naming, etc.) is unchanged and still a separate action item.

### 3. `/bearings` + `/ahoy`-style decision digest — **Adopt, with one restriction**

Real net-new value: today, answering "what is actually open and undecided?" requires re-reading three long documents. A digest that surfaces open TD items, undecided roadmap steps, and narrative-log entries awaiting a call is a markdown ritual, not infrastructure.

The more valuable half is `/ahoy`'s, not `/bearings`'s: *one open decision at a time, ordered by impact*, rather than a flat dump. CLIO already has an ordering key for this in its existing backlog-tiering policy, so the ordering need not be invented.

**Restriction, tied to a specific past failure:** firstmate optionally writes bearings to a dated report file. CLIO must not, or must write it only to the disposable `reports.md`-class location. This project has already been burned by exactly this failure mode — `CLAUDE.md`'s "Facts every session should know" section went stale as a derived summary while its sources stayed current, which is why that section is now explicitly labelled a non-synced highlight reel. A durable bearings file would be a fourth derived artifact competing with three authoritative ones. Derive on demand; never persist as a source of truth.

### 4. Two-tier verification-rigor policy — **Adopt, but as three tiers keyed to failure mode, not two keyed to artifact type**

The preliminary sort proposed "full treatment vs. light touch." That understates what CLIO actually does, because the golden-file ritual and the docx ritual are not one tier applied to two artifact types — they defend against different failure modes and use different techniques. Proposed framing:

- **Tier A — silently-wrong-number risk.** Analytical logic whose failure produces a plausible but false figure: classification/regime SQL, features, marts feeding the dashboard or any published finding. Required: recorded golden fixtures for a known-good window before the change, re-materialization after, fixture comparison. This is TD-08 generalized.
- **Tier B — already-in-someone-else's-hands risk.** Artifacts that leave the workspace or are hard to correct after the fact: OTF deliverables, the methodology whitepaper, incident reports, published PDFs/docx, outreach messages. Required: exact-occurrence-count assertion before any in-place edit, structural validation after, render-and-visually-confirm the specific affected page. This is the docx ritual generalized. External-facing text additionally passes the existing AI-proofing check — that stays where it is and is not restated here.
- **Tier C — cheap-to-detect-and-revert.** Planning docs, comments, dashboard cosmetics, scaffolding. Normal care; no ritual.

Keying tiers to failure mode rather than file extension is what makes the policy extensible: a new artifact class gets classified by asking "if this is wrong, does it produce a confident false number, or does it reach a third party?" **Location:** this belongs in `docs/03-development/testing-strategy.md`, with a one-line pointer from `CLAUDE.md` — not pasted into `CLAUDE.md`, which is already long and whose own synchronization fragility is documented.

### 5. `no-mistakes`'s staged pipeline **shape** — **Adopt the shape; reject the automated tail permanently**

The staged sequence (review → test → docs → lint) and the auto-fix-vs-escalate split are both sound, and CLIO half-has them already: `bruin validate`, the test suite, and the same-change documentation rule all exist but run ad hoc per relay prompt rather than as a named, always-run sequence. Adopt as a **pre-handback checklist** the live session runs before writing `reports.md`. The escalate-vs-autofix distinction maps cleanly onto a principle CLIO already holds — mechanical corrections proceed; anything touching intent or diagnosis escalates, consistent with "treat a bug report's proposed fix as a hypothesis."

**The tail is refused outright.** `no-mistakes` ends by forwarding the branch to the real remote and opening the PR itself; `+yolo` lets the first mate merge on its own judgment. Both are precisely the action reserved to Sam by hand. Useful vocabulary borrowed from firstmate's trust tiers: CLIO is not `local-only` and certainly not `+yolo` — it is a stricter tier the source tooling does not offer, **report-only**: verify, report, stop. Nothing about this is a cost/benefit question that better tooling could reopen.

### 6. Context-window auto-compact — **Adopt, with a mitigation**

Setting a compaction threshold once and stopping manual context management is free and applies to the live Codespace session. One CLIO-specific interaction is worth naming: compaction can silently discard the file-and-line evidence that this project's "name exactly why, with a file and line reference" standard depends on, and long investigative passes are exactly where compaction fires. Mitigation: the live session writes findings into `reports.md` **incrementally as it goes**, not only at the end — overwrite once at the start (per the standing rule), then append within the session. Compaction then cannot lose evidence already externalized.

### 7. Discord/X public-mention relay — **Reject**

No community, no public bug inbox, no contributors — the pattern has nothing to act on. The stronger reason, which would hold even if a community existed: every outgoing external message is governed by a standing practice requiring human drafting in first-person singular plus an AI-proofing pass. An agent answering public @-mentions on its own is structurally incompatible with that, independent of volume.

### 8. Persistent secondmates / multi-machine fleet — **Reject**

Solves portfolio-scale coordination (≈36 projects, an always-on second machine) against one repository and one active session. Beyond being unnecessary, it is counterproductive here: because the terminal step is a single human reviewing and committing by hand, added parallel capacity lengthens the review queue rather than shortening time-to-done, and it points the project at exactly the scope profile OTF screens against for solo researchers.

### 9. Quota-telemetry-driven model routing — **Reject; this is the single sharpest mismatch**

Agreed with the preliminary sort, and the reason is worth stating more precisely than "not worth the effort." In Kun's setup quota is renewable and expires unused, so routing to spare capacity is free upside and the optimal policy is opportunistic spending. Fable's allocation here is *depleting and countdown-timed*, and CLIO's existing policy deliberately reserves it for two named situations only: genuine novelty with no precedent, and post-milestone audit passes. **Automating routing on availability would silently convert a deliberate-scarcity policy into a spend-it-while-it's-there policy** — not an optimization of the existing rule but a reversal of it. The infrastructure cost is secondary; the incentive inversion is the disqualifier. A narrow carve-out that needs no tooling: Sam glancing at remaining Fable allocation before committing to a milestone audit pass is a sensible human check, and stays a human check. Model routing continues to be governed by the existing `CLAUDE.md` policy, which this ADR does not modify or restate.

### 10. lavish-style interactive HTML review boards — **Reject the format; acknowledge one narrow case already covered**

Well-matched to a visually-driven product with many disposable prototype variants to judge by eye. CLIO's outputs are written and analytical — findings, documents, SQL, classifier output — and are judged by correctness against evidence, not by preference among throwaway variants.

One narrow case does deserve acknowledgement rather than silent dismissal: dashboard chart/layout alternatives, or competing rendered report templates, are genuine side-by-side visual comparisons where a board beats sequential screenshots. But CLIO already renders artifacts to images and inspects them visually as part of Tier B, and the Cowork environment already has native widget/artifact rendering capable of a side-by-side comparison. So the *capability* exists; adopting `lavish-axi` would add a dependency to get something already available. Rejected as redundant rather than as useless — a materially different reason, and the one a future session should re-test.

## Trade-off Analysis

**What CLIO gives up.**

- *Attention-free automation.* The single largest productivity gain in the demo — `+yolo` and auto-PR meaning work completes while the human is elsewhere — is unavailable by construction. Every unit of work terminates in a queue waiting on one person. This is bought deliberately: the manual commit/push is CLIO's answer to reviewers inclined to discount AI-assisted work, and that answer is worth more to the project than saved keystrokes.
- *Quota-optimized throughput.* No cross-vendor spillover, no automatic fallback when one budget is low. In exchange, no telemetry to build or maintain, and — more importantly — no mechanism nudging an expiring scarce budget toward being spent because it is available.
- *Parallel fleet throughput.* Sequential work continues. In exchange, work-in-progress stays reviewable by one person and project scope stays inside what the funder considers plausible for a solo researcher.
- *Ready-made tooling.* Everything adopted here is written by hand as markdown policy rather than installed. The trade is real: hand-written policy can be forgotten in a way a git proxy cannot be. Patterns 2 and 4 are the mitigation — a template and a written tier policy are precisely the artifacts that stop invariants from depending on memory.

**What CLIO gains.**

- Two proven-but-unnamed rituals become stated policy with a classification rule, so a new artifact type gets the right rigor by derivation instead of by whoever happens to remember.
- A recurring, already-observed defect class (omitted relay-prompt boilerplate) gets a structural fix.
- A capability that genuinely did not exist: an on-demand, impact-ordered view of what is open and undecided.
- Zero new dependencies, zero CI surface, zero devcontainer bootstrap debt — notable given this project's existing unresolved friction around things that do not survive a fresh clone (`.env`, the untracked pre-commit hook, TD-36/TD-132).

## Consequences

**Easier.** Answering "what's open?" in one pass. Drafting a relay prompt without re-deriving its invariants. Knowing which verification ritual an artifact warrants before starting. Onboarding a future session into the Cowork/Codespace division of labour, since it will be written down.

**Harder / newly obligated.** Four more pieces of prose to keep honest. The bearings digest in particular must stay derived-on-demand; if it ever acquires a durable file, it becomes a staleness liability of exactly the kind already documented in `CLAUDE.md`. The pre-handback checklist adds a small fixed cost to every live session, justified only if the checks it names are ones actually worth running — if it accretes ceremony, prune it.

**Unchanged.** Model routing, the commit/push rule, external-communication tone and AI-proofing, and the same-change documentation discipline. This ADR references all of them and modifies none.

**To revisit, and on what trigger.** Several rejections above are contingent, not principled, and should be re-opened when their premise changes rather than treated as settled:

- *More than one repository, or any second contributor* → re-open 8 (fleet/secondmates) and 1's worktree-isolation question, since review contention and tree contamination both become real.
- *A second funded period with renewable rather than depleting model budget* → re-open 9 (quota routing); its rejection is an economics argument, not a design one.
- *Any public-facing community or issue tracker* → re-open 7, subject to the external-communication standing practice, which would still forbid unreviewed autonomous replies.
- *A dashboard redesign with genuine multi-variant layout comparison* → re-test 10, first against Cowork's existing widget rendering before considering any dependency.
- *Permanently not revisitable:* the auto-forward / auto-PR / auto-merge tail in 5. This is a values decision by the project owner, not a cost/benefit one, and a future session should not reinterpret it as an efficiency trade-off awaiting better tooling.

## Action Items

- [x] Sam reviews and approves, amends, or rejects this ADR. **Approved 2026-09-16.** The items below are now live practice going forward, not merely proposed — except where individually still marked open.
- [ ] Decide the one open question in pattern 1: is `git worktree` isolation for speculative/high-blast-radius live-session work acceptable under the standing rule, given it creates a branch ref but no commit and no push? Record the answer in `decision-log.md`'s narrative section either way.
- [x] **Cowork-side half of pattern 2, done 2026-09-16:** the "prior decisions checked" grounding mechanism for Agent-tool advisory dispatches is designed (Opus 5, verified against the actual ADR text before applying), written into this ADR's Option 2 addendum above, and added to `CLAUDE.md` as a standing practice. Applies starting now to every Cowork-side dispatch that asks an advisor to decide, design, or diagnose.
- [ ] Write the live-Codespace-facing half of the relay-prompt template (pattern 2) as a Cowork-side skill or checklist, covering at minimum: no commit / no push / no drafted commit message; overwrite `reports.md` at start and confirm its `.gitignore` entry; advisor consults name **Opus 4.8** for the live environment; restate inline anything that exists only in the planning workspace; update `decision-log.md`, `technical-debt-inventory.md`, and the relevant ADR in the same change. This is still unbuilt — the grounding mechanism above is a separate, already-complete piece of pattern 2, not a substitute for this one.
- [ ] Write the three-tier verification-rigor policy (pattern 4) into `docs/03-development/testing-strategy.md`, keyed to failure mode, with Tier A illustrated by TD-08's golden fixtures and Tier B by the whitepaper docx ritual. Add a one-line pointer from `CLAUDE.md`; do not inline the policy there.
- [ ] Draft the bearings/ahoy digest ritual (pattern 3): sources fixed to `decision-log.md`, `technical-debt-inventory.md`, `implementation-roadmap.md`; output impact-ordered, one decision at a time, using the existing backlog-tiering policy as the ordering key; explicitly derived-on-demand, never written to a durable file.
- [ ] Draft the pre-handback checklist (pattern 5) and fold it into the relay-prompt template rather than maintaining it separately: review → test (`bruin validate`, suite, re-materialization where relevant) → same-change doc updates → lint → write `reports.md` → stop.
- [ ] Set the auto-compact threshold in the live Codespace session (pattern 6), and add the incremental-`reports.md` instruction to the relay-prompt template as its mitigation.
- [x] Record this ADR in `decision-log.md` — both the ADR index row and a narrative entry capturing the funding-asymmetry reasoning. **Done as part of this same porting session — see Part 3 below.**
- [ ] If any action item above is deferred rather than done, open a corresponding entry in `technical-debt-inventory.md` with location, severity, and recommended action — so the deferral is tracked rather than implicit in an unchecked box in this file.
