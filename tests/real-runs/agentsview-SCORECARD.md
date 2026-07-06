# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/agentsview (Go / cobra CLI — `cmd/agentsview`)
**Date:** 2026-07-06
**Score:** 20 / 32 applicable checks (62.5%)
**Failing gaps:** 3 Blocker · 6 Friction · 3 Target
**Suspicious N/A:** P8 (Async-aware execution) is entirely N/A — legitimate: the CLI owns a local SQLite archive and exposes no async job-submit/poll API (no job ids, `status: queued`, or poll loop). No other principle is wholly N/A.

Scope note: only the Go cobra command surface (`cmd/agentsview/`, `internal/`) was assessed. `frontend/`, `desktop/`, `node_modules/`, and helper binaries (`cmd/testfixture`, `cmd/benchgate`, `internal/pricing/cmd/*`) were excluded per instructions.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on a prompt without a bypass | pass | | C | Destructive `prune` honors `--yes` (prune.go:122); `update` honors `--yes` (update.go:90); prompts read via `bufio.Scanner`/`Reader` and return the safe default (abort/"no") on EOF. `pg service install` lingering prompt (pg_service.go:152) has no bypass flag but is non-destructive and degrades to "no" on EOF. |
| 1.2 Non-TTY stdin treated as headless | fail | B | C | No `isatty`/`term.IsTerminal` guard anywhere; prompts at prune.go:152, update.go:90, pg_service.go:152 rely only on scanner EOF rather than detecting a non-TTY and skipping the prompt. |
| 1.3 Confirmation-bypass flag for destructive ops | pass | | C | `prune --yes` (cli.go:364), `prune --dry-run` (cli.go:363). |
| 1.4 Interactive menus have flag/file equivalent | pass | | C | No select/menu prompts exist. |
| 1.5 Bypass convention consistent | pass | | C | Confirmation bypass is `--yes` on both prune and update; no mixed names. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | | C | Broad `--json`/`--format json` → `json.NewEncoder(cmd.OutOrStdout()).Encode` on session/stats/secrets/export/etc. (session.go:229, stats.go:74, export.go:228). |
| 2.2 Every data command supports `--json` (coverage) | fail | F | C | `pg status` (cli.go:620) and `duckdb status` (cli.go:707) return status data but declare no `--json`/`--format`; `usage statusline`/`usage cursor` also human-only. Verified per-handler, not by declaration. |
| 2.3 One consistent flag name | fail | F | C | `--format human|json` and its `--json` alias coexist on every machine-readable command (session.go:229-233); the rubric flags `--format=json` coexisting with `--json`. Deliberate alias, but two names for one concept. |
| 2.4 Exit codes: stable non-zero taxonomy | pass | | C | `exitCodeFromError` (cli.go:55) maps `cliExitError.code`; codes 0/1/2/3/4 (cli.go:25,211; export.go:19,549; token_use.go:20-23). |
| 2.5 Data → stdout, diagnostics → stderr | pass | | C | Progress/warnings to `os.Stderr` (secrets.go:68, main.go:57, cli.go:601); JSON/data to stdout. (`session_usage.go:55`/`token_use.go:220` write to `os.Stdout` directly rather than `cmd.OutOrStdout()`, but still stdout.) |
| 2.6 ANSI/color suppressed off-terminal | pass | | C | No ANSI/color libraries used anywhere; `term.GetSize` used only for help wrapping (cli.go:891). Nothing to leak. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Clear failure message (no bare stack/panic) | pass | | C | `fatal()` (main.go:612) and `cliExitError` print messages; sole `panic` (cli.go:326) is a programmer-error guard on `MarkHidden`. |
| 3.2 Input validated early | pass | | C | Enum flags validated at parse time before side effects (`formatFlag.Set` session.go:215; export `--format` export.go:26). |
| 3.3 Enum rejections enumerate valid set | pass | | C | `formatFlag.Set` → "must be human or json" (session.go:221); `--type` claude-ai/chatgpt (cli.go:411); `--confidence` definite/candidate/all (secrets.go:150); `--sort` via `db.SortKeys()` (session_list.go:166). |
| 3.4 Errors include corrective guidance/example | fail | F | C | `SilenceUsage:true` on commands; `fatal()`/wrapped errors state the problem but generally give no example invocation. Enum errors list valid values (partial credit) but lack a corrective command example. |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create ops idempotent (idempotency/natural key) | pass | | Ft | Ingestion (`sync`/`import`) upserts sessions by natural session ID; re-running is idempotent, `--full` forces a full re-derive (prune.go/main.go resync). |
| 4.2 Destructive ops require explicit non-default flag | pass | | C | `prune` deletes only after `--yes` or interactive "y"; headless EOF → abort (prune.go:122-129). `sync --full`/`classifier rebuild` gated by explicit `--full` (classifier.go:164). |
| 4.3 Consequential ops support `--dry-run` | fail | F | C | Only `prune` has `--dry-run` (cli.go:363). Consequential `sync --full`, `pg push`, `duckdb push`, `classifier rebuild` rewrite the archive / external mirrors with no `--dry-run`. |
| 4.4 Mutation responses return affected id(s) | fail | F | C | `prune` prints counts only ("Deleted %d sessions, removed %d files", prune.go:144), not the deleted session IDs; sync reports counts, not affected IDs. |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | pass | | C | `session list` default `db.DefaultSessionLimit` (session_list.go:158), `health` default 20/max 500 (health.go:25), `secrets list` default 50/max 500 (secrets.go:154), `export sessions` default `MaxSessionLimit`. (`projects` cli.go:416 is unbounded but inherently low-cardinality.) |
| 5.2 Filtering + pagination/cursor | pass | | Ft | `session list` rich filters + opaque `--cursor` (session_list.go); `export sessions --cursor/--all` (export.go); `secrets list --cursor` (secrets.go:155). |
| 5.3 Truncation signalled + narrowing hint | pass | | C | `session list` prints "More results: --cursor …"; `secrets list` prints next cursor; MCP `get_messages` flags per-message truncation (server.go:92). |
| 5.4 MCP tool descriptions fit a small audited budget | fail | T | C | MCP has 6 tools with prose descriptions (server.go:63-115); a couple (`search_sessions`, `get_messages`) run ~90 words and there is no token-budget audit test enforcing a ceiling. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | | C | `get`/`list`/`search`/`export`/`import`/`sync`/`prune`/`stop`/`status`/`update`/`push`/`scan` — all canonical; no `info`/`ls`/`rm`/`new`. |
| 6.2 Flags follow conventions | pass | | C | `--force`, `--yes`, `--json`, `--limit`, `--cursor` used; no `--skip-*`/`--no-confirm` aliases. |
| 6.3 Naming internally consistent | pass | | C | `--limit`, `--cursor`, `--json`, `--yes`, `--full`, `--projects` used consistently across subcommands. |
| 6.4 Documented naming policy + mechanical CI check | fail | T | Ft | No documented CLI naming policy and no lint/CI check enforcing vocabulary (AGENTS.md is prose working-rules only). |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable command/flag schema | fail | B | Ft | No `agent-context`/`--schema`/`dump-schema` emitting the cobra command/flag tree. `openapi` (cli.go:240) emits the HTTP API schema, not the CLI surface; root help (writeRootHelp cli.go:806) is hand-rendered prose. |
| 7.2 Introspection versioned (`schema_version`) | na | | C | N/A — 7.1 absent. |
| 7.3 Long-form SKILL.md manifest | fail | T | Ft | No CLI SKILL.md/skills dir teaching workflows (unrelated `.agents/skills/*` only). |
| 7.4 Introspection generated/validated vs implementation | na | | Ft | N/A — 7.1 absent. |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | | Ft | N/A — no async job-submit API (no job ids / `status: queued`). |
| 8.2 Poll loop uses exponential backoff + jitter | na | | C | N/A — no async poll loop. |
| 8.3 Persistent job ledger | na | | Ft | N/A — no async jobs. |
| 8.4 `jobs` list/get/prune command | na | | Ft | N/A — no async jobs. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Recurring non-auth config can be persisted & reused | pass | | Ft | Non-auth config (server addr, PG/DuckDB targets) persists in `~/.agentsview/config.toml` with named `[pg.NAME]` targets + `default_pg` (config.go:375,564; session.go:179); commands don't force re-specification. |
| 9.2 Profile management subcommands | na | | Ft | N/A — no named-profile subsystem; config is a hand-edited TOML + env, not a `profile save/use/list` CRUD surface. |
| 9.3 `--profile` root flag + precedence | na | | C | N/A — no profile subsystem; target selection via `--pg` + env>config precedence, no `--profile`. |
| 9.4 Profiles in machine introspection | na | | C | N/A — no profiles and 7.1 absent. |
| 9.5 Stable documented storage location | na | | C | N/A — no profiles (config storage is `~/.agentsview/`, documented at cli.go:817, but that is config not a profile store). |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel (`feedback <text>` local JSONL) | fail | B | Ft | No `feedback` command anywhere in the command tree (cli.go:105-126). |
| 10.2 Feedback POST upstream when configured | na | | C | N/A — 10.1 fails. |
| 10.3 Artifact commands support `--deliver` | fail | F | Ft | `export sessions` and `session export` produce artifacts but only to stdout; no `--deliver`/`--output` scheme abstraction (file/webhook/stdout). |
| 10.4 File sinks atomic + unknown-scheme refusal | na | | C | N/A — no `--deliver`. |
| 10.5 `--deliver`+`feedback` in introspection | na | | C | N/A — depends on 7.1 (absent) and neither feature exists. |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 1.2 (B) — Add a `term.IsTerminal(os.Stdin.Fd())` guard so `prune`, `update`, and `pg service install` treat non-TTY stdin as headless (skip the prompt, take the safe default) instead of relying on scanner EOF. (prune.go:152, update.go:90, pg_service.go:152)

### Friction (conformance, lower priority)
- [ ] 2.2 (F) — Add `--json`/`--format` to `pg status` (cli.go:620), `duckdb status` (cli.go:707), `usage cursor`, and `usage statusline`.
- [ ] 2.3 (F) — Consolidate on one name: keep `--json` canonical and hide/deprecate the `--format` alias (session.go:229-233).
- [ ] 3.4 (F) — Add a corrective example/usage snippet to the common error paths (`fatal()` main.go:612, `cliExitError`).
- [ ] 4.3 (F) — Add `--dry-run` to `sync`, `pg push`, `duckdb push`, and `classifier rebuild` (currently only `prune` has it — cli.go:363).
- [ ] 4.4 (F) — Emit affected session IDs (not just counts) in `prune`/`sync` output, especially under `--json`. (prune.go:144)
- [ ] 5.4 (T) — Add a token-budget audit test over MCP tool descriptions and trim the verbose ones. (server.go:63-115)

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (B) — Add a machine-readable introspection command (`agent-context`/`dump-schema`) that walks the cobra tree and emits commands+flags as structured JSON with a `schema_version`; unblocks 7.2/7.4/9.4/10.5. Requires your go-ahead.
- 10.1 (B) — Add a `feedback <text>` command writing local JSONL (optionally POST upstream when a configured endpoint exists → 10.2). Requires your go-ahead.
- 6.4 (T) — Document a CLI naming policy and add a CI/lint check enforcing the verb/flag vocabulary. Requires your go-ahead.
- 7.3 (T) — Author a long-form SKILL.md manifest teaching agent workflows against the CLI. Requires your go-ahead.
- 10.3 (F) — Add a `--deliver` scheme abstraction (stdout/file/webhook, atomic file writes, structured refusal for unknown schemes → 10.4) to `export sessions`/`session export`. Requires your go-ahead.
