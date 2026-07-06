# CLI Agent-Nativeness Scorecard

**Target:** ~/Source/cu  (`cmd/cu/` — Go / cobra CLI wrapping the ClickUp API; SDK in `libcu/`)
**Date:** 2026-07-06
**Score:** 14 / 28 applicable checks (50%)
**Failing gaps:** 5 Blocker · 7 Friction · 2 Target
**⚠ Suspicious N/A:** two whole principles returned N/A — **P8 (async)** and **P9 (profiles)**. Both are legitimate: the CLI wraps only synchronous ClickUp REST endpoints (no job submission / polling), and its persisted state is auth-centric (token/JWT/refresh) plus an already-persisted `team_id`/`inbox_region`, with no forced recurring non-auth flag cluster. Recorded here so a reviewer can confirm.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on a prompt without a bypass | pass | | C | `login.go:47-49` (email) and `:52-58` (password) prompt, but both are bypassable: `--email`/`CLICKUP_EMAIL` and `CLICKUP_PASSWORD`. No other command prompts. |
| 1.2 TTY detection treats non-TTY stdin as headless | fail | B | C | `login.go:48` `fmt.Scanln` and `:54` `term.ReadPassword(syscall.Stdin)` have no `term.IsTerminal` guard — a non-TTY agent with no env set still hits the prompt. |
| 1.3 Confirmation-bypass flag exists for destructive ops | fail | F | C | `task delete` (`task.go:371`) defines no `--force`/`--yes`; no bypass flag exists (shares fix with 4.2). |
| 1.4 Interactive menus have a flag/file equivalent | pass | | C | No select/menu prompts; multi-team case just prints `Use --team-id` (`main.go:108-114`). |
| 1.5 Bypass convention consistent | na | | C | 0 bypass flags defined → N/A. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 Supports structured (JSON) output | pass | | C | `--json` on most data commands, e.g. `task.go:49-54`. |
| 2.2 Every data-returning command supports `--json` | fail | F | C | `status` (`main.go:205-248`) and `config show` (`main.go:143-191`) emit structured auth/config data with no `--json`; `field set` also lacks it. Per-handler check, not declaration. |
| 2.3 One consistent flag name (`--json`) | pass | | C | Only `--json`; `attachment get --output/-o` is a file path, not a format selector. |
| 2.4 Exit codes: 0 success / non-zero failure | pass | | C | `RunE` errors bubble to `main.go:251-254` → `os.Exit(1)`; success returns nil (cobra). |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | | C | JSON/data to `os.Stdout`; errors to stderr (`main.go:252`); warnings to stderr (`inbox.go:308`, `inbox_comments.go:206`). |
| 2.6 ANSI/color suppressed when not a terminal | pass | | C | No color libraries or ANSI escapes anywhere (histogram uses plain `█`); nothing to suppress. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message | pass | | C | Errors wrapped via `fmt.Errorf(...: %w)`, printed to stderr; no `panic`/bare traceback in `cmd/`. |
| 3.2 Input validated early, before side effects | pass | | C | `task create` checks `--name` (`task.go:325`) and priority range (`:343-349`) before the API call. |
| 3.3 Enum/choice rejections enumerate the valid set | fail | F | C | `field set` dropdown/label rejections don't list valid options though they're in hand: `field.go:130` `invalid option '%s'`, `field.go:141` `invalid label '%s'`. (priority does enumerate at `task.go:275`.) |
| 3.4 Errors include corrective guidance | pass | | C | e.g. `task.go:32` "Run: cu config set --token"; `inbox.go:54` step-by-step JWT help. |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations idempotent | na | | Ft | Creates (`task/docs/pages create`, `comment/attachment add`) wrap the ClickUp REST API; idempotency is the upstream server's responsibility. |
| 4.2 Destructive ops require an explicit non-default flag | fail | B | C | `task delete` (`task.go:371-405`) calls `client.DeleteTask` immediately with no `--force`/confirmation. |
| 4.3 Consequential ops support `--dry-run` | fail | F | C | Consequential handlers (update/delete/create/field set/page update/comment add) exist; none honor `--dry-run` → fail, not N/A. |
| 4.4 Mutation responses return the affected id | pass | | C | `task.go:366` (create id), `:304` (update CustomID), `:403` (delete id), `comment.go:141`, `docs.go:143/293`. |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | fail | B | C | `task list -n` defaults to **0 = no limit** (`task.go:417`); same for `comment list` (`comment.go:205`), `attachment list` (`attachment.go:242`), `view` (`view.go:85`); `docs list`/`pages list`/`field list` have no limit flag at all. Only `inbox assigned/mentions` default to 20 (`inbox.go:416,420`). |
| 5.2 List commands support filtering and pagination/cursor | fail | F | Ft | `task list` filters (assignee/list/status, `task.go:126-161`) but exposes no cursor/page token; `-n` only caps a full internal fetch. |
| 5.3 Truncated output signals truncation + narrowing hint | fail | F | C | `task.go:180-182` silently slices to the limit; no `truncated` flag or hint emitted (same in `attachment.go:53-56`). |
| 5.4 MCP wrapper tool-description budget | na | | C | No MCP server/wrapper in the repo. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | | C | Canonical, internally consistent set: `get/list/create/update/delete/set/add/reply`. Minor: `config show` (`main.go:143`) and `-n`/`--n` long name (vs `--limit`) — not banned, noted only. |
| 6.2 Flags follow conventions | pass | | C | `--json` (not `--format=json`); no `--skip-*`/`--no-confirm` aliases. |
| 6.3 Naming internally consistent across subcommands | pass | | C | `--json`, `-n`, `--stdin` used uniformly across handlers. |
| 6.4 Documented naming policy + mechanical CI check | fail | T | Ft | No naming policy doc and no CI/lint enforcing vocabulary. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection command | fail | B | Ft | No `agent-context`/`--schema`/`dump-schema` emitting the command/flag tree. CLAUDE.md/README.md/SDK.md are prose (does not satisfy 7.1). |
| 7.2 Introspection is versioned (`schema_version`) | na | | C | 7.1 fails. |
| 7.3 Long-form skill manifest (`SKILL.md`) teaches workflows | fail | T | Ft | No `SKILL.md`/skills dir teaching agent workflows; `.claude/napkin.md`, `SDK.md`, `docs/` are dev docs, not a workflow manifest. |
| 7.4 Introspection generated/validated against impl | na | | Ft | 7.1 fails. |

### P8. Async-aware execution — *entire principle N/A (wraps no async API)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | | Ft | All ClickUp calls are synchronous REST; no job id / `status: queued` returned. |
| 8.2 Poll loop uses exponential backoff + jitter | na | | C | No poll loop. |
| 8.3 Persistent job ledger | na | | Ft | No async work / ledger. |
| 8.4 `jobs list/get/prune` command | na | | Ft | No async work. |

### P9. Persistent identity through profiles — *entire principle N/A (auth-centric config, already persisted)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse recurring non-auth config bundle | na | | Ft | Persisted state (`config.go:10-19`) is auth (token/JWT/refresh) plus `team_id`/`inbox_region`, already saved via `cu config set`; no recurring non-auth flag cluster is forced per-invocation. |
| 9.2 Profile management subcommands | na | | Ft | No profiles (9.1 N/A). |
| 9.3 `--profile` root flag + precedence | na | | C | No profiles. |
| 9.4 Profiles in machine introspection | na | | C | No profiles / 7.1 fails. |
| 9.5 Stable, documented storage location | na | | C | No profile system (precondition absent). Note: a single global config does live at a stable `~/.cu/config.json`, mode 0600 (`config.go:31,69`). |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel (`feedback <text>`) | fail | B | Ft | No `feedback` command; nothing writes local feedback JSONL. |
| 10.2 Feedback POST upstream when configured | na | | C | 10.1 fails. |
| 10.3 Artifact-producing commands support `--deliver` | fail | F | Ft | `attachment get` downloads files (`attachment.go:128-237`) via bare `--output`/`--dir` only — no file/webhook/stdout scheme abstraction → fail, not N/A. |
| 10.4 File sinks atomic + unknown-scheme refusal | na | | C | No `--deliver` (10.3). |
| 10.5 `--deliver` + `feedback` in machine introspection | na | | C | Depends on 7.1 (fails) and absent features. |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] **1.2 (B)** — Guard the `login` email/password prompts with `term.IsTerminal(int(syscall.Stdin))`; return an error pointing at `--email`/`CLICKUP_EMAIL`/`CLICKUP_PASSWORD` when not a TTY.  (`login.go:47-58`)
- [ ] **4.2 (B)** — Add `--force` to `task delete` and refuse to delete without it. Same edit clears **1.3 (F)**.  (`task.go:371-405`, flag in `init` ~`:435`)
- [ ] **5.1 (B)** — Give list commands a bounded default limit (change `-n` default 0→e.g. 100; add a bounded `-n` to `docs list`/`pages list`/`field list`).  (`task.go:417`, `comment.go:205`, `attachment.go:242`, `view.go:85`, `docs.go`, `field.go`) *(behavior-changing — see fix notes)*
- [ ] **2.2 (F)** — Add `--json` to `status` and `config show` (and `field set`).  (`main.go:143,205`)
- [ ] **3.3 (F)** — Include the valid option/label set in `field set` rejection errors.  (`field.go:130,141`)
- [ ] **5.3 (F)** — Emit a truncation hint to stderr when a list is capped.  (`task.go:180`, `attachment.go:53`)
- [ ] **4.3 (F)** — Add `--dry-run` to consequential handlers, returning a preview before the client mutation call. *(spread across many handlers — non-local)*

### Friction (conformance, lower priority)
- Covered above (2.2, 3.3, 5.3, 4.3, 1.3).

### Proposals — features, not auto-built (failing `feature` checks)
- **7.1 (B, Ft)** — `agent-context`/`--schema` command emitting the real cobra command+flag tree as JSON. Requires walking `rootCmd`; go-ahead needed.
- **10.1 (B, Ft)** — `feedback <text>` command writing local JSONL.
- **5.2 (F, Ft)** — Expose cursor/page tokens on list commands (`task list`, `view`).
- **10.3 (F, Ft)** — `--deliver` scheme abstraction (file/webhook/stdout) for `attachment get` and other artifact producers.
- **6.4 (T, Ft)** — Documented naming policy + CI/lint check enforcing the verb/flag vocabulary.
- **7.3 (T, Ft)** — Long-form `SKILL.md` workflow manifest for agents.
