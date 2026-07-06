# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/msgvault  (Go / cobra v1.10.2; CLI surface = `cmd/msgvault/cmd/`)
**Date:** 2026-07-06
**Score:** 23 / 32 applicable checks (72%)
**Failing gaps:** 2 Blocker · 6 Friction · 1 Target
**⚠ Suspicious N/A:** Principle **P8 (async-aware execution)** returned entirely N/A. This is judged correct: the daemon/client split proxies long-running `sync`/`verify`/`run` as **synchronous blocking HTTP streams** (`internal/daemonclient/cli.go:547-580`), never a submit→job-id→poll flow — no command returns a job id or `status: queued`, and there is no client-side poll loop. Verify the recon before trusting this N/A.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on interactive prompt without a bypass | pass | — | C | Destructive prompts honor a *read* `--yes` (deduplicate.go:920; deletions.go:453; delete_deduped.go:70; remove_account.go:68); all readers treat non-TTY/closed stdin as EOF→cancel/error, never infinite block (confirm.go:48-80). |
| 1.2 Non-TTY stdin treated as headless | pass | — | C | Reauth callers derive `interactive` from `isatty.IsTerminal(os.Stdin.Fd())` and switch to out-of-band hint (root.go:516-521; calendar.go:52-53; sync.go:235); IMAP password path routes non-terminal stdin to pipe reader (addimap.go:34-50). |
| 1.3 Confirmation-bypass flag exists for destructive ops | pass | — | C | `--yes/-y` on deduplicate/delete-staged/delete-deduped/remove-account/embeddings retire·activate (deletions.go:1468; delete_deduped.go:139; remove_account.go:48; embeddings_manage.go:149-151). |
| 1.4 Interactive menus have a flag/file equivalent | pass | — | C | Only interactive surfaces are `setup`/`tui`; all their data/config reachable headless via add-account/add-imap, config.toml, query/search/stats (setup.go:19-32; tui.go:23-110). |
| 1.5 Bypass convention consistent (one flag name) | pass | — | C | `--yes` uniformly = skip-confirm; `--permanent`/`--force-active`/typed `delete` are distinct-purpose, not competing bypass names (deletions.go:1468; confirm.go:45-59). |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | `printJSON` = `json.NewEncoder(os.Stdout)` (output.go:138-142); `--json` on search, list-accounts, show-message, verify, export-attachment, list-deletions, identity list/show, aggregate family. |
| 2.2 Every data-returning command supports `--json` (coverage) | **fail** | F | C | Seven data commands are text/tabwriter-only, no `--json`: stats (stats.go), collection list/show (collection.go:117-197), backup list (backup.go:130-153), cache-stats (build_cache.go:672), embeddings list (embeddings_manage.go:184), show-deletion (deletions.go:166). |
| 2.3 One consistent flag name (`--json`) | **fail** | F | C | `query` uses `--format json\|csv\|table` (query.go:210-214) instead of the boolean `--json` idiom (constants.go:29) the other ~9 commands share. (`--output/-o` on export names a file destination, not a format — not a conflict.) |
| 2.4 Exit codes: 0 success, non-zero failure, stable taxonomy | pass | — | C | 0 success / 1 error / 130 interrupt / 2 panic (main.go:14-15,26-31; root.go:268). RunE errors propagate non-zero. |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | Data via stdout/tabwriter/printJSON; slog handler on os.Stderr (root.go:40,148-159); prompts to `cmd.ErrOrStderr()` (confirm.go:92). |
| 2.6 ANSI/color suppressed when not a terminal | pass | — | C | No color on data paths (plain tabwriter); the only escapes are progress cursor control gated on isatty (deletions.go:1225; backup_progress.go:104; syncfull.go:669). No `NO_COLOR` guard, but no color reaches non-TTY data. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent/bare trace) | pass | — | C | RunE returns `fmt.Errorf(...%w...)`, cobra prints `Error:` (root.go:308-311); the 4 non-test panics are flag-registration/marshal invariants unreachable from user input, and caught by recoverAndLogPanic→exit 2 (root.go:250-269). |
| 3.2 Input validated early, before side effects | pass | — | C | search validates --mode/--message-type/--limit/query before scope/DB work (search.go:69-99); add-calendar validates before writes (calendar.go:224-228). |
| 3.3 Enum/choice rejections enumerate the valid set | pass | — | C | `--mode` → "want fts\|vector\|hybrid" (search.go:71); `--message-type` → "want one of: %s" (search.go:80-82). Minor gap: `openapi --format` (openapi.go:43) and dedup `--prefer` don't list the set — insufficient to fail. |
| 3.4 Errors include corrective guidance | pass | — | C | Copy-paste remediation: reauth hints (root.go:462-477,516-521), token-mismatch two-line fix (root.go:530-540), OAuth setup scan for client_secret*.json (root.go:378-419). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations idempotent (token or natural key) | pass | — | Ft | add-account keyed on (source_type,email) via GetOrCreateSource → "already authorized" no-op (addaccount.go:404); imports use checkpoint/resume (import_mbox.go:322); collections keyed by name. |
| 4.2 Destructive ops require an explicit, non-default flag | pass | — | C | delete-staged trash-default + `--permanent` opt-in + env gate + confirm (deletions.go:437-457); delete-deduped refuses without `--batch`/`--all-hidden` (delete_deduped.go:41-43); remove-account confirms (remove_account.go:150-164). |
| 4.3 Consequential ops support `--dry-run` | pass | low | C | Two headline ops have literal `--dry-run` (delete-staged deletions.go:1470; deduplicate deduplicate.go:1096); delete-deduped/remove-account use mandatory plan/count previews + confirm instead (delete_deduped.go:61; remove_account.go:146-164). Low-severity coverage gap, not broadly missing. |
| 4.4 Mutation responses return affected identifier(s) | pass | — | C | delete-staged prints batch IDs (deletions.go:167); collection/identity/add-account/delete-deduped/remove-account echo names/ids/counts (collection.go:96; identity.go:254-265; addaccount.go:457; remove_account.go:275). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default | pass | low | C | search `--limit 50` (search.go:266), aggregate family `--limit 50` (output.go:54), all MCP list tools default 20/50/100 clamp to 1000 (handlers.go:28). Weakness: `query [sql]` injects no default LIMIT (query.go:56) — power-user escape hatch, not enough to sink the check. |
| 5.2 List commands support filtering + pagination/cursor | pass | low | Ft | search: filters + `--limit`/`--offset` (search.go:266-276); MCP tools expose offset+limit+filters+has_more. Aggregate family has `--after/--before`+`--limit` but no `--offset` (minor). |
| 5.3 Truncated output signals truncation + narrowing hint | **fail** | F | C | list-deletions silently caps completed/cancelled to 10 via limitManifests (deletions.go:111-113) with only a soft "(recent)" label — no hidden-count, no hint; search "Showing N results" footer gives no more-available signal (output.go:93). (MCP side does carry has_more.) |
| 5.4 MCP tool descriptions fit a small audited budget | pass | — | C | 10 tools, mostly terse one-liners (server.go:329,336,352); only search_messages/get_message run long, encoding load-bearing pagination/mode contract (server.go:204-224,247-252). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | **fail** | F | C | `show-message`/`show-deletion`/`collection show`/`identity show` use `show` where canonical is `get`/`view` (show_message.go:22; deletions.go:141; collection.go:39). Set is internally consistent (no ls/rm/info/new), so **downgraded Blocker→Friction** per methodology; fix = alias the canonical verb. |
| 6.2 Flags follow conventions | pass | — | C | `--yes`/`--force`/`--json`/`--permanent` idiomatic; no `--skip-confirm`/`--no-confirm`/`--format=json` anti-patterns; `--json` deliberately distinct from `--format` where multiple formats are real (constants.go:26-35). |
| 6.3 Naming internally consistent across subcommands | **fail** | F | C | Two coexisting styles: flat hyphenated top-level (list-accounts, show-message, add-account, remove-account) vs newer parent+bare-verb groups (collection/identity/backup/embeddings/serve `{list,show,add,...}`). Self-consistent within each, split correlates with feature age → Friction. |
| 6.4 Documented naming policy + mechanical CI/lint check | **fail** | T | Ft | `.golangci.yml` lints only Go identifiers (revive/errname), no verb-vocabulary check; `.github/workflows/ci.yml` and `scripts/check-docs.sh` have no vocab gate. No enforced policy → FAIL@T. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable command/flag schema | **fail** | B | Ft | No surface emits the cobra command/flag *tree*. `openapi` dumps the daemon's Huma **REST API** schema, not CLI commands/flags (openapi.go:14; internal/api/openapi.go:33-40); `quickstart` is embedded markdown prose (quickstart.go:24); MCP registers 10 domain tools, not the command tree (server.go:122-132). No `--schema`/`dump-schema`/`agent-context`. |
| 7.2 Machine introspection is versioned | na | — | C | N/A — 7.1 fails; no CLI introspection surface to version. (openapi output carries an API `version`, but that versions the REST wire contract, not a CLI schema.) |
| 7.3 Long-form skill manifest teaches workflows | pass | — | Ft | `skills/claude-code/SKILL.md` — YAML frontmatter (name/description/triggers) + workflow body (SQL views, query recipes, CLI command table, ops tips) + `references/views.md`; plus quickstart.md/CLAUDE.md. |
| 7.4 Introspection generated/validated against real impl | na | — | Ft | N/A — 7.1 fails; no CLI introspection artifact to keep in sync. (openapi IS generated from the real Huma routes, but that's REST fidelity, not the cobra tree.) |

### P8. Async-aware execution  — *entire principle N/A*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | N/A — no command submits async work returning a job id; sync/verify/run proxy to the daemon via `runCLIStream`, a synchronous HTTP stream that blocks until a terminal `complete`/`error` event (cli.go:547-580). |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | N/A — no status-poll loop exists (8.1 absent). Only retry is `operationBusyWaiter.wait` (client.go:57-73), a fixed-1s daemon-concurrency-gate contention retry, not a job poll. |
| 8.3 Persistent job ledger across invocations | na | — | Ft | N/A — no async jobs to record. Nearest persistent record is deletion.Manifest (deletions.go:32), a deletion-staging workflow, not a job ledger. |
| 8.4 `jobs` command exposes list/get/prune | na | — | Ft | N/A — no `jobs` command; the list/show/cancel-deletion family is deletion staging, not an async-job ledger. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | pass | — | Ft | The recurring non-auth bundle (data dir, `[remote].url`, named `[oauth]` apps, `[vector]`/`[backup]`/`[analytics]`, per-account schedules) is already persisted in `~/.msgvault/config.toml` and auto-loaded every command (config.go:376-402; root.go:85). Only per-command flags are `--account`/`--collection` — data-scoping natural keys, not a config bundle. |
| 9.2 Profile management subcommands | na | — | Ft | N/A — no named `--profile` system exists and none needed; config.toml provides persistent named config (9.1). |
| 9.3 `--profile` root flag + precedence | na | — | C | N/A — no profile system. (Analogous `--home`/`--config` store-root selectors do implement flag>env>default precedence: config.go:322-331,382-386.) |
| 9.4 Profiles surfaced in machine introspection | na | — | C | N/A — no profiles to surface (and 7.1 absent). |
| 9.5 Stable, documented storage location | na | — | C | N/A (profile-specific). Noted: `~/.msgvault` is a stable, documented `~/.<cli>/` store (config.go:329; quickstart.md:8; CLAUDE.md:314-321), overridable via MSGVAULT_HOME/--home. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel exists (`feedback <text>` → local JSONL) | **fail** | B | Ft | No `feedback` command anywhere; grep for `feedback` across cmd/ and internal/mcp/ returns zero matches. |
| 10.2 Feedback can POST upstream when configured | na | — | C | N/A — 10.1 fails; no feedback channel to submit. |
| 10.3 Artifact commands support `--deliver` (stdout/file/webhook) | **fail** | F | Ft | Artifacts are produced (export-eml/attachment/attachments) but expose only a bare `--output/-o` file sink + `-` stdout sentinel (export_eml.go:107; export_attachment.go:289) — no scheme/webhook abstraction. Per methodology, bare `--output` = partial credit → FAIL@F. (export-token's `--to`/`--api-key` push is a bespoke OAuth-token path, not a reusable deliver scheme.) |
| 10.4 File sinks atomic; unknown schemes get structured refusal | na | — | C | N/A — no `--deliver` scheme dispatch. Noted: existing sinks are atomic (os.CreateTemp+os.Rename export_attachment.go:193-254; fileutil.SecureWriteFile export_eml.go:97). |
| 10.5 `--deliver` + `feedback` surfaced in introspection | na | — | C | N/A — no deliver/feedback affordances to surface, and 7.1 absent. |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
*(No conformance Blockers — both Blockers are `feature` kind, see Proposals.)*

### Friction (conformance, lower priority)
- [ ] 2.2 — Add a `--json` flag (reuse `flagJSON` + `printJSON`) to the seven text-only data commands: stats, collection list/show, backup list, cache-stats, embeddings list, show-deletion. (stats.go; collection.go:117-197; backup.go:130-153; build_cache.go:672; embeddings_manage.go:184; deletions.go:166)
- [ ] 2.3 — Standardize the JSON idiom: make `query` accept boolean `--json` (alias for `--format json`) so JSON selection is uniform across the CLI. (query.go:210-214)
- [ ] 5.3 — On CLI truncation, print a narrowing hint: list-deletions should emit "… N more (use --json for the full list)" when `limitManifests` drops entries; search/aggregate footer should surface a "more available, raise --limit/--offset" hint when returned == limit. (deletions.go:111-113; output.go:93)
- [ ] 6.1 — Add canonical aliases via cobra `Aliases` on the `show-*`/`show` commands (e.g. `get`/`view`); no rename needed. (show_message.go:22; deletions.go:141; collection.go:39; identity.go:145)
- [ ] 6.3 — Converge the two naming styles: introduce parent+bare-verb groups (e.g. `account {list,show,add,remove}`, `message show`) that alias the legacy flat hyphenated commands, so top-level and grouped surfaces match.

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (Blocker) — Add a machine-readable CLI introspection command (e.g. `msgvault --schema` / `introspect`) that walks the cobra command graph and emits every command/subcommand/flag (name, type, default, help) as structured JSON, ideally codegen'd from the tree so it can't drift (would then also satisfy 7.2 `schema_version` and 7.4 in-sync). Requires your go-ahead.
- 10.1 (Blocker) — Add a `feedback <text>` command appending structured entries (timestamp, version, text) to a local JSONL file (e.g. `~/.msgvault/feedback.jsonl`), optionally with a discoverable opt-in upstream POST (10.2). Requires your go-ahead.
- 10.3 (Friction) — Introduce a unified `--deliver` scheme abstraction (`stdout:`, `file://`, `https://` webhook) shared across export-eml/attachment/attachments, retaining the existing atomic temp+rename for file sinks and returning a structured refusal for unknown schemes (10.4). Requires your go-ahead.
- 6.4 (Target) — Add a documented verb/flag vocabulary policy plus a mechanical gate (a Go test or CI script that walks the cobra tree and asserts each command's leading verb + flag names against an allowlist). Requires your go-ahead.
