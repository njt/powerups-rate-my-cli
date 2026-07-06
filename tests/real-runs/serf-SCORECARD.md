# CLI Agent-Nativeness Scorecard

**Target:** `/Users/gnat/Source/AI Experiments/serf` — main `serf` CLI (Go, stdlib `flag` + hand-rolled dispatch; **not** cobra). Module `primeradiant.com/serf`.
**Date:** 2026-07-06
**Score:** 20 / 31 applicable checks (64.5%)
**Failing gaps:** 4 Blocker · 5 Friction · 2 Target
**⚠ Suspicious-N/A warning:** Principle **P8 (Async-aware execution)** returned entirely N/A. This is *legitimate*: the main serf CLI wraps no async submitting API — the agent run is synchronous from the CLI's view, and serf's job-control system (`docs/job-control.md`) is a **model-facing agent-tool surface**, not a CLI command surface. No CLI command returns a job id / `status: queued`. Recorded here per template, but not a scoring artifact.

> Scope note: only the main `serf` command surface was assessed (`cmd/serf/main.go`, `cmd/serf/*.go`, `cmd/serf/internal/`). Helper binaries (`serf-hub`, `serf-tui`, `serf-doctor`, `llmcall`, `serf-fuzz-harvest`) and the frontend were excluded, except that `serf-namingcheck` / `serf-docscheck` were investigated for P6.4.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | Agent run is `NonInteractive: true` (`run.go:196`); `openai login` picks device-code vs browser flow via headless detection (`openai_login.go:162-189`), so headless has a non-stdin path; plugin gates *return an error*, not a prompt (`plugincmd.go:84,318`). |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | `os.ModeCharDevice` check chooses prompt-vs-pipe for the CLI prompt (`main.go:110-111`); `isHeadlessLogin`/`isHeadlessLoginFor` gate the login flow (`openai_login.go:162-189`). |
| 1.3 Confirmation-bypass flag exists for destructive ops | **fail** | F | C | Install/marketplace-add have `--yes` (`plugincmd.go:71,305`), but destructive `plugin remove`/`marketplace remove`/`gc`/`disable`/`openai logout` define **no** `--force`/`--yes` (`plugincmd.go:92-106,327-344,447-469`). Low blast radius (local, reversible) but the bypass-flag convention is not carried onto the removes. |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | — | C | No select/menu prompts anywhere (no `survey`/`promptui`); pass by absence. |
| 1.5 Bypass convention is consistent (one flag name) | pass | — | C | `--yes` is the sole bypass flag, used identically on `plugin install` and `marketplace add` (`plugincmd.go:71,305`); no competing `--force`/`--no-confirm`. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | `--json` on `plugin list`/`marketplace list`/`browse`/`gc`/`doctor`/`check-now` (`plugincmd.go:59,125,292,450,482,517`) and `launch-check --json` (`launchcheck.go:70,106-107`). |
| 2.2 Every data-returning command supports `--json` (coverage) | **fail** | F | C | Coverage is partial: `--list-sessions` prints human-only (`run.go:379-397`), `openai status` has no `--json`, and the **default agent-run result** has no `--json` (final answer → stdout as text; `--verbose` emits NDJSON only on *stderr*, `run.go:264-275`). |
| 2.3 One consistent flag name (`--json`) | pass | — | C | Only `--json` used; no `--format=json`/`-o json`. (`--output-schema` is unrelated — a JSON Schema for a model tool's output, `main.go:185`.) |
| 2.4 Exit codes: 0 success, non-zero failure | pass | — | C | `os.Exit(1)` on run/subcommand error, `os.Exit(2)` on flag-parse error, help exits 0 (`main.go:79,89,159,74-77`). |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | Result → `cfg.stdout` (`run.go:259`); events, notices, usage → stderr (`run.go:234-236`, `main.go:165`, `plugincmd.go:58`). |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | — | C | Pass by absence: no color/ANSI library or escape codes in the `cmd/serf` run path (grep for `NO_COLOR`/`IsTerminal`/`\x1b`/`color` hits only test files) — nothing to suppress. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent, not bare stack) | pass | — | C | Errors wrapped `fmt.Errorf("…: %w")` and printed as `"%s: %v"` with a subcommand prefix (`main.go:78`); no bare panics on the error path. |
| 3.2 Input validated early, before side effects | pass | — | C | Flag/enum/conflict validation runs at parse time before `run()` acts (`cmdutil.go:258`, `openai_login.go:101`). |
| 3.3 Enum/choice rejections enumerate the valid set | pass | — | C | e.g. `invalid reasoning effort %q (expected minimal|low|medium|high|xhigh|max|none)` (`cmdutil/cmdutil.go:258`); usage strings also list choices (`main.go:181,183,184`). |
| 3.4 Errors include corrective guidance | pass | — | C | Confirmation errors print `"Pass --yes to confirm."` (`plugincmd.go:83-84,317-318`); usage strings on flag errors; enum errors show expected values. |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent (idempotency token / natural key) | pass | — | Ft | Create-style ops are keyed by a natural identifier — `plugin install <plugin>@<marketplace>`, `marketplace add <name>`, `enable <plugin>@<marketplace>` (`plugincmd.go:310,90,359`). Exact re-create semantics live in `internal/plugins` (out of CLI scope). |
| 4.2 Destructive operations require an explicit, non-default flag | **fail** | B | C | `plugin remove`/`marketplace remove`/`gc`/`disable`/`openai logout` act immediately on positional args with **no** guard flag (`plugincmd.go:92-106,327-344,447-469`). Only `install`/`add` are gated (`--yes`). Mitigation: all are local/reversible operations. |
| 4.3 Consequential operations support `--dry-run` | **fail** | F | C | Consequential ops exist (`install`, `remove`, `upgrade`, `gc`, `marketplace add`, plus the file-mutating agent run) but **no `--dry-run` anywhere** (grep negative across `cmd/serf`). Per Detection methodology this is a fail, not N/A. |
| 4.4 Mutation responses return the affected identifier(s) | pass | — | C | Each mutation echoes the affected id: `Installed %s@%s version %s at %s`, `Removed %s@%s`, `Enabled %s@%s`, `Added marketplace at %s` (`plugincmd.go:324,343,362,90`). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default (limit/page size) | **fail** | B | C | `plugin list`, `marketplace list`, `marketplace browse`, `--list-sessions` dump the full set with no default limit/page (`run.go:379-397`, `plugincmd.go:252-282,200-224`). `browse` (remote catalog) is the real risk; the others are small local sets. |
| 5.2 List commands support filtering and pagination/cursor | **fail** | F | Ft | No `--filter`/`--limit`/cursor on any list handler (same sites as 5.1). |
| 5.3 Truncated output signals truncation and hints how to narrow | na | — | C | Lists never truncate (they dump all) — no truncation to signal. Precondition absent. |
| 5.4 MCP wrapper: each tool description fits a small token budget | na | — | C | serf is an MCP *client* (consumes `--mcp` servers, `run.go:190-191`); it exposes **no** MCP server/tool-description surface (`grep mcp.NewServer` negative). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | — | C | Verb set — `list`, `remove`, `add`, `install`, `enable`/`disable`, `status`, `upgrade`, `login`/`logout` — uses no banned verbs (`rm`/`ls`/`info`/`new`/`show`). Domain verbs (`gc`, `browse`, `doctor`, `check-now`) are internally consistent (`main.go:273-286`, `plugincmd.go:31-47`). |
| 6.2 Flags follow conventions | pass | — | C | `--json` (not `--format=json`), `--yes`, kebab-case throughout (`--max-rounds`, `--reasoning-effort`, `--no-project-prompts`); no `--skip-*`/`--no-confirm`. |
| 6.3 Naming is internally consistent across subcommands | pass | — | C | kebab-case CLI flags / snake_case JSON+TOML applied uniformly, documented in `docs/conventions/naming.md:14`. |
| 6.4 Documented naming policy + mechanical CI/lint enforces vocabulary | **fail** | T | Ft | A documented policy (`docs/conventions/naming.md`) **and** a linter (`serf-namingcheck`) **and** CI wiring (`.github/workflows/ci.yml:28-30`, `Makefile:282-283`) all exist — but they enforce **serialized-identifier casing** (JSON/TOML snake_case), *not* CLI verb/flag vocabulary. The one CLI-relevant rule (kebab-case flags) is explicitly **not** machine-enforced: "CLI flags are kebab-case; that's enforced where flags are registered" (`cmd/serf-namingcheck/main.go:4-5`). No verb-vocabulary or flag-name-vocabulary check exists. See verdict note below. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection (command/flag tree) | **fail** | B | Ft | No `agent-context`/`--schema`/`dump-schema` emitting the serf command/flag *tree* (grep negative). `launch-check --json` is a provider/model **launch contract** (`launchcheck.go:48-60`), and `AGENTS.md`/`docs/` are prose — none enumerate the real command tree. |
| 7.2 Machine introspection is versioned (`schema_version`) | na | — | C | 7.1 fails — no introspection to version. |
| 7.3 Long-form skill manifest teaches workflows | **fail** | T | Ft | No SKILL.md-style manifest teaching how to *drive the serf CLI*. `AGENTS.md` is an 855-byte testing note; `docs/skills/{tool-fluency,fuzzing-an-api-surface}` are skills injected **into serf's own runtime agent** via `--skills-dir`, not documentation of the CLI command surface. (A skills subsystem exists, but aimed at the in-CLI agent.) |
| 7.4 Introspection generated/validated against real implementation | na | — | Ft | 7.1 fails — nothing generated/validated. |

### P8. Async-aware execution — *entire principle N/A (CLI wraps no async submitting API)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | No CLI command returns a job id / `status: queued`; agent run is synchronous. serf's `job_*` tools are model-facing (`docs/job-control.md`), not a CLI surface. |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | No CLI poll loop (8.1 absent). |
| 8.3 Persistent job ledger across invocations | na | — | Ft | No CLI job ledger; `sess.DrainJobTree` (`run.go:246`) drains in-process subagent work only. |
| 8.4 A `jobs` command exposes `list`/`get`/`prune` | na | — | Ft | No CLI `jobs` command. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Recurring non-auth config can be persisted & reused | pass | — | Ft | Recurring non-auth config (`--model`, `--reasoning-effort`, `--plugin-dir`, `--max-rounds`, …) is persisted in `launch.toml` (`internal/launchconfig/`) and provider defaults in `providers.toml` (`llm/providercfg/`); commands do not force re-specifying it each run. |
| 9.2 Profile management subcommands exist (`save`/`use`/`list`/`show`/`delete`) | na | — | Ft | serf persists config via a single per-project/global TOML edited directly; there is no *named-profile* abstraction to manage, so profile-management verbs don't apply. |
| 9.3 `--profile` root flag + precedence flag>env>profile>default | na | — | C | No `--profile` flag (no named profiles). A precedence chain (flag > `launch.toml` > default; env for API keys) does exist, but not the named-profile mechanism this check targets. |
| 9.4 Profiles surfaced in machine introspection | na | — | C | No named profiles and 7.1 absent. |
| 9.5 Stable, documented storage location | pass | — | C | `$SERF_STATE_DIR` else `~/.serf` (`cmdutil/statedir.go:19-27`); `$XDG_CONFIG_HOME/serf` else `~/.config/serf` (`cmdutil/userdirs.go:13-23`); `launch.toml` locations documented (`docs/conventions/naming.md:51`). |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists (`feedback <text>` local JSONL) | **fail** | B | Ft | No `feedback` command anywhere (grep negative); the `.jsonl` files are internal transcript/API-log caches (`cmdutil/api_logging.go`), not a user feedback log. |
| 10.2 Feedback can POST upstream when configured | na | — | C | 10.1 fails. |
| 10.3 Artifact-producing commands support `--deliver` (stdout/file/webhook) | **fail** | F | Ft | serf produces artifacts (`--export-atif <path>`, `--cpu-profile <path>`, `--trace <path>`, `main.go`) via **bare file-path sinks** with no scheme abstraction (file/webhook/stdout). Per Detection methodology, bare `--output`-style sinks are a fail@F, not N/A. |
| 10.4 File sinks write atomically; unknown schemes get structured refusal | na | — | C | No `--deliver` scheme layer (10.3), so no scheme parsing/refusal to evaluate. |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | na | — | C | Depends on 7.1 (absent) and 10.1/10.3 (absent). |

## 6.4 verdict (called out per task)

**FAIL@T — `serf-namingcheck` does *not* satisfy 6.4.** serf has a genuinely impressive naming apparatus: a canonical policy doc (`docs/conventions/naming.md`), a custom AST linter (`cmd/serf-namingcheck`) plus two siblings (`serf-internalcheck`, `serf-docscheck`), all wired as first-class CI steps (`.github/workflows/ci.yml:28-35`) and Makefile targets (`Makefile:282-293`, rolled into `lint:`). But the enforced axis is the **wire-format casing of serialized identifiers** (JSON snake_case, TOML snake_case, with codex/appwire camelCase carve-outs) — not the **agent-facing CLI verb/flag vocabulary** that P6 governs. The policy *documents* kebab-case CLI flags, yet that rule is explicitly left to manual review ("enforced where flags are registered", `cmd/serf-namingcheck/main.go:4-5`), and nothing mechanically checks verb choices (`get` vs `info`, `list` vs `ls`) or flag-name conventions. So the mechanical check enforces the wrong surface for 6.4's intent.

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] **4.2 (B)** — Add a required guard flag (`--yes`) to `plugin remove`, `marketplace remove`, `gc`, `disable`, `openai logout`, mirroring the existing install/add gate. (`cmd/serf/plugincmd.go:92-106,327-344,447-469`; `openai_logout.go`)
- [ ] **5.1 (B)** — Apply a default limit/page size to list handlers, especially `marketplace browse` (remote catalog). (`cmd/serf/plugincmd.go:200-224,252-282`; `run.go:379-397`)
- [ ] **1.3 (F)** — Same fix as 4.2: give the destructive removes the `--yes` bypass convention so it's consistent CLI-wide.
- [ ] **2.2 (F)** — Add `--json` to `--list-sessions`, `openai status`, and the default agent-run final result (route structured result to stdout, not just NDJSON on stderr). (`run.go:379-397`, `run.go:259`)
- [ ] **4.3 (F)** — Add `--dry-run` to consequential ops (`install`/`remove`/`upgrade`/`gc`/`marketplace add`).

### Friction (conformance, lower priority)
- [ ] (covered above — 1.3, 2.2, 4.3 are the conformance Frictions; no others)

### Proposals — features, not auto-built (failing `feature` checks)
- **7.1 (B)** — Add an `agent-context`/`serf schema --json` command that emits the real command/flag *tree* as structured data (ideally generated from the dispatch table so it can't drift). Requires your go-ahead.
- **10.1 (B)** — Add a `serf feedback <text>` command that appends JSONL locally (optional upstream POST when configured → 10.2).
- **6.4 (T)** — Extend the naming-CI apparatus (already excellent) to also assert a CLI verb/flag *vocabulary* (approved-verb list + kebab-case flag lint), closing the one axis the current linter documents but doesn't enforce.
- **7.3 (T)** — Ship a SKILL.md-style manifest that teaches agents how to *drive the serf CLI* (distinct from the runtime skills under `docs/skills/`).
- **5.2 (F)** — Add `--filter` + cursor/pagination to list commands.
- **10.3 (F)** — Generalize the `--export-atif`/`--cpu-profile`/`--trace` file sinks into a `--deliver` scheme abstraction (stdout/file/webhook) with atomic writes + structured refusal for unknown schemes (→ 10.4).
