# Design: `rate-my-cli` — agent-native CLI assessor & remediation loop

**Date:** 2026-06-25
**Author:** Nat (with Claude)
**Source material:** `trevin-essay.md` — *10 Principles for Agent-Native CLIs* (Trevin Chow, 2026-05-05)

---

## 1. Purpose

A Claude Code skill that assesses a CLI codebase against the 10 principles in
Trevin Chow's essay and, in its primary mode, drives a fix loop that closes the
gaps it finds. The essay already carries most of the structure we need: each
principle ships a `What good looks like` sentence-list (→ concrete checks) and a
Blocker / Friction / Target ladder (→ severity).

The unit of work is a **check**: a single pass/fail assertion derived from the
essay, carrying an intrinsic severity and an explicit rule for what "the thing
this check looks for doesn't exist" means.

## 2. Scope & non-goals

- **In scope:** static assessment of a CLI codebase; a remediation loop that
  applies small conformance fixes; a markdown scorecard + grouped remediation
  plan.
- **Assessment is strictly read-only.** It never runs the target CLI, to avoid a
  destructive command (`delete`, `prune`, …) touching real data.
- **Remediation edits source files only.** It never invokes mutating CLI
  commands. Verification runs only provably read-only commands (see §6).
- **Non-goals:** auto-building Target-level *features* (profile systems, async
  job ledgers, `agent-context`, `feedback`, `--deliver`). These are surfaced as
  proposals requiring the user's go-ahead.

## 3. Decisions (resolved during brainstorming)

| # | Decision | Choice |
|---|----------|--------|
| D1 | Assessment method | Static analysis (read source). No CLI execution during assessment — avoids destructive test runs. |
| D2 | Scoring model | Per-check pass/fail/N-A, each failed check carries a severity (Blocker/Friction/Target). Roll up per-principle and overall. |
| D3 | Deliverable | Markdown scorecard with `file:line` evidence + a prioritized remediation plan. Primary use is the remediate loop, not the human report. |
| D4 | Architecture | Recon-once → parallel fan-out (one read-only subagent per principle) → synthesize. |
| D5 | "No X found" semantics | Each check declares an **absence resolution**: PASS, N/A, or FAIL@severity (see §5). |
| D6 | Severity's role | Priority (fix order) **and** a loop stop-gate: auto-fix Blockers + cheap Friction; halt and propose Targets. |
| D7 | Remediation verification | Run **read-only commands only** (`--help`, `list`, `get`, `--json`, `--dry-run`) to confirm fixes; never destructive ones. |

## 4. Architecture & flow

```
skill: rate-my-cli
├── SKILL.md            # orchestration instructions (this design, operationalized)
├── rubric.md           # the 10 principles → ~45 checks (Appendix A)
└── report-template.md  # scorecard + remediation skeleton

Modes:
  assess     → recon → fan-out → scorecard + remediation plan (read-only)
  remediate  → loop: assess → auto-fix Blockers + cheap Friction → re-assess
               → repeat until zero Blockers & no cheap Friction
               → present Target gaps as proposals (never auto-built)
```

**Stage 1 — Recon (one pass).** Map the CLI once so the 10 evaluators don't each
re-discover it: entry point, command/subcommand tree, where flags are declared,
where output is serialized, where errors are constructed, config/profile storage,
async/job code, MCP wrapper (if any), and any build/codegen/schema layer. Emits a
`recon-map`. If no CLI entry point is found, the skill stops and says so rather
than producing a bogus scorecard.

**Stage 2 — Fan-out (parallel, read-only).** One subagent per principle, each
given the `recon-map` + its slice of `rubric.md`. Agents are read-only (use the
`Explore` agent type). Each returns structured findings.

Per-check finding shape:

```json
{
  "check_id": "1.1",
  "verdict": "pass | fail | na",
  "severity": "blocker | friction | target",   // meaningful only when fail
  "evidence": "src/cmd/delete.go:42  (or a one-line reason for pass-by-absence / na)",
  "fix_hint": "short remediation note"
}
```

**Stage 3 — Synthesize.** The orchestrator collects all findings, renders
`report-template.md` → `SCORECARD.md`. It computes the score as
`passed / (passed + failed)` **excluding N/A**, so a do-nothing CLI cannot score
100%. It flags any **suspicious-N/A cluster** (e.g. a whole principle returning
N/A) so absences don't silently vanish.

## 5. Absence resolution (the "no X" rule)

Conditional checks ("no X should Y") and presence checks ("there should be X")
need different handling when X is absent. Every check declares one of three:

- **PASS** — absence means the failure mode *cannot occur* and the principle's
  goal is met. E.g. check 1.1: zero interactive prompts ⇒ the CLI is
  non-interactive by construction.
- **N/A** — X is an optional capability the CLI may legitimately lack; absence is
  neither good nor bad *for this principle*. E.g. `--wait` when no async API
  exists; MCP description budget when there's no MCP wrapper; idempotency when
  there are no create operations. Excluded from the score denominator.
- **FAIL@severity** — the essay treats *absence of X as the gap itself* (its
  Blocker line reads "no X at all"): no structured output (P2), only `--help`
  with nothing machine-readable (P7), no way to persist config (P9), no feedback
  channel (P10).

Every PASS-by-absence and every N/A is reported **with its one-line reason**, so
a reviewer can sanity-check that an N/A isn't masking a real gap.

## 6. Remediation loop

1. Run `assess` → current scorecard.
2. **Auto-fix** Blockers + cheap Friction. These are small conformance edits, by
   construction (see the ladder in Appendix A): add `--json`, add `--force`/
   `--yes`, add an `isatty` guard, enumerate the valid set in an enum error,
   route data→stdout / diagnostics→stderr, rename off-convention verbs/flags
   (`ls`→`list`, `info`→`get`, `--skip-confirmations`→`--force`,
   `--format=json`→`--json`). One fix per commit (per Nat's standard workflow);
   a `/roborev-fix` pass fits after a batch.
3. **Verify** each fix by running **read-only commands only** from the allowlist
   (`--help`, `list`, `get`, anything with `--json` or `--dry-run`). Never run
   destructive commands.
4. **Re-assess** to confirm the check cleared and catch regressions.
5. Repeat until **zero Blockers and no cheap Friction remain**.
6. **Stop** and present Target-level gaps as proposals — profile system, async
   ledger + `--wait`, versioned `agent-context`, `feedback`, `--deliver`. These
   are features, not fixes; never auto-built.

"Cheap Friction" = a localized edit (rename, add a flag, reorder a stream,
extend an error string). Friction requiring new subsystems is treated as Target.

## 7. Report format (`SCORECARD.md`)

1. **Header** — target path, date, overall roll-up: count of failing Blockers /
   Friction / Target gaps, and the score (passes / applicable checks).
2. **Per-principle sections** — a table of checks: id, assertion, verdict,
   severity (if failed), evidence (`file:line`).
3. **Remediation plan** — grouped and ordered:
   - **Blockers** — fix now (small, safe).
   - **Friction** — fix if cheap; quick wins first.
   - **Target** — propose, don't auto-build (feature decisions).

## 8. Edge cases

- **Not a CLI / no entry point found** → stop after recon, report why.
- **Whole principle N/A** → surfaced as a suspicious-N/A cluster, not hidden.
- **Codegen/schema-driven CLI** (the essay's ideal) → recon notes the schema
  layer; checks can pass at the schema level even when individual subcommands
  aren't hand-written.
- **Monorepo with multiple CLIs** → out of scope for v1; assess one CLI root at a
  time (caller points the skill at the root).

## 9. Open / deferred

- This repo is not currently a git repository, so the design doc can't be
  committed yet (offer `git init`).
- Exact `rubric.md` wording per check is finalized during implementation;
  Appendix A is the authoritative source list and severities.

---

## Appendix A — The rubric (10 principles → checks)

Severity legend: **B** = Blocker, **F** = Friction, **T** = Target.
Absence column = resolution when the thing the check looks for is absent.

### Tier 1 — Table Stakes

**P1. Non-interactive by default**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 1.1 | No command can block on an interactive prompt without a bypass | B | PASS (no prompts ⇒ non-interactive) |
| 1.2 | TTY detection treats non-TTY stdin as headless (no prompt when not a TTY) | B | PASS |
| 1.3 | A confirmation-bypass flag exists for destructive ops (`--force`/`--yes`) | F | N/A (no destructive ops) |
| 1.4 | Interactive menus have a structured flag/file equivalent | F | PASS (no menus) |
| 1.5 | Bypass convention is consistent across subcommands (one flag name) | F | N/A (0–1 bypass flag) |

**P2. Structured, parseable output**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 2.1 | The CLI supports structured (JSON) output | B | FAIL@B |
| 2.2 | Every data-returning command supports `--json` (coverage) | F | N/A (none support it ⇒ 2.1 fails) |
| 2.3 | One consistent flag name (`--json`, not mixed `--format`/`--output`) | F | N/A |
| 2.4 | Exit codes: 0 success, non-zero failure, stable taxonomy | F | FAIL@B if always 0 on failure |
| 2.5 | Data → stdout, diagnostics/errors → stderr | F | — |
| 2.6 | ANSI/color suppressed when output isn't a terminal | F | — |

**P3. Errors that teach, and enumerate**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 3.1 | Failures produce a clear message (not silent, not a bare stack trace) | B | — |
| 3.2 | Input validated early, before side effects | F | — |
| 3.3 | Enum/choice rejections enumerate the valid set | F | N/A (no enum inputs) |
| 3.4 | Errors include corrective guidance (valid invocation / example) | F | — |

**P4. Safe retries & explicit mutation boundaries**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 4.1 | Create operations are idempotent (idempotency token or natural key) | B | N/A (no create ops) |
| 4.2 | Destructive operations require an explicit, non-default flag | B | N/A (no destructive ops) |
| 4.3 | Consequential operations support `--dry-run` | F | N/A |
| 4.4 | Mutation responses return the affected identifier(s) | F | N/A (no mutations) |

**P5. Bounded responses**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 5.1 | List-style commands have a bounded default (limit/page size) | B | N/A (no list commands) |
| 5.2 | List commands support filtering and pagination/cursor | F | N/A |
| 5.3 | Truncated output signals truncation and hints how to narrow | F | N/A |
| 5.4 | MCP wrapper: each tool description fits a small audited token budget | T | N/A (no MCP wrapper) |

### Tier 2 — Compounding

**P6. Cross-CLI vocabulary consistency**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 6.1 | Verbs follow universal conventions (`get` not `info`, `list` not `ls`) | B | — |
| 6.2 | Flags follow conventions (`--force` not `--skip-confirmations`, `--json` not `--format=json`) | B | — |
| 6.3 | Naming is internally consistent across subcommands | F | — |
| 6.4 | Documented naming policy + mechanical check (CI/lint) enforces vocabulary | T | FAIL@T |

**P7. Three-layer introspection**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 7.1 | Machine-readable introspection exists (`agent-context`-style command/flag schema) | B | FAIL@B |
| 7.2 | The machine introspection is versioned (`schema_version`) | F | N/A (7.1 fails) |
| 7.3 | A long-form skill manifest (`SKILL.md`-style) teaches workflows | T | FAIL@T |
| 7.4 | Introspection is generated/validated against the real implementation (in sync) | T | N/A (7.1 fails) |

(Note: `--help` for humans is assumed present; its absence falls out of 7.1's "only `--help`, nothing structured" Blocker framing.)

**P8. Async-aware execution** — *entire principle N/A if the CLI wraps no async API*

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 8.1 | Async-submitting commands offer `--wait` (block until done) | B | N/A (no async API) |
| 8.2 | The poll loop uses exponential backoff + jitter | F | N/A |
| 8.3 | A persistent job ledger records jobs across invocations | F | N/A |
| 8.4 | A `jobs` command exposes `list`/`get`/`prune` over the ledger | F | N/A |

**P9. Persistent identity through profiles**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 9.1 | A profile/config persistence mechanism exists | B | FAIL@B |
| 9.2 | Profile management subcommands exist (`save`/`use`/`list`/`show`/`delete`) | F | N/A (9.1 fails) |
| 9.3 | `--profile` is a persistent root flag; precedence flag > env > profile > default | F | N/A |
| 9.4 | Profiles surfaced in machine introspection (`agent-context`) | F | N/A (depends on 7.1) |
| 9.5 | Stable, documented storage location (`~/.<cli>/`) | F | N/A |

**P10. Two-way I/O**

| id | Assertion | Sev | Absence |
|----|-----------|-----|---------|
| 10.1 | A feedback channel exists (`feedback <text>` recorded locally) | B | FAIL@B |
| 10.2 | Feedback can POST upstream when configured, and that's discoverable | F | N/A (10.1 fails) |
| 10.3 | Artifact-producing commands support `--deliver` (stdout/file/webhook) | F | N/A (no artifacts produced) |
| 10.4 | File sinks write atomically; unknown schemes get a structured refusal | F | N/A (no `--deliver`) |
| 10.5 | `--deliver` + `feedback` surfaced in machine introspection | T | N/A (depends on 7.1) |

**Totals:** 10 principles, ~46 checks (≈ 4–5 per principle).
