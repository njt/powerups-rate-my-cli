---
name: rate-my-cli
description: Use when asked to assess, rate, audit, or remediate a CLI codebase against agent-native CLI principles (inspired by Trevin Chow's 10 principles, extended from real-world use). Statically scores 48 pass/fail checks across 10 principles, drives a conformance-fix loop, and can optionally confirm the result live. Assessment/remediation are static and read-only by default; the live `validate` phase is opt-in (read-only against any account; mutations only against an explicit throwaway sandbox).
---

# rate-my-cli

Assess a CLI codebase against the 10 agent-native principles, remediate, and optionally confirm the result live. **Three modes:** `assess` (default, static/read-only), `remediate` (conformance-fix loop), and `validate` (opt-in live e2e). The check rubric is in `rubric.md`; the report shape is `report-template.md`.

## Hard constraints
- `assess` is **static only** — never run the target CLI during assessment. `remediate` edits source and verifies with **read-only commands only**.
- The recon agent and all evaluators are **read-only**: dispatch them as the `Explore` agent type.
- Score = passes / (passes + fails), **excluding N/A**.
- **Static assessment is necessary but not sufficient.** It finds missing capabilities well but cannot prove the CLI *works* — response-parse fragility, lossy pagination, and secret-leaking `--json` only surface at runtime (see the rubric's Detection methodology). When the goal is "confirmed working," run `validate`.

## Mode: assess

### Stage 1 — Recon (one read-only agent)
Dispatch one `Explore` agent to map the CLI once and return a recon map: entry point & arg-parsing framework; command/subcommand tree; where flags are declared; where output is serialized; where errors are built; config/profile storage; async/job code; MCP wrapper (if any); build/codegen/schema layer; whether the CLI is a thin upstream-API wrapper (auth-only state). If no CLI entry point is found, STOP and report that — do not produce a scorecard.

### Stage 2 — Fan-out (10 read-only agents, parallel)
Dispatch one `Explore` agent per principle (P1–P10) in a single message so they run concurrently. Give each: the recon map + that principle's section of `rubric.md`. Each returns a JSON array of findings, one per check id: `{check_id, verdict: pass|fail|na, severity, kind, evidence, fix_hint}`. Evaluators apply the Absence column mechanically and always include a one-line reason for pass-by-absence and N/A.

### Stage 3 — Synthesize
Collect all findings. Render `report-template.md` → write `SCORECARD.md` in the target repo root. Compute score excluding N/A. If any whole principle is entirely N/A, set the suspicious-N/A warning. Group the remediation plan by kind then severity exactly as the template lays out.

## Mode: remediate

A loop that closes conformance gaps and proposes feature gaps. Gate on **kind**, not severity.

**Before you branch — the target is a *moving* repo (learned from go365):**
- **`git fetch` and branch from the true `origin/HEAD`**, not a possibly-stale local branch. Branching from a stale base caused a 9-commit divergence, a 5-way merge conflict, and a mis-pointed tag on go365 — all avoidable.
- **Expect concurrent development.** When you merge back, reconcile with work that landed meanwhile by *combining* — a command that gained `--attach` upstream and `--dry-run` from you keeps both; never clobber.
- **Consistency is cross-CLI, not just per-CLI** (Principle 6's actual point: agents build one generalized model across every CLI they've seen). If the target is one of a suite, converge on the sibling tools you've already remediated — same `agent-context` shape, same canonical verbs, same flag names. Don't invent a local dialect.

1. Run `assess` to get the current scorecard.
2. **Auto-fix every failing `conformance` check**, Blockers first. These are localized source edits only — add `--json`, add `--force`/`--yes`, add an `isatty` guard, enumerate the valid set in an enum error, route data→stdout / diagnostics→stderr, rename off-convention verbs/flags. One fix per commit. **Never** auto-fix a `feature` check.
3. **Verify each fix by running read-only commands ONLY** — `--help`, `list`, `get`, anything with `--json` or `--dry-run`. Never run a mutating/destructive command. If a fix can't be verified read-only, re-read the code to confirm.
4. Re-assess to confirm the check cleared and catch regressions.
5. Repeat until no failing `conformance` checks remain.
6. **Stop. Present every failing `feature` check as a proposal** (profile system, async ledger + `--wait`, `agent-context`, skill manifest, `feedback`, `--deliver`, naming-policy CI check), ordered by severity. Do not build these without explicit go-ahead.

## Mode: validate (opt-in — runs the CLI live)

The static rubric found the *gaps*; only running the CLI finds the *bugs*. On cu, live-fire testing surfaced six real bugs that assess/remediate and unit tests all passed: a `--json` credential leak, a `truncated`/`next_cursor` lie, ~95% pagination data-loss at small `-n`, a `docs pages list` crash, a `comment add` parse crash, and a missing `delete --json`. This mode confirms the remediated CLI actually works. **It runs the target CLI, so it is opt-in and requires an explicit safe target.**

### Safety gate (never skip)
- **Reads** may run against any account the CLI is already authed for.
- **Mutations** (`create`/`update`/`delete`) run **only** against an explicit **throwaway sandbox** the user names (a dedicated workspace/list/project). Never against production. If no sandbox is given, run reads only and skip mutations.
- **Auth freshness:** if the CLI uses an expiring session credential, refresh it (add a `… auth refresh`-style command if missing) or skip the credential-gated paths.

### Build a build-tagged live suite (so offline `test`/CI stay green)
Scaffold e2e tests behind a build tag / opt-in flag, discovering fixtures at runtime (no hardcoded ids). Assert **invariants**, not content:
- **Smoke:** every read command → exit 0, valid JSON, no panic.
- **Envelope:** `count == len(items)`, `count ≤ -n`, and **`truncated ⟺ next_cursor present`**.
- **Pagination is lossless:** the `--cursor` page equals `items[k:2k]` of a single `-n 2k` read (no skips/dupes).
- **No secret leak:** `--json` of status/config carries no full-length credential.
- **Safety refusals (no mutation):** bad `--deliver` scheme refused; `delete` without `--force` refused (and the target still exists); `--dry-run` prints without writing.
- **Sandbox mutation lifecycle** (only with an explicit sandbox target): create → get → update → comment → dry-run → delete, with **guaranteed cleanup** (register the force-delete the instant the task is created) and a post-run **residue check**.

Any failure here is a real bug — fix it and re-run, don't loosen the assertion. Leave the suite in the repo as a repeatable gate.
