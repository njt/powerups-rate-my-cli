---
name: rate-my-cli
description: Use when asked to assess, rate, audit, or remediate a CLI codebase against agent-native CLI principles (Trevin Chow's 10 principles). Statically scores 45 pass/fail checks across 10 principles and can drive a conformance-fix loop. Read-only assessment; never runs the target CLI's mutating commands.
---

# rate-my-cli

Assess a CLI codebase against the 10 agent-native principles, and optionally remediate. **Two modes:** `assess` (default, read-only) and `remediate` (loop). The check rubric is in `rubric.md`; the report shape is `report-template.md`.

## Hard constraints
- Assessment is **static only** — never run the target CLI during assessment.
- The recon agent and all evaluators are **read-only**: dispatch them as the `Explore` agent type.
- Score = passes / (passes + fails), **excluding N/A**.

## Mode: assess

### Stage 1 — Recon (one read-only agent)
Dispatch one `Explore` agent to map the CLI once and return a recon map: entry point & arg-parsing framework; command/subcommand tree; where flags are declared; where output is serialized; where errors are built; config/profile storage; async/job code; MCP wrapper (if any); build/codegen/schema layer; whether the CLI is a thin upstream-API wrapper (auth-only state). If no CLI entry point is found, STOP and report that — do not produce a scorecard.

### Stage 2 — Fan-out (10 read-only agents, parallel)
Dispatch one `Explore` agent per principle (P1–P10) in a single message so they run concurrently. Give each: the recon map + that principle's section of `rubric.md`. Each returns a JSON array of findings, one per check id: `{check_id, verdict: pass|fail|na, severity, kind, evidence, fix_hint}`. Evaluators apply the Absence column mechanically and always include a one-line reason for pass-by-absence and N/A.

### Stage 3 — Synthesize
Collect all findings. Render `report-template.md` → write `SCORECARD.md` in the target repo root. Compute score excluding N/A. If any whole principle is entirely N/A, set the suspicious-N/A warning. Group the remediation plan by kind then severity exactly as the template lays out.

## Mode: remediate

A loop that closes conformance gaps and proposes feature gaps. Gate on **kind**, not severity.

1. Run `assess` to get the current scorecard.
2. **Auto-fix every failing `conformance` check**, Blockers first. These are localized source edits only — add `--json`, add `--force`/`--yes`, add an `isatty` guard, enumerate the valid set in an enum error, route data→stdout / diagnostics→stderr, rename off-convention verbs/flags. One fix per commit. **Never** auto-fix a `feature` check.
3. **Verify each fix by running read-only commands ONLY** — `--help`, `list`, `get`, anything with `--json` or `--dry-run`. Never run a mutating/destructive command. If a fix can't be verified read-only, re-read the code to confirm.
4. Re-assess to confirm the check cleared and catch regressions.
5. Repeat until no failing `conformance` checks remain.
6. **Stop. Present every failing `feature` check as a proposal** (profile system, async ledger + `--wait`, `agent-context`, skill manifest, `feedback`, `--deliver`, naming-policy CI check), ordered by severity. Do not build these without explicit go-ahead.
