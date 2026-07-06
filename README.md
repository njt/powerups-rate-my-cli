# powerups-rate-my-cli

> A [Powerup](https://github.com/njt/powerups-marketplace) — a Claude Code plugin.

A Claude Code skill that **statically assesses a CLI codebase** against the 10
agent-native-CLI principles from Trevin Chow's essay *10 Principles for
Agent-Native CLIs*, and can drive a **conformance-fix loop**.

It scores **45 pass/fail checks** across the 10 principles, maps each gap onto a
Blocker / Friction / Target severity, and tags each as `conformance` (a localized
edit) or `feature` (a whole subsystem). The output is a `SCORECARD.md` with
`file:line` evidence and a prioritized remediation plan.

## Safety model

- **Assessment is read-only and static.** The skill never runs the target CLI
  during assessment — it reads source, flag declarations, error strings, and any
  schema/codegen. This avoids a destructive command (`delete`, `prune`, …)
  touching real data.
- **Remediation edits source files only**, and verifies fixes by running **only
  provably read-only commands** (`--help`, `list`, `get`, `--json`, `--dry-run`).
  It never invokes mutating commands.
- **Features are never auto-built.** The remediate loop gates on *kind*: it
  auto-fixes `conformance` gaps and only *proposes* `feature` gaps (profile
  systems, async ledgers, `agent-context`, `feedback`, `--deliver`).

## Modes

| Mode | What it does |
|------|--------------|
| `assess` (default) | Recon the CLI once → fan out one read-only evaluator per principle → synthesize `SCORECARD.md` with score (excluding N/A), evidence, and a grouped remediation plan. |
| `remediate` | Loop: assess → auto-fix failing `conformance` checks (Blockers first, one commit each) → verify with read-only commands → re-assess → repeat until no conformance gaps remain → present `feature` gaps as proposals. |

A check whose target capability is absent resolves to **PASS** (the failure mode
can't occur), **N/A** (an optional capability legitimately missing — excluded
from the score), or **FAIL** (the essay treats absence itself as the gap). N/A
and pass-by-absence are always reported with a reason; a whole-principle N/A
raises a suspicious-N/A warning.

## Layout

```
skills/rate-my-cli/
  SKILL.md            # orchestration: modes, recon/fan-out/synthesize, the loop
  rubric.md           # the 45 checks: id, assertion, severity, kind, absence, detection
  report-template.md  # SCORECARD.md skeleton

docs/superpowers/
  specs/2026-06-25-rate-my-cli-design.md   # design spec (Appendix A = rubric master)
  plans/2026-06-25-rate-my-cli.md          # implementation plan

tests/
  VERIFY.md           # how to run the e2e validation
  fixtures/
    badcli/           # fails many Tier-1 conformance checks
    wrappercli/       # thin upstream-API wrapper → P8 & P9 score N/A
    goodcli/          # conformant baseline → feature gaps routed to proposals
    badcli-remediate/ # post-remediation copy (loop output)
  real-runs/          # scorecards from real-world CLIs (azdo, go365)
```

## Installing

Install as a Claude Code plugin from the Powerups marketplace:

```
/plugin marketplace add njt/powerups-marketplace
/plugin install powerups-rate-my-cli
```

Or add this repo directly as its own single-plugin marketplace:

```
/plugin marketplace add njt/powerups-rate-my-cli
/plugin install powerups-rate-my-cli
```

Then invoke it by asking Claude to "assess this CLI with rate-my-cli" (or
"remediate this CLI"). The `skills/`, and nothing else, is what Claude loads as a
capability; `tests/`, `docs/`, and the essay ride along as reference.

## Running the validation

See [`tests/VERIFY.md`](tests/VERIFY.md). Each fixture ships an `EXPECTED.md` of
per-check verdicts; the skill is run in `assess` mode against the fixture and its
`SCORECARD.md` is diffed against the expectations. The committed `SCORECARD.md`
files are golden references — `badcli` reproduced all expected failures,
`wrappercli` correctly scored P8/P9 as N/A (not Blocker), and `goodcli` passed
Tier 1 with its two feature gaps routed to proposals.

`tests/real-runs/` holds scorecards from running the assessor against real-world
Go/cobra CLIs (`azdo`, `go365`). Those runs also hardened the rubric's detection
methodology — see the preamble in `skills/rate-my-cli/rubric.md` and Appendix B
of the design spec.

The fixtures are tiny single-file Python CLIs; the read-only sanity checks need
only `python3` and `jq`.

## Source

The principles are from Trevin Chow's essay (`trevin-essay.md` in this repo). The
rubric's authoritative master is **Appendix A** of the design spec; if you change
a severity/kind/absence value there, update `rubric.md` too so they don't drift.
