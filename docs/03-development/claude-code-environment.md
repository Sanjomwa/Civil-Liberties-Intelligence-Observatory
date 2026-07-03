# Claude Code + GitHub Codespaces — Environment Setup and Migration

Status: engineering environment recommendation, CLIO Engineering Reset. Companion to `coding-standards.md` and `implementation-roadmap.md`. Written because the canonical CLIO repository lives in GitHub Codespaces and Claude Code is becoming the primary engineering assistant for implementation work, with Cowork reserved for design and documentation.

## 1–5. Direct answers

**Can Claude Code run directly inside GitHub Codespaces?** Yes. Codespaces is an officially supported host for the Dev Containers spec, and Anthropic ships a dedicated Dev Container Feature for exactly this case. Claude Code, the terminal, and all build tools run inside the container itself; the editor (VS Code or the Codespaces browser UI) just connects to it.

**Current recommended installation method?** Inside a devcontainer, add Anthropic's official feature to `devcontainer.json` rather than installing manually — see Section 2 below. On a bare local machine (not relevant here since the Codespace is canonical), the current recommended method is the native install script (`curl -fsSL https://claude.ai/install.sh | bash`), not `npm install` — npm installation is no longer the primary path.

**How should authentication work inside Codespaces?** Run `claude` in the container terminal and complete the browser-based OAuth login with your Claude Pro account — no API key needed. One important gotcha: if an `ANTHROPIC_API_KEY` environment variable is set anywhere in the container (including accidentally via `containerEnv`), Claude Code silently uses metered API billing instead of your Pro subscription. Check with `/status` after logging in. Two persistence details specific to Codespaces:
- `~/.claude` (credentials, settings, session history) survives stopping and starting a Codespace automatically, but is wiped on a full container rebuild — mount a named volume there to survive rebuilds (Section 7).
- To carry authentication across entirely different Codespaces (not just rebuilds of one), generate a long-lived token with `claude setup-token` and store it as a GitHub Codespaces repository secret (`CLAUDE_CODE_OAUTH_TOKEN`); Codespaces injects repository secrets as environment variables automatically.

**Should the Codespace be canonical, local machine as terminal only?** Yes — this is exactly what the dev container model is designed for, and it matches your stated priority (engineering velocity over local convenience). Every actual computation — Claude Code, language servers, the Bruin pipeline, BigQuery access — runs in the container where the datasets and dependencies already exist. The local machine becomes a thin client: a browser tab, or VS Code's Codespaces extension connecting remotely. Nothing meaningful needs to run locally, so there is no environment to keep in sync.

**Limitations or quotas specific to Codespaces?** None on the Claude side — usage is tracked per Anthropic account, not per machine, so a Codespace draws from the same Pro-plan pool as running Claude Code locally or using Cowork. Two things to actually watch: GitHub's own Codespaces compute/storage quota is separate from Anthropic's and depends on your GitHub plan, not your Claude plan. On the Claude side, Pro-plan usage for Claude and Claude Code is one shared pool with a rolling 5-hour window plus a weekly cap; Anthropic does not publish exact hour or token figures for Pro, only relative multipliers against Max tiers, so budget the one month conservatively rather than against a specific number. If usage credits or pay-as-you-go API billing get offered when you hit the limit, decline them unless you deliberately want metered spend — accepting switches you off the Pro allocation for that session.

## 6. Recommended workflow for a solo engineer on this project

- Keep `CLAUDE.md` (already drafted in this working folder) at the actual repository root inside the Codespace — Claude Code reads it automatically every session, so it should carry exactly the load-bearing facts already written there (the ACLED-path open question, the synthetic Lumen data, the CROSS JOIN bug, the confidence-scheme duplication) rather than making Claude Code rediscover them each session.
- Use plan mode before any nontrivial change, especially anything touching `int.acled_event_classification.sql`, `features/acled_pressure_signals.sql`, or `intelligence/acled_pressure_regimes.sql` — this is exactly the code the Technical Debt Inventory flags as highest-risk and least-tested.
- Work in small, git-committed increments. Claude Code makes git operations conversational (`what files have I changed?`, `commit my changes with a descriptive message`) — use that to keep history reviewable rather than batching large changes.
- Use `/clear` deliberately between unrelated tasks so unrelated debugging history doesn't leak into the next task's context.
- Start with Step 0 of `implementation-roadmap.md` — verifying whether `intelligence.acled_pressure_regimes` is actually consumed by any reporting mart — as the first real task in the new environment. It is well-specified, bounded, and its answer determines how several later steps are sequenced, which makes it a good test of the setup itself as well as a genuinely necessary task.
- Build the golden-file regression tests from `testing-strategy.md` Priority 1 early, so that any change Claude Code makes to classification logic is checked automatically rather than only reviewed by eye.

## 7. Recommended devcontainer.json additions

The current `.devcontainer/devcontainer.json` in the repository pins `mcr.microsoft.com/devcontainers/python:1-3.11-bookworm`, which is Technical Debt Inventory item TD-07 — it contradicts `pyproject.toml`'s `>=3.12.3` requirement. Since this file needs editing to add Claude Code anyway, fix that in the same change:

```json
{
  "name": "Python 3",
  "image": "mcr.microsoft.com/devcontainers/python:1-3.12-bookworm",
  "features": {
    "ghcr.io/anthropics/devcontainer-features/claude-code:1.0": {}
  },
  "customizations": {
    "codespaces": {
      "openFiles": [
        "README.md",
        "streamlit/app.py"
      ]
    },
    "vscode": {
      "settings": {},
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance"
      ]
    }
  },
  "mounts": [
    "source=claude-code-config-${devcontainerId},target=/home/vscode/.claude,type=volume"
  ],
  "updateContentCommand": "[ -f packages.txt ] && sudo apt update && sudo apt upgrade -y && sudo xargs apt install -y <packages.txt; [ -f requirements.txt ] && pip3 install --user -r requirements.txt; pip3 install --user streamlit; echo '✅ Packages installed and Requirements met'",
  "postAttachCommand": {
    "server": "streamlit run streamlit/app.py --server.enableCORS false --server.enableXsrfProtection false"
  },
  "portsAttributes": {
    "8501": {
      "label": "Application",
      "onAutoForward": "openPreview"
    }
  },
  "forwardPorts": [
    8501
  ]
}
```

Notes on this patch:
- `target=/home/vscode/.claude` assumes the Microsoft Python devcontainer image's default `remoteUser` is `vscode`; confirm this against the actual image (check `whoami` in the container) before relying on it.
- Do not add `ANTHROPIC_API_KEY` to `containerEnv` — that would force metered billing instead of Pro-plan usage.
- The `duckdb` version drift (TD-06, `Bruin/requirements.txt` pins `0.10.0` against `pyproject.toml`/`uv.lock`'s `1.5.0`) is a separate fix inside `Bruin/requirements.txt` itself, not a devcontainer setting — worth doing in the same sitting since both are one-line, mechanical fixes from the Technical Debt Inventory.
- Not included, and not recommended for a solo, trusted-repository setup: the reference container's network-egress firewall and `--dangerously-skip-permissions`. Both are documented options for team/security-sensitive setups, not a default a solo engineer needs.

## 8. Division of labor between Claude Code and Cowork going forward

Recommended: yes, reserve Cowork for design discussion and documentation, and move implementation into Claude Code inside the Codespace. Two concrete reasons, not just a general preference: Pro-plan usage limits are one shared pool across Claude (the product Cowork runs on) and Claude Code, so running heavy implementation work in both concurrently draws down the same monthly allowance faster than routing it through one tool. And practically, everything produced during the Engineering Reset (`CLAUDE.md`, the `docs/` tree, the ADRs, the roadmap) is exactly the standing context Claude Code will read automatically once pointed at the repository — Cowork's role narrows naturally to producing and updating those planning documents, reviewing proposals at a higher level, and any deliverable that benefits from Cowork's document-generation tooling, while Claude Code becomes where the actual SQL and Python changes, tests, and commits happen.

## Migration checklist

1. Open the CLIO Codespace and edit `.devcontainer/devcontainer.json`: add the Claude Code feature block, bump the Python base image to 3.12, and add the `~/.claude` volume mount (Section 7).
2. While there, fix `Bruin/requirements.txt`'s `duckdb` pin to match `pyproject.toml`/`uv.lock` (TD-06) — a one-line fix, same sitting.
3. Rebuild the container (Codespaces: Command Palette → "Codespaces: Rebuild Container", or the equivalent rebuild action from the Codespaces web UI).
4. Open a terminal in the rebuilt container and run `claude`; complete the browser OAuth login with the Pro account.
5. Run `/status` to confirm subscription billing is active and no stray `ANTHROPIC_API_KEY` is forcing API billing instead.
6. Run `claude setup-token` to generate a long-lived token; store it as a GitHub Codespaces repository secret (`CLAUDE_CODE_OAUTH_TOKEN`) so future or rebuilt Codespaces don't require a fresh manual login.
7. Copy `CLAUDE.md` from this planning folder into the actual repository root inside the Codespace — this is the step that makes everything else in this reset (the debt inventory, the roadmap, the ADRs) something Claude Code actually reads on every session, rather than a file that stays outside the loop.
8. Bring the `docs/02-architecture/` and `docs/03-development/` content from this planning folder into the repository (or reference it from `CLAUDE.md`) so Claude Code's working context includes the findings from this reset.
9. Point Claude Code at Step 0 of `implementation-roadmap.md` as its first task inside the new environment.
10. From here forward: route implementation work through Claude Code in the Codespace; bring Claude Code's proposals back to Cowork only for higher-level review, design discussion, or updates to the planning documents themselves.

This document does not include steps 1–4 executed on your behalf — Cowork does not have access to your GitHub Codespace, so these need to be carried out there directly. Everything above is written to be followed as-is inside that environment.
