# CLI Agent-Nativeness Scorecard

**Target:** `~/Source/kata` (Go / cobra; task/backlog tracker, thin HTTP client to a local huma/net-http daemon over SQLite)
**Date:** 2026-07-06
**Score:** 20 / 32 applicable checks (62.5%)
**Failing gaps:** 3 Blocker · 7 Friction · 2 Target
**⚠ Suspicious-N/A:** Principle **P8 (async)** returned entirely N/A. This is **legitimate**: the CLI submits no async jobs and returns no job ids — `events --tail` is an SSE stream, not job submission. No masking suspected. (Assessment is static/read-only; the target repo, its git state, and its binary were untouched.)

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on a prompt without a bypass | pass | — | C | Only prompts are the destructive confirmations in `resolveConfirm` (delete.go:80-108); non-TTY without `--confirm` returns ExitConfirm(6), never blocks (delete.go:85-90). |
| 1.2 Non-TTY stdin treated as headless | pass | — | C | `if !isTTY(os.Stdin)` guards the prompt and errors out (delete.go:85); `isTTY` via x/term (tty.go:18-22). |
| 1.3 Confirmation-bypass flag for destructive ops | pass | — | C | `--force` + `--confirm` on delete (delete.go:31), purge (purge.go:24); `--force` on projects remove/detach (projects.go:547/602). |
| 1.4 Interactive menus have a flag/file equivalent | pass | — | C | Pass by absence: no select/menu prompts exist — only yes/no-style typed confirmations, all bypassable via `--confirm`. |
| 1.5 Bypass convention consistent (one flag name) | pass | — | C | `--force` used consistently across every destructive op; `--confirm <string>` is the uniform typed-confirmation value (delete.go:31, purge.go:24, projects.go, import.go:43). |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports JSON output | pass | — | C | Global `--json` (main.go:44) + `emitJSON` envelope splicing `kata_api_version:1` (helpers.go:133-162). |
| 2.2 Every data command supports `--json` (coverage) | **fail** | F | C | `export` (export.go:68), `import` (import.go:102), `restore` (restore.go:40) accept `--json` but emit **no** JSON object — the flag only silences the human line. Declared ≠ honored. |
| 2.3 One consistent flag name (`--json`) | pass | — | C | Only `--json`; no `--format`/`-o json`. `export --output <path>` is a file sink, not a format selector (main.go:44). |
| 2.4 Exit codes: stable taxonomy | pass | — | C | 8-code taxonomy 0=OK..7=DaemonUnavail (helpers.go:17-27); mapped via `cliError.ExitCode` / `exitCodeForErr` (main.go:112,212). |
| 2.5 Data → stdout, diagnostics → stderr | pass | — | C | `emitError` writes to stderr (main.go:127-161); data via `emitJSON` to `OutOrStdout`; warnings to stderr (client.go:37, init.go:306). |
| 2.6 ANSI/color suppressed off-terminal | pass | — | C | Pass by absence: command printers emit plain `fmt.Fprintf`+`textsafe.Line` (e.g. ready.go:74); the vendored `termenv`/color code is confined to the interactive bubbletea TUI. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message | pass | — | C | `emitError` renders `kata: <msg>` or a `{"error":{...}}` envelope (main.go:127-161); `SilenceErrors` means main owns all rendering, no bare panics. |
| 3.2 Input validated early, before side effects | pass | — | C | `--priority`/`--limit` range-checked client-side before any HTTP call (list.go:20-30, create.go:56-62, ready.go:20). |
| 3.3 Enum rejections enumerate the valid set | pass | — | C | Priority errors state the 0–4 range (create.go:56-62); import reason validated against `done|wontfix|duplicate` (imports.go:635). |
| 3.4 Errors include corrective guidance | pass | — | C | Flag-error handler rewrites shorthand errors with a `--` separator hint (main.go:184); daemon-unavailable error tells how to proceed (quickstart.go:78-81); confirm error prints the exact `--confirm` string to pass (delete.go:87). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create ops idempotent | pass | — | Ft | kata owns its data (not upstream): `create --idempotency-key` sends `Idempotency-Key` header, server dedups → 409 `duplicate_candidates` (create.go:41,114-117; handlers_issues.go:558). |
| 4.2 Destructive ops require an explicit non-default flag | pass | — | C | delete/purge require `--force` + typed `--confirm`; projects remove/detach require `--force` (delete.go:31, purge.go:24, projects.go:547/602). |
| 4.3 Consequential ops support `--dry-run` | **fail** | F | C | Consequential ops exist (delete, purge, projects merge/remove, edit, import --force) but **no `--dry-run` anywhere** in the tree. Per detection methodology: subject present, capability missing ⇒ fail, not N/A. |
| 4.4 Mutation responses return affected id(s) | pass | — | C | Mutations echo the daemon body (issue ref/id) via `printMutation`/`emitJSON` (printMutation.go:222, create.go, assign.go:65). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | **fail** | B | C | `ready` defaults to `--limit 0` = **no limit** (ready.go:82); `projects list` has **no limit flag at all** (projects.go:42). `list`(50)/`search`(20)/`events`(100) are bounded, but two list-style commands are unbounded by default. |
| 5.2 List commands support filter + pagination/cursor | **fail** | F | Ft | `list` filters (status/priority) but has **no cursor**; only `events` offers `--after`/`next_after_id` (events.go:78-83). search/ready/list lack cursor pagination (list.go:107-110). |
| 5.3 Truncated output signals truncation + hints | **fail** | F | C | `list`/`search` cut off at the limit with no `truncated` flag or narrowing hint in the payload; only `events` returns a resume cursor. |
| 5.4 MCP wrapper token budget | na | — | C | No MCP wrapper exists (no mcp/JSON-RPC/stdio-server code anywhere). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | **fail** | F | C | `show <ref>` used where `get` is conventional (show.go:14). Downgraded from Blocker to Friction: the verb set is otherwise canonical (create/list/delete/edit) and `show` is a coherent `gh view`-style choice. Fix: alias `get`. |
| 6.2 Flags follow conventions | pass | — | C | `--force`, `--json`, `--limit` — no `--skip-*`, `--no-confirm`, or `--format=json` aliases (main.go:44, delete.go:31). |
| 6.3 Naming internally consistent | **fail** | F | C | Removal verbs drift: `label rm` (label.go:59) vs full `delete`, and vs the `un-` family `unlink`/`unassign`/`unblock` (link.go, assign.go:23). |
| 6.4 Documented naming policy + mechanical CI check | **fail** | T | Ft | No naming/vocabulary lint. `.golangci.yml`/`prek.toml` are generic Go lint only; absence ⇒ fail@T. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable command/flag schema | **fail** | B | Ft | No `agent-context`/`--schema`/`dump-schema`. `quickstart`/`agent-instructions` is **prose** (quickstart.go), and `--json` just wraps that prose in `{"quickstart":"..."}`. OpenAPI is deliberately disabled (`OpenAPIPath = ""`, server.go:52). No command/flag tree is emitted as data. |
| 7.2 Schema is versioned | na | — | C | N/A — 7.1 fails (no machine schema to version). |
| 7.3 Long-form skill manifest | **fail** | T | Ft | No `SKILL.md`/skills dir. `AGENTS.md`/`CLAUDE.md`/`docs/superpowers/specs/` are prose; `quickstart` prints a prose agent contract (partial credit only, not a manifest). Absence ⇒ fail@T. |
| 7.4 Introspection generated/validated in sync | na | — | Ft | N/A — 7.1 fails (nothing to keep in sync). |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | N/A — the CLI submits no async jobs and returns no job id/`status:queued`. |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | N/A — no async poll loop. (`events --tail` SSE reconnect has 1s→30s backoff, events.go:189-368, but is streaming, not job polling.) |
| 8.3 Persistent job ledger | na | — | Ft | N/A — no job ledger file written. |
| 8.4 `jobs` command over the ledger | na | — | Ft | N/A — no jobs concept. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Recurring non-auth config is persisted & reused | pass | — | Ft | The recurring non-auth bundle (project identity, actor) is persisted and auto-resolved: workspace→project binding in committed `.kata.toml` (init.go:105, config/project_config.go); actor via `$KATA_AUTHOR`/git (helpers.go:97). Agents are not forced to re-specify it, so the Blocker condition never fires. |
| 9.2 Profile management subcommands | na | — | Ft | N/A — no named-profile system; kata uses cwd-bound directory config (`.kata.toml`) instead of `profile save/use/list`. |
| 9.3 `--profile` root flag + precedence | na | — | C | N/A — no profiles (config selection is by `--workspace`/cwd, not a `--profile` flag). |
| 9.4 Profiles in machine introspection | na | — | C | N/A — no profiles and 7.1 absent. |
| 9.5 Stable, documented storage location | pass | — | C | `$KATA_HOME` or `~/.kata` with DB/runtime/hooks paths (config/paths.go:15-135), documented in the design spec. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel (`feedback <text>`) | **fail** | B | Ft | No `feedback` command anywhere (grep empty). (The app tracks issues, but there is no self-feedback channel for the CLI tool itself.) Absence ⇒ fail@B. |
| 10.2 Feedback POSTs upstream when configured | na | — | C | N/A — 10.1 fails. |
| 10.3 Artifact commands support `--deliver` | **fail** | F | Ft | `export` produces a JSONL artifact but only via a bare `--output <path>` (export.go:75) — no scheme abstraction (file/webhook/stdout). Per detection: artifact produced without `--deliver` scheme ⇒ fail@F. |
| 10.4 File sinks atomic + unknown-scheme refusal | na | — | C | N/A — no `--deliver` scheme system exists. |
| 10.5 `--deliver`+`feedback` in machine introspection | na | — | C | N/A — depends on 7.1 (absent) and neither capability exists. |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 5.1 — Give `ready` a bounded default (e.g. `--limit 50`, keep `0`=explicit-unbounded) and add a default limit to `projects list`.  (ready.go:82, projects.go:42)

### Friction (conformance, lower priority)
- [ ] 2.2 — Make `export`/`import`/`restore` emit a real `emitJSON` envelope under `--json` (e.g. `{count}`/`{imported}`/`{restored, ref}`) instead of only silencing the human line.  (export.go:68, import.go:102, restore.go:40)
- [ ] 4.3 — Add `--dry-run` to consequential ops (delete, purge, projects merge/remove, import --force): validate + report the intended effect, skip the mutating POST.
- [ ] 5.3 — Include a `truncated`/`next` signal + narrowing hint in `list`/`search` payloads when the limit is hit (mirror `events`' `next_after_id`).  (list.go, search.go)
- [ ] 6.1 — Alias `get` → `show` for canonical-verb compatibility.  (show.go:14)
- [ ] 6.3 — Rename `label rm` → `label remove` (or align on the `un-`/`delete` family) for internal consistency.  (label.go:59)
- [ ] (related, honesty) `close --reason` documents `done|wontfix|duplicate` (close.go:20) but stores any string (queries.go:873) — validate the enum to match the `import` path (imports.go:635).

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (Blocker) — Add an `agent-context`/`--schema` command that emits the real cobra command+flag tree as structured, versioned JSON (re-enabling the huma OpenAPI at server.go:52 could feed it); requires your go-ahead.
- 10.1 (Blocker) — Add a `feedback <text>` command writing local JSONL (optional upstream POST when configured); requires your go-ahead.
- 5.2 (Friction) — Add cursor pagination (`--after`/`next`) to `list`/`search`, matching the `events` model.
- 10.3 (Friction) — Generalize `export --output` into a `--deliver` scheme abstraction (stdout/file/webhook) with atomic file writes and structured refusal of unknown schemes.
- 6.4 (Target) — Add a documented naming policy + a CI/lint check enforcing the verb/flag vocabulary.
- 7.3 (Target) — Ship a long-form `SKILL.md` (or skills dir) teaching agent workflows, beyond the `quickstart` prose.
