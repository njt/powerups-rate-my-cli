# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/go365 (Go / cobra Microsoft-365 CLI; handlers in `cmd/go365/main.go`, Graph client in `libgo365/`)
**Date:** 2026-07-07
**Rubric:** current hardened 47-check rubric (adds 2.7, 7.5; sharpened 2.2 / 5.2 / 5.3; "static ≠ runtime" methodology)
**Mode:** assess (static, read-only — the target CLI/binary was never run)
**Score:** 22 / 33 applicable checks (67%)
**Failing gaps:** 4 Blocker · 6 Friction · 1 Target
**Delta vs pre-hardening (22 / 35, 4B·7F·2T):** denominator 35→33 (more legitimate N/A); passes 22→22; % 63→67; **all 4 original Blockers persist (4.2, 6.1, 7.1, 10.1 — none remediated)**; Friction 7→6; Target 2→1 (7.3 now passes on a shipped SKILL.md). Both NEW checks (2.7 secrets, 7.5 version) PASS.

> ⚠️ **Whole-principle N/A:** P8 (Async-aware execution) is entirely N/A. This is **legitimate**, not suspicious — go365 is a synchronous Graph wrapper with no async/job-submitting command, which is P8's own documented escape clause. No other principle is wholly N/A.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | Pass by absence: repo-wide grep found **no** `bufio.NewReader(os.Stdin)`/`Scanf`/`survey.`/`confirm`/`ReadString` in any handler (only `internal/plugin/plugin.go:32` passes stdin through to a spawned plugin). CLI never blocks on input. |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | Pass by absence: no prompts exist, so none can prompt on a TTY. (No `isatty`/`IsTerminal` anywhere — nothing to guard.) |
| 1.3 Confirmation-bypass flag exists for destructive ops | fail | F | C | Destructive ops exist (see 4.2) but define **no** `--force`/`--yes`. Only `--force-new` exists (`main.go:2594`), which bypasses send-dedupe, not destruction. Not N/A (destructive ops present). |
| 1.4 Interactive menus have a flag/file equivalent | pass | — | C | Pass by absence: no select/menu prompts. |
| 1.5 Bypass convention consistent across subcommands | na | — | C | 0–1 bypass flags (only `--force-new`); nothing to be inconsistent. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | Per-command `--json` on ~40 commands (e.g. `main.go:724,741,752,3241`); `internal/output/output.go` WriteJSON / ListResponse envelope. |
| 2.2 Every data-returning command supports `--json` (coverage incl. mutations) | fail | F | C | **Sharpened-detection flip.** Mutations `calendar cancel` (`main.go:1166-1207`), `calendar delete` (`1221-1261`), `calendar respond` (`1141-1148`) register **no** `--json` flag and print human text only. `--json` is per-command (not a persistent root flag), so each gap is real. Reads are well covered; the mutation-coverage rule surfaces these three. |
| 2.3 One consistent flag name | pass | — | C | Always `--json` (bool). No `--format`/`-o json`. `drive get --output` is a file path, not a format selector (`main.go:3269`); `--agent` is a distinct concise mode, not a competing format name. |
| 2.4 Exit codes: 0 success / non-zero failure | pass | — | C | `RunE` handlers return wrapped errors; `main()` `os.Exit(1)` on non-nil (`main.go:6165-6167`), `SilenceUsage:true`/`SilenceErrors:false`. **Caveat (runtime risk):** `calendar respond` prints "Failed to respond…" then `return nil` (`main.go:1144-1150`) → exits 0 on total failure. Localized bug, not "always 0". |
| 2.5 Data → stdout, diagnostics → stderr | pass | — | C | Data via `output.WriteJSON(os.Stdout,…)`/`fmt.Print`; warnings/notes to `os.Stderr` (`main.go:416,595,3812,4845,5381`). |
| 2.6 ANSI/color suppressed off-terminal | pass | — | C | Pass by absence: no color library, no ANSI escapes anywhere — nothing to suppress. |
| 2.7 Structured output never emits raw secrets | pass | — | C | **NEW check.** No secret-bearing field reaches a JSON encoder: `Config` struct (`libgo365/config.go:11-17`) holds only tenant/client IDs, scopes, timezone, site — **no token field**. `status` (`main.go:207-234`) and `config show` (`285-303`) print no credential; `agent-guide --json` emits a static contract. MSAL tokens live in the `~/.go365` cache and are never serialized to stdout. (Confirm live in validate.) |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message | pass | — | C | Uniform `fmt.Errorf("…: %w", err)` via cobra `RunE`; `SilenceUsage:true` (`main.go:77-78`); no `panic` in handlers; `SuggestionsMinimumDistance:2` gives "Did you mean". |
| 3.2 Input validated before side effects | pass | — | C | `mail send` validates subject/to/body (`main.go:532-540`) before send; `drive share` validates `--type`/`--scope` (`3016-3031`) before acting. |
| 3.3 Enum/choice rejections enumerate the valid set | fail | F | C | Mixed → fail. `calendar respond` enumerates (`libgo365/calendar.go:362`) and `drive share` does (`main.go:3025,3030`), but **`presence set` validates nowhere** — handler passes the raw arg through (`main.go:4055-4058`), `SetPresence` posts it unchecked (`libgo365/teams.go:747-760`); the valid set lives only in `Long` help (`main.go:4037`). |
| 3.4 Errors include corrective guidance | pass | — | C | Usage examples in errors: `calendar respond` usage (`main.go:1130`), `calendar cancel` usage (`1184`), `--type is required (view or edit)` (`3017`), `--force-new` hint (`2717`). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations idempotent | pass | — | Ft | `libgo365/idempotency.go`: persisted store `~/.go365/idempotency.json` (0600, atomic temp+rename); explicit `--idempotency-key` 24h TTL + auto content-hash 5-min soft-block; `Record` only after success. Wired on all send/create commands (`main.go:546,748,3284,3322,4262,4280`). |
| 4.2 Destructive ops require an explicit non-default flag | **fail** | **B** | C | **Original Blocker — NOT remediated.** No confirmation flag on any destructive command; each acts immediately: `drive rm` (`main.go:2979`), `calendar cancel` (`1196`), `calendar delete` (`1250`), `drive unshare` (`3215`). `mail delete` soft-deletes by default (recoverable) and gates only its *permanent* path behind `--permanent` (`681`) — the plain delete is unguarded. |
| 4.3 Consequential ops support `--dry-run` | fail | F | C | No `--dry-run`/`--dryRun` anywhere (grep: 0 hits). Consequential ops exist (send, delete, cancel, share) → fail, not N/A. |
| 4.4 Mutation responses return the affected id | pass | — | C | Ids returned where output exists: `mail delete` `{id}` (`main.go:697`), `drive unshare` `{permissionId}` (`3222`), `calendar create` object (`1636`); text mutations still name the id ("Cancelled event <id>" `1201`). Only `mail send` lacks an id — an upstream Graph `/sendMail` limitation (`602`). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | pass | — | C | Responses are bounded by Graph server-side paging + `nextPageToken`; `mail list` adds an explicit cap `DefaultMessageLimit=100` (`libgo365/mail.go:14`). Note: only mail / `sites search`(10) / `sharepoint search`(20) / `teams messages`(20) set an explicit cap; calendar/drive/teams/lists/pages inherit Graph's page size (still bounded). |
| 5.2 List commands support filtering + pagination/cursor | pass | — | Ft | `--page-token` (skiptoken cursor, `libgo365/mail.go:93-133`) + `--skip` offset + filters (`--from/--subject/--search`). **Runtime risk:** losslessness not statically provable — a small `--top`/`--skip` on cursor lists could under-return; calendar uses `$skip`-offset only. Flag for validate. |
| 5.3 Truncated output signals truncation + consistency | pass | — | C | `ListResponse.Truncated` (`output.go:36-47`, `omitempty`) set only on client-side aggregation caps (`teams chat list`, `pages ls --folder`) with stderr narrowing hints (`main.go:3812,4845`). Trap avoided: `truncated` is **omitted** (never `false`-beside-cursor); cursor lists signal more via `hasMore`/`nextPageToken`. **Runtime risk:** two different completeness signals by command type — confirm no agent-confusion in validate. |
| 5.4 MCP wrapper tool-description budget | na | — | C | No MCP server / tool-description surface exists (grep: 0 hits). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | **fail** | **B** | C | **Original Blocker — not remediated.** Verb set is internally **inconsistent** across sibling nouns: destroy is `rm` (drive `main.go:2960`) vs `delete` (mail `668` / calendar `1211`); list is `ls` (drive/lists/pages/sharepoint) vs `list` (mail/calendar/teams); `drive get`(download)/`cat`(content)/`info`(metadata) overlap confusingly; filesystem verbs spread onto non-file nouns (`lists ls`, `pages cat`) where undocumented. Downgrade-to-Friction condition (internally consistent + documented convention) not met CLI-wide. *Note: the `drive` subtree alone (ls/cat/cp/mv/rm, documented in `docs/plans/2025-12-26-onedrive-design.md`) would qualify for the Friction downgrade — the Blocker rests on the cross-noun split.* |
| 6.2 Flags follow conventions | pass | — | C | `--json` (not `--format=json`); no `--skip-*`/`--no-confirm` aliases (`--skip` is a pagination offset). Missing `--force` is a 4.2/1.3 gap, not a naming violation. |
| 6.3 Naming internally consistent across subcommands | fail | F | C | Same evidence as 6.1 at Friction severity: the verb-per-noun split (`rm`/`delete`, `ls`/`list`, `get`/`cat`/`info`). Output flags (`--json/--agent/--markdown/--top/--fields`) are consistent. |
| 6.4 Documented naming policy + mechanical (CI/lint) check | fail | T | Ft | Absence → FAIL@T. No vocabulary policy; no `.github/` (no CI); `Makefile:57` `lint` is golangci-lint (Go style only, not verbs). |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection (command/flag schema) | **fail** | **B** | Ft | **Original Blocker — not remediated.** `agent-guide` (`main.go:4322`, `agentGuideJSON()` `4394`) is a **hand-written contract** (output flags, pagination idiom, envelope, send-dedupe) — even as `--json` it does **not** enumerate the real command/flag tree, so per the detection rule it does not satisfy 7.1. |
| 7.2 Machine introspection is versioned | na | — | C | 7.1 fails; the guide carries no `schema_version` regardless. |
| 7.3 Long-form skill manifest teaches workflows | pass | — | Ft | Ships `.claude/skills/clearing-calendar-with-go365/SKILL.md`, a workflow-teaching manifest teaching an end-to-end go365 workflow. |
| 7.4 Introspection generated/validated against real impl | na | — | Ft | 7.1 fails — no machine command-tree to sync-check. |
| 7.5 `version` command reports build (version + commit/date) | pass | — | Ft | **NEW check.** `version` cmd (`main.go:4308-4319`) prints version/commit/buildDate, injected via `-ldflags` (`Makefile:13`) with a `debug.ReadBuildInfo` fallback (`main.go:51-57`). Root `--version` too (`108-116`). An agent can detect a stale binary. |

### P8. Async-aware execution — *entire principle N/A (synchronous Graph wrapper, no async API)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 `--wait` on async-submitting commands | na | — | Ft | No async/job-submitting command — synchronous Graph calls only. |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | No poll loop (8.1 absent). |
| 8.3 Persistent job ledger | na | — | Ft | No async jobs to record. |
| 8.4 `jobs list/get/prune` | na | — | Ft | No job ledger. |

### P9. Persistent identity through profiles — *auth (MSAL device-code) out of scope*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | pass | — | Ft | Non-auth config persists: `config set --sharepoint-site`/`--timezone` (`main.go:256-270`) → `~/.go365/config.json`, shown by `config show`. Covers the main recurring `--site`/timezone cluster. (Per-call `--user`/`--library`/`--shared` selectors are not persisted — minor gap.) |
| 9.2 Profile management subcommands | na | — | Ft | No named-profile system — a single global config bundle, not `save/use/list/delete` profiles. |
| 9.3 `--profile` root flag + precedence | na | — | C | No `--profile` flag / profiles (root registers only `--version`). |
| 9.4 Profiles surfaced in introspection | na | — | C | No profiles to surface. |
| 9.5 Stable, documented storage location | pass | — | C | `~/.go365/config.json`, 0700 dir / 0600 file, `libgo365/config.go:31-36`. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel exists | **fail** | **B** | Ft | **Original Blocker — not remediated.** No `feedback` command; grep for `feedback`/`jsonl` across the tree returns nothing. |
| 10.2 Feedback can POST upstream when configured | na | — | C | 10.1 fails — no feedback path. |
| 10.3 Artifact commands support `--deliver` | fail | F | Ft | Artifacts are produced (`drive get` downloads to a file, `main.go:2432`) but only via a bare `--output`/`-o` path (`3269`) — no scheme abstraction (file/webhook/stdout). Per rule, bare file sink = partial credit = fail@F. `drive cat`/`pages cat`/`lists cat`/`sharepoint get` stream to stdout only. |
| 10.4 File sinks atomic; unknown schemes refused | na | — | C | No `--deliver`. (Note: `drive get` writes non-atomically via `os.Create` + partial-cleanup, `main.go:2432,2440` — relevant if `--deliver` is added.) |
| 10.5 `--deliver` + `feedback` in introspection | na | — | C | Depends on 7.1 (fails) and on 10.1/10.3 surfaces that don't exist. |

## Runtime risks to confirm in a `validate` phase (static can't settle these)

1. **Pagination losslessness (5.2).** Does `--page-token`/`--skip` with a small `--top` on cursor lists (`mail list`, `drive ls`, `teams`) visit every item exactly once? Assert a `--page-token` page equals `items[k:2k]` of one larger read. Watch calendar's `$skip`-offset path especially.
2. **truncated/hasMore two-signal model (5.3).** Confirm an agent following the documented idiom never sees a `truncated:false`-beside-cursor lie, and that aggregation caps (`teams chat list`, `pages ls --folder`) set `truncated:true` only when data was actually cut.
3. **Response-parse fragility.** Feed real Graph responses to the `libgo365` structs; hunt for fields typed `string` that Graph may return as number/array (ids, dates, `@odata.count`) — the class that crashed cu's `comment add`.
4. **Secret-leak confirmation (2.7).** Static shows no token field reaches JSON; confirm at runtime that `status`, `config show`, `agent-guide --json`, and error paths never dump the MSAL access token/JWT.
5. **Enum pass-through (3.3).** `presence set` posts a raw value to Graph — confirm an invalid value yields a clean error, not a crash/opaque 400.
6. **Exit-code-on-failure bug (2.4).** `calendar respond` returns nil after printing "Failed to respond…" → exits 0 on total failure. Confirm and treat as a bug.
7. **Unguarded destructive ops (4.2).** Confirm (read-only, via `--help` — do NOT run against real data) that `drive rm` / `calendar delete` / `calendar cancel` execute with no `--force`.

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 4.2 (**B**) — add a required non-default guard (`--force`/`--yes`) to `drive rm`, `calendar cancel`, `calendar delete`, `drive unshare` (and gate `mail delete`'s soft path, or accept recoverable-by-default). (`main.go:2979,1196,1250,3215`)
- [ ] 6.1 (**B**) — alias canonical verbs (`delete` for `rm`, `list` for `ls`, `get`/`show` for `info`) so the destroy/list/metadata verb is uniform across nouns; keep filesystem aliases on `drive`. (`main.go` verb `Use:` fields)
- [ ] 2.2 (F) — register `--json` + a structured result on `calendar cancel`/`delete`/`respond`. (`main.go:1166,1221,1141`)
- [ ] 3.3 (F) — validate `presence set` against its enum and enumerate the valid set on rejection. (`main.go:4055`)
- [ ] 4.3 (F) — add `--dry-run` to consequential ops (send/delete/cancel/share). (grep: none today)
- [ ] 1.3 (F) — the `--force`/`--yes` added for 4.2 also clears this (destructive bypass flag).
- [ ] 6.3 (F) — resolved by the 6.1 verb-aliasing (internal naming consistency).

### Proposals — features, not auto-built (failing `feature` checks; require go-ahead)
- 7.1 (**B**) — add real machine introspection (`agent-context`/`--schema`) emitting the actual cobra command/flag tree as structured data (walk `rootCmd`), not the hand-written `agent-guide`.
- 10.1 (**B**) — add a `feedback <text>` command writing local JSONL (optionally POST upstream when configured — 10.2).
- 10.3 (F) — generalize `drive get --output` into a `--deliver` scheme abstraction (stdout/file/webhook) with atomic file writes + structured refusal of unknown schemes (10.4).
- 6.4 (T) — document a naming policy and add a CI/lint check enforcing the verb/flag vocabulary.
