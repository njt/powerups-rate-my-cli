# powerups-rate-my-cli

> A [Powerup](https://github.com/njt/powerups-marketplace) — a Claude Code plugin.

A Claude Code skill that **statically assesses a CLI codebase** for how well it
serves AI agents — **inspired by** Trevin Chow's essay *10 Principles for
Agent-Native CLIs*, and extended well beyond it from applying the rubric to real
projects. It turns the essay's prose into mechanically-scored checks, drives a
**conformance-fix loop**, and can optionally **validate the result live**
(because passing the rubric ≠ actually working). See [Provenance](#provenance)
for what comes from the article versus what we added.

It scores **47 pass/fail checks** across the 10 principles, maps each gap onto a
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
- **`validate` is opt-in and runs the CLI.** Static assessment is necessary but
  not sufficient — see Appendix C of the design spec, where remediating one CLI
  (`cu`) live surfaced six real bugs the rubric and unit tests all passed. Reads
  may run against any authed account; **mutations run only against an explicit
  throwaway sandbox**, never production.

## Modes

| Mode | What it does |
|------|--------------|
| `assess` (default) | Recon the CLI once → fan out one read-only evaluator per principle → synthesize `SCORECARD.md` with score (excluding N/A), evidence, and a grouped remediation plan. |
| `remediate` | Loop: assess → auto-fix failing `conformance` checks (Blockers first, one commit each) → verify with read-only commands → re-assess → repeat until no conformance gaps remain → present `feature` gaps as proposals. |
| `validate` (opt-in) | Runs the remediated CLI live to catch bugs static analysis can't — parse fragility, lossy pagination, secret-leaking `--json`. Reads run against any authed account; mutations run **only** against an explicit throwaway sandbox, with cleanup. Leaves a build-tagged e2e suite in the repo. |

A check whose target capability is absent resolves to **PASS** (the failure mode
can't occur), **N/A** (an optional capability legitimately missing — excluded
from the score), or **FAIL** (the essay treats absence itself as the gap). N/A
and pass-by-absence are always reported with a reason; a whole-principle N/A
raises a suspicious-N/A warning.

## Layout

```
skills/rate-my-cli/
  SKILL.md            # orchestration: modes, recon/fan-out/synthesize, the loop
  rubric.md           # the 47 checks: id, assertion, severity, kind, absence, detection
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

## Provenance

This project was **inspired by** Trevin Chow's essay *10 Principles for
Agent-Native CLIs* (`trevin-essay.md` in this repo) — it is not a literal
implementation of it. Credit for the direction is his; the operational machinery,
and the lessons from taking real CLIs from "passes the rubric" to "confirmed
working," are ours.

**From the essay:**
- the **10 principles** and their two tiers (Table Stakes / Compounding);
- the **Blocker / Friction / Target** severity framing;
- the prose "what good looks like" targets that seed each check.

**Our additions** (developed by applying the rubric to real CLIs — azdo, go365,
msgvault, agentsview, kata, serf, and a full remediation of `cu`):
- turning that prose into **discrete, mechanically-scored checks** (47 of them);
- the **`kind`** axis (conformance vs feature) and the **absence-resolution**
  model (PASS / N-A / FAIL);
- the **detection methodology** hardened from real runs (declared≠honored,
  idiomatic verbs, and *static ≠ runtime correctness*);
- checks **2.7** (no secret leak) and **7.5** (version reporting), added from
  real-world use and marked *(from real-world use)* in the rubric;
- the **assess / remediate / validate** workflow — including the live-validation
  phase the essay doesn't cover, which is where the hardest bugs actually surface.

The rubric's authoritative master is **Appendix A** of the design spec (essay-
derived); **Appendices B and C** record what real use added. If you change a
severity/kind/absence value in Appendix A, update `rubric.md` too so they don't
drift.
