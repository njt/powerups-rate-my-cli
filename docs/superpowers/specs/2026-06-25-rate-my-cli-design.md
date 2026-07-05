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
| D8 | What gets auto-fixed | Gate on **kind** (conformance vs feature), not severity. Conformance = localized edit → auto-fix; feature = new subsystem → propose-only. Severity orders *within* each. |
| D9 | Profiles (P9) scope | P9 covers persisting a **recurring non-auth config bundle**, not auth. Auth/credentials handled upstream or via env are out of scope; a CLI whose only persistent state is auth scores N/A on P9. |

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
  "kind": "conformance | feature",             // gates auto-fix vs propose
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
2. **Auto-fix** all failing **`conformance`** checks (severity orders them —
   Blockers first). These are localized edits by construction: add `--json`, add
   `--force`/`--yes`, add an `isatty` guard, enumerate the valid set in an enum
   error, route data→stdout / diagnostics→stderr, rename off-convention
   verbs/flags (`ls`→`list`, `info`→`get`, `--skip-confirmations`→`--force`,
   `--format=json`→`--json`). One fix per commit (per Nat's standard workflow);
   a `/roborev-fix` pass fits after a batch. Failing `feature` checks are **never
   auto-fixed**, regardless of severity.
3. **Verify** each fix by running **read-only commands only** from the allowlist
   (`--help`, `list`, `get`, anything with `--json` or `--dry-run`). Never run
   destructive commands.
4. **Re-assess** to confirm the check cleared and catch regressions.
5. Repeat until **no failing `conformance` checks remain** (Blockers cleared
   first, then the rest).
6. **Stop** and present all failing **`feature`** checks as proposals — profile
   system, async ledger + `--wait`, `agent-context`, skill manifest, `feedback`,
   `--deliver`, naming-policy CI check. These are subsystems, not fixes; never
   auto-built. Order proposals by severity.

**Kind vs severity are different axes.** Severity (Blocker/Friction/Target) is
how bad the gap is, taken from the essay's per-principle ladder. Kind is how big
the fix is: `conformance` = a localized edit (rename, add a flag, reorder a
stream, extend an error string); `feature` = a new subsystem. Most Tier-1 gaps
are conformance; most Tier-2 "Blocker"-rung gaps are features — which is exactly
why we gate the loop on kind, not severity.

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
Kind legend: **C** = conformance (localized edit → auto-fixable), **Ft** = feature (new subsystem → propose-only).
Absence column = resolution when the thing the check looks for is absent.

### Tier 1 — Table Stakes

**P1. Non-interactive by default**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 1.1 | No command can block on an interactive prompt without a bypass | B | C | PASS (no prompts ⇒ non-interactive) |
| 1.2 | TTY detection treats non-TTY stdin as headless (no prompt when not a TTY) | B | C | PASS |
| 1.3 | A confirmation-bypass flag exists for destructive ops (`--force`/`--yes`) | F | C | N/A (no destructive ops) |
| 1.4 | Interactive menus have a structured flag/file equivalent | F | C | PASS (no menus) |
| 1.5 | Bypass convention is consistent across subcommands (one flag name) | F | C | N/A (0–1 bypass flag) |

**P2. Structured, parseable output**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 2.1 | The CLI supports structured (JSON) output | B | C | FAIL@B |
| 2.2 | Every data-returning command supports `--json` (coverage) | F | C | N/A (none support it ⇒ 2.1 fails) |
| 2.3 | One consistent flag name (`--json`, not mixed `--format`/`--output`) | F | C | N/A |
| 2.4 | Exit codes: 0 success, non-zero failure, stable taxonomy | F | C | FAIL@B if always 0 on failure |
| 2.5 | Data → stdout, diagnostics/errors → stderr | F | C | — |
| 2.6 | ANSI/color suppressed when output isn't a terminal | F | C | — |

**P3. Errors that teach, and enumerate**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 3.1 | Failures produce a clear message (not silent, not a bare stack trace) | B | C | — |
| 3.2 | Input validated early, before side effects | F | C | — |
| 3.3 | Enum/choice rejections enumerate the valid set | F | C | N/A (no enum inputs) |
| 3.4 | Errors include corrective guidance (valid invocation / example) | F | C | — |

**P4. Safe retries & explicit mutation boundaries**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 4.1 | Create operations are idempotent (idempotency token or natural key) | B | Ft | N/A (no create ops; often upstream's responsibility) |
| 4.2 | Destructive operations require an explicit, non-default flag | B | C | N/A (no destructive ops) |
| 4.3 | Consequential operations support `--dry-run` | F | C | N/A |
| 4.4 | Mutation responses return the affected identifier(s) | F | C | N/A (no mutations) |

**P5. Bounded responses**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 5.1 | List-style commands have a bounded default (limit/page size) | B | C | N/A (no list commands) |
| 5.2 | List commands support filtering and pagination/cursor | F | Ft | N/A |
| 5.3 | Truncated output signals truncation and hints how to narrow | F | C | N/A |
| 5.4 | MCP wrapper: each tool description fits a small audited token budget | T | C | N/A (no MCP wrapper) |

### Tier 2 — Compounding

**P6. Cross-CLI vocabulary consistency**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 6.1 | Verbs follow universal conventions (`get` not `info`, `list` not `ls`) | B | C | — |
| 6.2 | Flags follow conventions (`--force` not `--skip-confirmations`, `--json` not `--format=json`) | B | C | — |
| 6.3 | Naming is internally consistent across subcommands | F | C | — |
| 6.4 | Documented naming policy + mechanical check (CI/lint) enforces vocabulary | T | Ft | FAIL@T |

**P7. Three-layer introspection**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 7.1 | Machine-readable introspection exists (`agent-context`-style command/flag schema) | B | Ft | FAIL@B |
| 7.2 | The machine introspection is versioned (`schema_version`) | F | C | N/A (7.1 fails) |
| 7.3 | A long-form skill manifest (`SKILL.md`-style) teaches workflows | T | Ft | FAIL@T |
| 7.4 | Introspection is generated/validated against the real implementation (in sync) | T | Ft | N/A (7.1 fails) |

(Note: `--help` for humans is assumed present; its absence falls out of 7.1's "only `--help`, nothing structured" Blocker framing.)

**P8. Async-aware execution** — *entire principle N/A if the CLI wraps no async API*

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 8.1 | Async-submitting commands offer `--wait` (block until done) | B | Ft | N/A (no async API) |
| 8.2 | The poll loop uses exponential backoff + jitter | F | C | N/A (no poll loop / 8.1 absent) |
| 8.3 | A persistent job ledger records jobs across invocations | F | Ft | N/A |
| 8.4 | A `jobs` command exposes `list`/`get`/`prune` over the ledger | F | Ft | N/A |

**P9. Persistent identity through profiles** — *covers a recurring **non-auth** config bundle, not auth. Auth/credentials handled upstream or via env are out of scope.*

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 9.1 | If commands force re-specifying a recurring non-auth config bundle, the CLI can persist & reuse it (profiles / named config) | B | Ft | N/A (auth-only state, or no recurring non-auth config) |
| 9.2 | Profile management subcommands exist (`save`/`use`/`list`/`show`/`delete`) | F | Ft | N/A (no profiles / 9.1 N/A) |
| 9.3 | `--profile` is a persistent root flag; precedence flag > env > profile > default | F | C | N/A (no profiles) |
| 9.4 | Profiles surfaced in machine introspection (`agent-context`) | F | C | N/A (no profiles / 7.1 absent) |
| 9.5 | Stable, documented storage location (`~/.<cli>/`) | F | C | N/A (no profiles) |

**P10. Two-way I/O**

| id | Assertion | Sev | Kind | Absence |
|----|-----------|-----|------|---------|
| 10.1 | A feedback channel exists (`feedback <text>` recorded locally) | B | Ft | FAIL@B |
| 10.2 | Feedback can POST upstream when configured, and that's discoverable | F | C | N/A (10.1 fails) |
| 10.3 | Artifact-producing commands support `--deliver` (stdout/file/webhook) | F | Ft | N/A (no artifacts produced) |
| 10.4 | File sinks write atomically; unknown schemes get a structured refusal | F | C | N/A (no `--deliver`) |
| 10.5 | `--deliver` + `feedback` surfaced in machine introspection | T | C | N/A (depends on 7.1) |

**Totals:** 10 principles, 45 checks (P1–P5 = 23, P6–P10 = 22; ≈ 4–5 per principle).

---

## Appendix B — Post-release hardening (2026-07-05)

First real-world runs against two Go/cobra CLIs (`azdo`, `go365`) surfaced
detection weaknesses that the synthetic fixtures could not. Core Sev/Kind/Absence
values in Appendix A are unchanged; the following operational guidance was added
to `rubric.md` (which now carries the authoritative **Detection methodology**
preamble):

- **Declared ≠ honored.** A framework-global/persistent flag (cobra
  `PersistentFlags`) can be declared yet ignored by a specific handler. Flag
  checks (1.1, 1.2, 2.2, 4.3, 5.1) must verify each handler *reads* the flag, not
  just that it exists — this caught real bugs (`pr comment` ignoring
  `--no-prompt`; `search` ignoring `--top`).
- **Absence vs informative-fail.** N/A applies only when a check's own
  precondition is absent; if the subject exists but the capability is missing,
  that's a fail (clarified on 4.3).
- **Idiomatic verb sets (6.1).** Downgrade a non-canonical verb from Blocker to
  Friction when the set is internally consistent and matches a documented target
  convention (`gh`-style `view`; filesystem `ls/cat/cp/mv/rm` on a drive
  subcommand). Generic, inconsistent `info`/`ls` stay Blocker.
- **7.1 prose-guide ≠ schema.** A hand-written agent guide, even emitted as JSON,
  does not satisfy machine introspection unless it enumerates the real
  command/flag tree.
- **10.3 bare `--output`.** A plain file-path sink with no scheme abstraction is
  partial credit (fail@F) when artifacts are produced — N/A only when no command
  emits a downloadable artifact.

Validation scorecards for both CLIs are committed under `tests/real-runs/`.
