# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/go365 (Go / cobra Microsoft-365 CLI; handlers in `cmd/go365/main.go`, Graph client in `libgo365/`)
**Branch:** `agent-native-conformance` (post-remediation)
**Date:** 2026-07-07
**Rubric:** current hardened 47-check rubric (adds 2.7, 7.5; sharpened 2.2 / 5.2 / 5.3; "static ≠ runtime" methodology)
**Mode:** assess (static, read-only — `go build` + `--help` only; no Microsoft Graph operation run)
**Score:** 33 / 36 applicable checks (92%)
**Failing gaps:** 1 Blocker · 1 Friction · 1 Target
**Delta vs prior assess (22 / 33, 4B·6F·1T):** now **33 / 36 (92%)**, +25pp. Seven conformance checks flipped fail→pass (4.2, 6.1 Blockers; 1.3, 2.2, 3.3, 4.3, 6.3 Friction) plus 1.5 and the `calendar respond` exit-0 fix; then the **`agent-context`** command (v0.4.0) cleared **7.1** (Blocker) and flipped **7.2** + **7.4** N/A→pass. **All conformance gaps closed, plus real machine introspection.** Remaining: **10.1** (feedback, the last Blocker), **10.3** (`--deliver`), **6.4** (naming CI) — all *feature* proposals. Build + `--help` verified working.

> ⚠️ **Whole-principle N/A:** P8 (Async-aware execution) is entirely N/A — go365 is a synchronous Graph wrapper with no async/job-submitting command (P8's own documented escape clause). No other principle is wholly N/A.

## What the remediation fixed (verified against current branch)

| Claim | Verdict | Evidence |
|-------|---------|----------|
| calendar respond exits non-zero on failure | **cleared** | `main.go:1196-1198` returns `fmt.Errorf("%d of %d responses failed", …)` when `failures>0` (was `return nil`). Resolves the 2.4 caveat. |
| `--json` on calendar respond/cancel/delete (2.2) | **cleared** | flags at `1821`, `1827`, `1834`; handlers `WriteJSON` a `{results,failures}` envelope (`1188-1195`, `1280-1287`, and delete's equivalent). |
| `--force` + `--dry-run` on destructive/consequential ops (4.2/1.3/4.3) | **cleared** | all 5 destructive ops guard `--force` before the mutating call; `--dry-run` now covers all 19 consequential ops (5 destructive + 14 more). |
| canonical verbs + back-compat aliases (6.1/6.3) | **cleared** | drive `rm`+alias `delete` (`3089-3090`), drive `ls`+alias `list` (`2270-2271`); teams/lists/pages `get`+alias `info` (`3572-3573`,`4782-4783`,`5065-5066`); lists/pages/sharepoint `list`+alias `ls` (`4712-4713`,`4963-4964`,`6051-6052`). |
| presence set validates the enum (3.3) | **cleared** | `main.go:4212-4222` validates against `{Available,Busy,DoNotDisturb,Away,Offline}` and enumerates the set on rejection, before any side effect. |

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | Pass by absence: no `bufio.NewReader(os.Stdin)`/`Scanf`/`survey.`/`confirm` in any handler. CLI never blocks on input. |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | Pass by absence: no prompts exist; nothing to guard. |
| 1.3 Confirmation-bypass flag exists for destructive ops | **pass** | F | C | **Flipped (was fail).** `--force` now registered and required on all destructive ops: mail delete `770`, calendar cancel `1828`, calendar delete `1835`, drive rm `3479`, drive unshare `3515`. |
| 1.4 Interactive menus have a flag/file equivalent | pass | — | C | Pass by absence: no select/menu prompts. |
| 1.5 Bypass convention consistent across subcommands | **pass** | F | C | **Now applicable (was N/A).** The destructive-confirmation bypass is uniformly `--force` across all 5 ops; `--force-new` is a distinct send-dedupe override, not a confirmation bypass. One name for one concept ⇒ consistent. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | Per-command `--json` across the CLI; `internal/output/output.go` WriteJSON / ListResponse envelope. |
| 2.2 Every data-returning command supports `--json` (coverage incl. mutations) | **pass** | F | C | **Flipped (was fail).** All three previously-missing calendar mutations now emit JSON (`1821/1827/1834`). Every mutation now covered: mail send/move/delete (`758/764/769`), calendar respond/cancel/delete/create (`1821/1827/1834/1874`), drive upload/mkdir/cp/mv/rm/share/invite/unshare (`3444…3510`), teams channel send/reply, chat send, presence set (`4444/4446/4462/4467`). Only `drive get` (downloads to file) and `drive cat` (streams raw content) lack `--json` — raw-content sinks, not structured-data gaps. |
| 2.3 One consistent flag name | pass | — | C | Always `--json` (bool). No `--format`/`-o json`. |
| 2.4 Exit codes: 0 success / non-zero failure | pass | — | C | `RunE` returns wrapped errors; `main()` `os.Exit(1)` on non-nil. **Prior caveat resolved:** calendar respond/cancel/delete now `return fmt.Errorf(...)` on any failure (`1196`, `1288`, delete equiv) rather than exiting 0. |
| 2.5 Data → stdout, diagnostics → stderr | pass | — | C | Data via `output.WriteJSON(os.Stdout,…)`/`fmt.Print`; warnings/notes to `os.Stderr`. **Minor smell (pre-existing, unchanged):** per-item `fmt.Printf("Failed to …")` in cancel/delete/respond prints to stdout in the non-JSON path, though the aggregate error still returns via cobra to stderr. Not a regression; kept pass. |
| 2.6 ANSI/color suppressed off-terminal | pass | — | C | Pass by absence: no color library / ANSI escapes. |
| 2.7 Structured output never emits raw secrets | pass | — | C | No secret-bearing field reaches a JSON encoder: `Config` holds only tenant/client IDs, scopes, timezone, site — no token field. MSAL tokens live in the `~/.go365` cache, never serialized. (Confirm live in validate.) |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message | pass | — | C | Uniform `fmt.Errorf("…: %w", err)` via cobra `RunE`; `SilenceUsage:true`; no `panic` in handlers. |
| 3.2 Input validated before side effects | pass | — | C | `mail send` validates subject/to/body before send; `drive share` validates `--type`/`--scope`; `presence set` validates the enum (`4212-4222`) before the Graph call. |
| 3.3 Enum/choice rejections enumerate the valid set | **pass** | F | C | **Flipped (was fail).** `presence set` now validates the arg and returns `invalid availability %q (must be one of: Available, Busy, DoNotDisturb, Away, Offline)` (`4221`). calendar respond and drive share already enumerated. |
| 3.4 Errors include corrective guidance | pass | — | C | Usage examples in errors: respond/cancel usage strings, `--type is required (view or edit)`, `--force-new` hint. |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations idempotent | pass | — | Ft | `libgo365/idempotency.go`: persisted store, `--idempotency-key` 24h TTL + auto content-hash soft-block; wired on send/create commands. |
| 4.2 Destructive ops require an explicit non-default flag | **pass** | **B** | C | **Blocker cleared (was fail).** Every destructive op guards `--force` *before* the mutating call: mail delete `--permanent` path → `697-701` (force gate precedes `PermanentDeleteMessage`); calendar cancel `1259-1267` (precedes `CancelEvent`); calendar delete `1349-1357` (precedes `DeleteEvent`); drive rm `3121-3126` (precedes `DeleteItem`); drive unshare `3375-3380` (precedes `DeletePermission`). Refusal message: `refusing to … without --force`. mail's plain (soft/recoverable) delete stays unguarded by design — only the permanent path is destructive. |
| 4.3 Consequential ops support `--dry-run` | pass | | C | All 19 mutating commands carry `--dry-run` (5 destructive + 14: mail send/move, calendar create/respond, drive upload/mkdir/cp/mv/share/invite, teams channel send/reply, chat send, presence set) — short-circuits before the Graph call, respecting `--json`. |
| 4.4 Mutation responses return the affected id | pass | — | C | Ids returned: mail delete `{id}`, drive unshare `{permissionId}`, calendar create object; cancel/delete/respond now return a `results` array carrying each event id. `mail send` lacks an id (upstream Graph `/sendMail` limitation). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | pass | — | C | Bounded by Graph server-side paging + `nextPageToken`; `mail list` adds explicit cap `DefaultMessageLimit=100`. |
| 5.2 List commands support filtering + pagination/cursor | pass | — | Ft | `--page-token` cursor + `--skip` offset + `--from/--subject/--search` filters. **Runtime risk:** losslessness not statically provable — flag for validate. |
| 5.3 Truncated output signals truncation + consistency | pass | — | C | `ListResponse.Truncated` (`omitempty`) set only on client-side aggregation caps with stderr narrowing hints; never emitted `false`-beside-cursor. **Runtime risk:** two completeness signals by command type — confirm in validate. |
| 5.4 MCP wrapper tool-description budget | na | — | C | No MCP server / tool-description surface exists. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | **pass** | **B** | C | **Blocker cleared (was fail).** The cross-noun split that made it a Blocker is resolved: canonical `list`/`get`/`delete` are now reachable on every noun as primary or alias — lists/pages/sharepoint expose `list` primary (alias `ls`) and `get` primary (alias `info`); teams `get` (alias `info`); drive `rm` carries alias `delete`, drive `ls` carries alias `list`. The only remaining non-canonical *primaries* (`drive ls/cat/cp/mv/rm/info`) are confined to the drive filesystem subtree — a coherent, documented convention (`docs/plans/2025-12-26-onedrive-design.md`) that the rubric's own idiom rule classifies as at most a Friction, not a Blocker. Residual `drive get`(download)/`cat`(content)/`info`(metadata) is an internal drive-idiom nuance, not a cross-noun Blocker. |
| 6.2 Flags follow conventions | pass | — | C | `--force`/`--dry-run`/`--json` all canonical; no `--skip-*`/`--no-confirm`/`--format=json`. |
| 6.3 Naming internally consistent across subcommands | **pass** | F | C | **Flipped (was fail).** With canonical verbs uniformly available across nouns (primary-or-alias), an agent can use one vocabulary (`list`/`get`/`delete`) everywhere. Remaining primary-name variation is the intentional, self-consistent drive filesystem idiom. Output flags (`--json/--agent/--markdown/--top/--fields`) already consistent. |
| 6.4 Documented naming policy + mechanical (CI/lint) check | fail | T | Ft | Absence → FAIL@T. No vocabulary policy; no `.github/` CI; `Makefile` `lint` is golangci-lint (Go style only). Feature proposal. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection (command/flag schema) | pass | | Ft | `go365 agent-context` (`cmd/go365/agentcontext.go`) walks the live cobra tree and emits the real command/flag schema as JSON (`schema_version` 1), zero-setup, no Graph. Matches cu's `agent-context`. The prose `agent-guide` remains as a separate contract. |
| 7.2 Machine introspection is versioned | pass | | C | `agent-context` carries `"schema_version":"1"`. |
| 7.3 Long-form skill manifest teaches workflows | pass | — | Ft | Ships `.claude/skills/clearing-calendar-with-go365/SKILL.md`, a workflow-teaching manifest. |
| 7.4 Introspection generated/validated against real impl | pass | | Ft | `agent-context` is generated from the live cobra tree at runtime — in-sync by construction (cannot drift from the real commands). |
| 7.5 `version` command reports build (version + commit/date) | pass | — | Ft | `version` cmd (`4491`) prints version/commit/buildDate via `-ldflags` with `debug.ReadBuildInfo` fallback; root `--version` too. |

### P8. Async-aware execution — *entire principle N/A (synchronous Graph wrapper, no async API)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 `--wait` on async-submitting commands | na | — | Ft | No async/job-submitting command. |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | No poll loop. |
| 8.3 Persistent job ledger | na | — | Ft | No async jobs to record. |
| 8.4 `jobs list/get/prune` | na | — | Ft | No job ledger. |

### P9. Persistent identity through profiles — *auth (MSAL device-code) out of scope*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | pass | — | Ft | `config set --sharepoint-site`/`--timezone` → `~/.go365/config.json`, shown by `config show`. Covers the main recurring `--site`/timezone cluster. |
| 9.2 Profile management subcommands | na | — | Ft | Single global config bundle, no named profiles. |
| 9.3 `--profile` root flag + precedence | na | — | C | No `--profile` / profiles. |
| 9.4 Profiles surfaced in introspection | na | — | C | No profiles to surface. |
| 9.5 Stable, documented storage location | pass | — | C | `~/.go365/config.json`, 0700 dir / 0600 file. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel exists | **fail** | **B** | Ft | **Declined non-goal** (owner's call, same as cu): a feedback channel needs an upstream receiver to be worth building. No `feedback` command exists. Scored fail@B for completeness, but intentionally not pursued. |
| 10.2 Feedback can POST upstream when configured | na | — | C | 10.1 fails. |
| 10.3 Artifact commands support `--deliver` | fail | F | Ft | Artifacts produced (`drive get` downloads to file) via bare `--output`/`-o` path only — no scheme abstraction (file/webhook/stdout). Partial credit ⇒ fail@F. Feature proposal. |
| 10.4 File sinks atomic; unknown schemes refused | na | — | C | No `--deliver`. |
| 10.5 `--deliver` + `feedback` in introspection | na | — | C | Depends on 7.1 (fails) and on surfaces that don't exist. |

## Regression sweep (did any edit break another check?)

- **Build + `--help`:** `go build ./...` exits 0; `/tmp/go365bin --help` and per-command `--help` render; aliases surface (`rm, delete`). No breakage.
- **2.4 exit codes:** improved, not broken — respond/cancel/delete now return non-zero on failure (prior caveat resolved).
- **2.5 stdout/stderr:** the new `--json` paths write `output.WriteJSON(os.Stdout,…)`; dry-run notices are stdout; force-refusals return errors (cobra → stderr). No new violation. The per-item `Failed to …` on stdout in the non-JSON path is a pre-existing smell carried into cancel/delete, not a new one.
- **6.2 flag conventions:** the added `--force`/`--dry-run` are canonical names; no `--skip-*`/`--no-confirm` introduced.
- **Aliases:** cobra aliases (`delete`←rm, `list`←ls, `info`←get) compile without collision (drive's `delete` alias and mail's `delete` primary are under different parents). No conflict.

## Score reconciliation

33 pass / 36 applicable. Fails (3): **6.4** (T, feature), **10.1** (B, feature), **10.3** (F, feature). N/A (11): 5.4, 8.1–8.4, 9.2–9.4, 10.2, 10.4, 10.5. Header roll-up (1B·1F·1T) matches the body verdicts above. **All conformance gaps closed, plus 7.1/7.2/7.4 via `agent-context`; only feedback (10.1), `--deliver` (10.3), and naming-CI (6.4) remain.**

## What remains

**Conformance (auto-fixable) still open — just one:**
- 4.3 (F) — DONE: `--dry-run` now on all 19 consequential ops.

**Pure feature proposals (require go-ahead; Kind=Ft):**
- 7.1 (B) — real machine introspection (`agent-context`/`--schema`) walking the cobra command/flag tree, not the hand-written `agent-guide`.
- 10.1 (B) — a `feedback <text>` command writing local JSONL (optional upstream POST → 10.2).
- 10.3 (F) — generalize `drive get --output` into a `--deliver` scheme abstraction (stdout/file/webhook) + atomic writes + structured refusal (10.4).
- 6.4 (T) — document a naming policy and add a CI/lint check enforcing the verb/flag vocabulary.

## Runtime risks to confirm in a `validate` phase (static can't settle these)

1. **Pagination losslessness (5.2).** Does `--page-token`/`--skip` with a small `--top` visit every item exactly once? Watch calendar's `$skip`-offset path.
2. **truncated/hasMore two-signal model (5.3).** Confirm no `truncated:false`-beside-cursor lie and that aggregation caps set `truncated:true` only when data was cut.
3. **Response-parse fragility.** Feed real Graph responses to the `libgo365` structs; hunt for `string`-typed fields Graph may return as number/array.
4. **Secret-leak confirmation (2.7).** Confirm `status`, `config show`, `agent-guide --json`, and error paths never dump the MSAL access token/JWT.
5. **Enum pass-through (3.3).** `presence set` now rejects invalid values statically; confirm the Graph call path is unreachable for a bad value.
6. **Destructive-op guards (4.2).** Confirm via `--help` (do NOT run against real data) that `drive rm`/`drive unshare`/`calendar cancel`/`calendar delete`/`mail delete --permanent` all refuse without `--force` — statically verified here; validate the runtime refusal.
