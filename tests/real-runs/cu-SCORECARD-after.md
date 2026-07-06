# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/cu (branch `conformance-fixes`, post-remediation — FINAL)
**Date:** 2026-07-06
**Score:** 31 / 32 applicable checks (96.9%)
**Failing gaps:** 1 Blocker · 0 Friction · 0 Target
**Suspicious-N/A warning:** Two whole principles returned all-N/A — **P8 (async)** and **P9 (profiles)**. Both are legitimate: the CLI is a synchronous ClickUp REST wrapper with no async job API (no job ids / `status:queued` / poll loop), and the only recurring cross-command state is auth/workspace credentials already persisted in `~/.cu/config.json` (no forced re-specification of a non-auth config bundle). Flagged per template policy; neither indicates an evaluation gap.

Denominator excludes 13 N/A checks (1.5, 4.1, 5.4, 8.1–8.4, 9.1–9.5, 10.2). 31 pass + 1 fail = 32 applicable. The single remaining fail (10.1 feedback) is a deliberately declined non-goal, not an unaddressed defect.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | Only prompts are login email/password (login.go:47,56), both TTY-guarded; comment.go/docs.go `os.Stdin` reads are gated behind explicit `--stdin`. |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | `term.IsTerminal(int(syscall.Stdin))` guards both login prompts (login.go:47,56), erroring instead of prompting when not a TTY. |
| 1.3 Confirmation-bypass flag exists for destructive ops | pass | — | C | `--force` declared task.go:478, read+enforced task.go:425-428; `task delete` is the only destructive op. |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | — | C | Pass-by-absence: no menu/select libs (no survey/promptui/inquirer). |
| 1.5 Bypass convention consistent across subcommands | na | — | C | N/A: only one bypass flag (`--force`); nothing to be inconsistent with. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | Per-command `--json` + list envelope; e.g. task.go:190-192, listoutput.go:79-107. |
| 2.2 Every data-returning command supports `--json` | pass | — | C | All data handlers read `--json` and encode to stdout, incl. status/config get (main.go) and all list envelopes. |
| 2.3 One consistent flag name (`--json`) | pass | — | C | Only `--json` used; no `--format`/`-o json`. `attachment get -o/--output` is a download file-path, not a format selector. |
| 2.4 Exit codes: 0 success, non-zero failure | pass | — | C | main.go: error → stderr + `os.Exit(1)`; success → 0. No handler forces exit 0 on failure. |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | **Regression-checked clean after the 5.2 envelope change.** All list JSON goes to `os.Stdout` via `writeListJSONPaged(os.Stdout,…)` (task.go:191, comment.go:74, view.go:68, docs.go:61, inbox_comments.go:391); truncation hints (listoutput.go:57-62), inbox bulk-fetch warnings (inbox_comments.go:280), and top-level errors (main.go) all go to `os.Stderr`. The new `next_cursor` rides inside the stdout envelope only. |
| 2.6 ANSI/color suppressed when not a terminal | pass | — | C | Pass-by-absence: no color lib and no ANSI escapes; output is plain text/JSON, inherently pipe-safe. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message | pass | — | C | Wrapped `fmt.Errorf` → stderr (main.go); no `panic(` in cmd/ or libcu/. |
| 3.2 Input validated early, before side effects | pass | — | C | Flag/arg validation precedes the mutating call in every create/update/set/delete handler (task.go:345-373 before 382; task.go:293-311; field.go). |
| 3.3 Enum/choice rejections enumerate the valid set | pass | — | C | field.go lists valid drop_down/label options via `optionNames()`; deliver scheme (deliver.go) and priority (task.go:296) enumerate the allowed set. |
| 3.4 Errors include corrective guidance | pass | — | C | Corrective examples throughout: inbox_comments.go:110,115; task.go:120; comment.go; login.go. |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent | na | — | Ft | N/A: thin wrapper; no idempotency token/natural-key dedup on task/doc/page create — ClickUp create endpoints are upstream's responsibility. |
| 4.2 Destructive operations require an explicit, non-default flag | pass | — | C | `task delete` performs no `DeleteTask` unless `--force` set (task.go:425-428). Only destructive op. |
| 4.3 Consequential operations support `--dry-run` | pass | — | C | All mutating handlers call `isDryRun()`/`printDryRun()` and return before the `client.*` mutation (task create/update/delete at task.go:241-248 etc., comment add/reply, attachment add, field set, docs create, pages create/update). |
| 4.4 Mutation responses return the affected identifier(s) | pass | — | C | create/update/delete echo the id (task.go:325, comment.go, attachment.go, docs.go). Nit: `field set`/`pages update` print name/value only. |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default | **pass** | — | C | **Fixed and verified.** Every list defaults to a finite cap: `task list`/`comment list`/`view`/`docs list`/`attachment list`/`field list`/`docs pages list` all declare `-n 100` (task.go:456-ish, attachment.go:280, field.go:187, docs.go:418/428) and **`inbox comments` now defaults `-n 100`** (inbox_comments.go:97) with `--all` (line 98) and routes its JSON through the truncation envelope `writeListJSONPaged` (line 391) — the prior unbounded `-n 0` default and envelope-bypass are gone. The uncapped path is opt-in via `--all`/`-n 0`. |
| 5.2 List commands support filtering and pagination/cursor | **pass** | — | Ft | **Fixed and verified honored, not merely declared.** Five list commands expose `--cursor` and emit `next_cursor`: for each, the handler reads the flag (`cmd.Flags().GetString("cursor")`) and passes it to a single-page libcu primitive whose result feeds `writeListJSONPaged(..., nextCursor)`: `task list` (task.go:133→`ListTasksPage` @184→writer @191), `comment list` (comment.go:53→`GetCommentsPage` @66→74), `view` (view.go:47→`GetViewTasksPage` @60→68), `docs list` (docs.go:40→`SearchDocsPage` @53→61), `inbox comments` (inbox_comments.go:143→`SearchAssignedCommentsPage` @245→391). The primitives genuinely send the cursor to the API — `ListTasksPage`/`GetViewTasksPage` set `page=N` query param (tasks.go:323, views.go:96), `SearchDocsPage` appends `&cursor=` (docs.go:165), `SearchAssignedCommentsPage` puts `Cursor: token` in the request body (comments_search.go:181) — and return the API's `next_cursor` (tasks.go:342-345, comments_search.go:212-213). The envelope emits `next_cursor` only when non-empty (listoutput.go:21,101; omitempty). `attachment list`/`field list`/`docs pages list` correctly stay fetch-all with no `--cursor` (ClickUp doesn't paginate them). Filters coexist (task.go:126-129, inbox_comments.go:135-139). Confirmed by tests: `TestWriteListJSONPagedNextCursorPresent/OmittedWhenEmpty` (listoutput_test.go:107-141) and libcu page-primitive tests (docs_test.go, comments_search_test.go). |
| 5.3 Truncated output signals truncation and hints how to narrow | pass | — | C | `writeListJSONPaged` sets `truncated`+`hint` (listoutput.go:99-100); human path prints stderr hint (printTruncationHint, listoutput.go:57-62). `inbox comments` now shares this envelope (inbox_comments.go:391,444) — the prior residual is closed. |
| 5.4 MCP wrapper tool descriptions fit a token budget | na | — | C | N/A: no MCP wrapper in the CLI (only ClickUp API reference docs under docs/). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | — | C | Canonical verbs throughout (get/list/create/update/delete/add/set/reply/view). Only banned spelling `show` survives as a permitted non-canonical alias on `config get`. |
| 6.2 Flags follow conventions | pass | — | C | No `--skip-*`/`--format`/`--no-confirm`; bypass is `--force`, JSON is boolean `--json`, pagination is `--cursor`/`-n`/`--all`; all kebab-case. |
| 6.3 Naming internally consistent across subcommands | pass | — | C | Principled `add` vs `create` vs `set`, applied consistently and documented (docs/conventions/cli-naming.md). New `--cursor`/`--all`/`-n` cluster is uniform across all list commands. |
| 6.4 Documented naming policy + mechanical check enforces vocabulary | pass | — | Ft | Policy doc + `cu-namingcheck` (cmd/cu-namingcheck/main.go, `os.Exit(1)` on violation) + Makefile `namingcheck`/`check` wiring. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists | pass | — | Ft | `agent-context` walks the live cobra tree in-process and emits real commands/subcommands/flags as JSON (verified by running `/tmp/cu-final agent-context`: the new `--cursor` flags appear on `comment list`, `task list`, `docs list`, etc.). |
| 7.2 Machine introspection is versioned | pass | — | C | `schema_version: "1"` (agentcontext.go; confirmed in live output). |
| 7.3 Long-form skill manifest teaches workflows | pass | — | Ft | skills/cu/SKILL.md teaches auth, discovery, list/truncation envelope, mutations, fields/docs, conventions. |
| 7.4 Introspection generated/validated against the real implementation | pass | — | Ft | In-sync by construction (live-tree walk cannot drift); exercised in the Makefile `check` gate. |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | N/A: no async job submission; synchronous ClickUp REST, no command returns a job id / `status:queued`. |
| 8.2 The poll loop uses exponential backoff + jitter | na | — | C | N/A: no job-poll loop. The only backoff (libcu/client.go) is request-level 429 retry, not job polling. |
| 8.3 A persistent job ledger records jobs across invocations | na | — | Ft | N/A: no async jobs, no ledger. |
| 8.4 A `jobs` command exposes `list`/`get`/`prune` | na | — | Ft | N/A: no async subsystem; no `jobs` command. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | na | — | Ft | N/A: the only recurring cross-command state is auth/workspace (token, team_id, user_id) already persisted in ~/.cu/config.json and loaded automatically. Target IDs are per-operation, not config. |
| 9.2 Profile management subcommands exist | na | — | Ft | N/A: no profiles; configCmd has only set + get/show. |
| 9.3 `--profile` persistent root flag + precedence | na | — | C | N/A: no profiles; only persistent root flag is `--dry-run`. |
| 9.4 Profiles surfaced in machine introspection | na | — | C | N/A: no profiles. |
| 9.5 Stable, documented storage location | na | — | C | N/A: no profile storage; single config.json under ~/.cu/. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists (`feedback <text>` local JSONL) | **fail** | B | Ft | No `feedback` command (grep → 0 hits). **Deliberately declined non-goal for this branch's scope** — scored fail per rubric (FAIL@B by absence), but an accepted product decision, not a regression or oversight. |
| 10.2 Feedback can POST upstream when configured, discoverable | na | — | C | N/A: depends on 10.1, which does not exist. |
| 10.3 Artifact-producing commands support `--deliver` | pass | — | Ft | deliver.go implements a true scheme abstraction (stdout \| file:<path> \| webhook:<url>), wired to `attachment get`. `docs get` emits text/JSON to stdout only — not a downloadable byte artifact — so no coverage gap. |
| 10.4 File sinks write atomically; unknown schemes get a structured refusal | pass | — | C | `atomicWriteFile` uses `os.CreateTemp` + `os.Rename`; unknown/empty scheme → structured `deliverSchemeError` naming the supported set, before any network. |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | pass | — | C | `--deliver` is surfaced by the agent-context flag walk (confirmed in live output on `attachment get`); feedback absent (moot). |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- (none — all conformance checks pass)

### Friction (conformance, lower priority)
- (none — no failing conformance-Friction checks remain)

### Proposals — features, not auto-built (failing `feature` checks)
- **10.1 (Blocker, Ft) — feedback channel.** A `cu feedback <text>` command writing local JSONL (with optional gated upstream POST for 10.2). **Intentionally declined** on this branch; listed for completeness. Requires go-ahead.
