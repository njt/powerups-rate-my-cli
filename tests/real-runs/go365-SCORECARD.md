# CLI Agent-Nativeness Scorecard

**Target:** /Users/gnat/Source/go365
**Date:** 2026-07-05
**Score:** 22 / 35 applicable checks (63%)
**Failing gaps:** 4 Blocker · 7 Friction · 2 Target
**Suspicious-N/A warning:** P8 (Async-aware execution) is entirely N/A — go365 is a synchronous wrapper over the Microsoft Graph REST API and submits no async/long-running jobs, so all four P8 checks are legitimately N/A. No other whole principle is entirely N/A.

Framework: Cobra (`github.com/spf13/cobra`). Entry point `cmd/go365/main.go`; command handlers all in that one 6168-line file; the Graph client lives in `libgo365/`; shared output helpers in `internal/output/output.go`. go365 is a thin, synchronous wrapper over Microsoft Graph — auth/credentials are handled upstream (MSAL device-code flow, tokens in `~/.go365/`) and are out of scope for P9.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | Grep for `input(`/`Scanf`/`survey.`/`bufio.*ReadString`/`promptui`/`confirm` across `cmd/` and `libgo365/` returns no prompt calls; every command runs to completion non-interactively. Pass by absence (no prompts ⇒ non-interactive). |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | No prompts exist, so no TTY guard is needed. No `isatty`/`IsTerminal`/`os.Stdin` polling anywhere. Pass by absence. |
| 1.3 A confirmation-bypass flag exists for destructive ops | fail | F | C | Destructive commands act immediately with no confirmation *and* no bypass flag: `mail delete` (main.go:667), `calendar cancel` (main.go:1154), `calendar delete` (main.go:1210), `drive rm` (main.go:2960), `drive unshare` (main.go:3191). Since they never prompt (1.1 passes) they aren't blocked, but the rubric wants an explicit `--force`/`--yes` bypass convention on destructive ops; none exists. |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | — | C | No select/menu prompts exist. Pass by absence (no menus). |
| 1.5 Bypass convention is consistent across subcommands | na | — | C | No `--force`/`--yes` bypass flags exist at all (only `--force-new` for send-dedupe, a different concept). N/A (0–1 bypass flag). |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 The CLI supports structured (JSON) output | pass | — | C | `--json` wired on ~100 handlers; `output.WriteJSON` (output.go:311) encodes to stdout. e.g. `mailListCmd.Flags().Bool("json", ...)` main.go:724. |
| 2.2 Every data-returning command supports `--json` (coverage) | pass | — | C | `--json` declared on essentially every data command (mail/calendar/drive/teams/sharepoint/pages/lists list+get+action). `grep -c '"json"'` in main.go = 100. A concise `--agent` and `--fields` projection layer also exist (output.go:192, `writeListAgent` main.go:2013). |
| 2.3 One consistent flag name (`--json`, not mixed `--format`/`--output`) | pass | — | C | Structured output is uniformly `--json`; no `--format`/`-o json` alias. `drive get --output` (main.go:2384) is a *download-path* flag, not an output-format flag, so no collision. |
| 2.4 Exit codes: 0 success, non-zero failure | pass | — | C | `main()` returns `os.Exit(1)` on any `rootCmd.Execute()` error (main.go:6165-6166); handlers return errors rather than exiting 0. No taxonomy beyond 0/1 but the Absence FAIL@B condition (always 0 on failure) does not apply. |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | Data via `output.WriteJSON(os.Stdout, ...)` / `fmt.Printf`; warnings/notes/errors via `fmt.Fprintln(os.Stderr, ...)` (main.go:416, 595, 3812, 5381, 5637, 5795). Cobra errors go to stderr. |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | — | C | No color/ANSI library or escape codes anywhere (`grep -rn '\\033\|\\x1b\|color\|ansi'` over `cmd/` + `internal/` returns nothing). Pass by absence (no color to suppress). |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent, not a bare stack trace) | pass | — | C | Errors are wrapped `fmt.Errorf("failed to ...: %w", err)` throughout (e.g. main.go:690, 2434); `SilenceUsage: true` keeps output clean; no `panic` on the user path. |
| 3.2 Input validated early, before side effects | pass | — | C | `mail send` validates required `--subject`/`--to`/`--body` before calling `newAuthenticatedClient()` or `SendMail` (main.go:517-540, returns at :533-539 before network). Drive `--library requires --site` checked before any call (main.go:2105 etc.). |
| 3.3 Enum/choice rejections enumerate the valid set | pass | — | C | `RespondToEvent` rejects with "invalid response: %s (must be accept, decline, or tentative)" (libgo365/calendar.go:362); `--conflict must be fail, rename, or replace` (main.go:2765); `--type must be view or edit` (main.go:3025); `--scope must be anonymous or organization` (main.go:3030); `--role must be read or write` (main.go:3099). |
| 3.4 Errors include corrective guidance (valid invocation / example) | pass | — | C | Usage-style errors: "usage: calendar respond <event-id> <accept\|decline\|tentative>" (main.go:1130), "usage: calendar cancel ..." (main.go:1184), "client ID and tenant ID must be configured. Use 'go365 config set' to configure" (main.go:130). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent (idempotency token or natural key) | pass | — | Ft | Send commands (mail/teams chat/teams channel send+reply) accept `--idempotency-key` (24h TTL) and default to a content-hash soft-block (`addIdempotencyFlags` main.go:2597-2599; check logic main.go:2672-2702; libgo365/idempotency.go). A replay returns `SkipResponse` (output.go:352). Pure resource creates (`calendar create`) delegate creation to Graph upstream. |
| 4.2 Destructive operations require an explicit, non-default flag | fail | B | C | `mail delete` / `calendar cancel` / `calendar delete` / `drive rm` / `drive unshare` execute on the first positional arg with no `--force`/`--confirm`/non-default gate (main.go:667, 1154, 1210, 2960, 3191). `mail delete --permanent` gates only the *harder* delete; the default soft-delete still needs no confirmation. |
| 4.3 Consequential operations support `--dry-run` | fail | F | C | No `--dry-run`/`--dryRun` flag anywhere (`grep -rn 'dry-run\|dryRun\|DryRun'` returns nothing). Consequential ops (delete/cancel/send/move/upload/share) all execute directly. |
| 4.4 Mutation responses return the affected identifier(s) | pass | — | C | `mail send --json` returns `"id": message.ID` (main.go:651); `mail delete --json` returns `"id": messageID` (main.go:697); `calendar create` prints `ID: <created.ID>` (main.go:1641); `drive rm --json` returns `"target"` (main.go:2984). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default (limit/page size) | pass | — | C | `mail list` defaults to `DefaultMessageLimit = 100` (`$top=100`, libgo365/mail.go:14,153); `calendar list` defaults to a bounded 1-day window (main.go:802-823); client-side aggregations cap at `maxScan` (e.g. `aggregateChatsMaxScan = 5000` teams.go:446, `searchPagesMaxScan = 5000` pages.go:168). |
| 5.2 List commands support filtering and pagination/cursor | pass | — | Ft | Cursor pagination via `--page-token` + `nextPageToken`/`hasMore` envelope (output.go:37-47), plus `--top`, `--skip`, and server-side filters (`--from`/`--subject`/`--search` main.go:721-723; `--filter`-equivalents). |
| 5.3 Truncated output signals truncation and hints how to narrow | pass | — | C | `ListResponse.Truncated` flag (output.go:42-46) set when a scan cap is hit, with a stderr hint to narrow: "chat list stopped at the scan cap; results may be incomplete" (main.go:3812), "folder filter stopped at the scan cap" (main.go:4845); `agent-guide` documents narrowing on `truncated` (main.go:4374). |
| 5.4 MCP wrapper: each tool description fits a small audited token budget | na | — | C | No MCP server/wrapper exists (`grep -rni 'mcp'` over source returns nothing). N/A (no MCP wrapper). |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions (`get` not `info`, `list` not `ls`) | fail | B | C | **Split under the new idiom rule.** (a) **Friction bucket** — the `drive` subcommand exposes a coherent, internally-consistent filesystem verb set `ls/cat/cp/mv/rm` (main.go:2142/2320/2874/2924/2960), which the rubric names as an explicit downgrade case → these are **Friction** (fix: add `list`/`copy`/`move`/`delete` aliases), not Blockers. (b) **Blocker bucket (drives the overall severity)** — generic `info` used as `get` on `teams info` (3403), `drive info` (2234), `lists info` (4598), `pages info` (4879), and generic `ls` used as `list` on `pages ls` (4778), `lists ls` (4529), `sharepoint ls` (5864) are **not** a documented convention and are internally *inconsistent* (mail/calendar use `get`/`list` for the same read; see 6.3). Docs only say "same calling conventions as m365" (README.md:10) — a compatibility note, not a naming policy. So the generic `info`/`ls` stay **Blocker**. Overall verdict fail; overall Sev **B** driven by the generic `info`/`ls`. |
| 6.2 Flags follow conventions (`--force` not `--skip-confirmations`, `--json` not `--format=json`) | pass | — | C | Flag names are conventional: `--json`, `--top`, `--page-token`, `--fields`. No `--skip-*`/`--no-confirm`/`--format=json` aliases (`grep '"skip-'` finds only `--skip` as an offset flag, not a confirmation-skip). |
| 6.3 Naming is internally consistent across subcommands | fail | F | C | Verb drift *within* the CLI: mail/calendar use `get`/`list`/`delete`/`create`, but drive/teams/lists/pages use `info`/`ls`/`rm`/`cat`. Same read operation is `get` in one namespace and `info`+`cat` in another (`calendar get` vs `drive info`+`drive cat`). |
| 6.4 Documented naming policy + mechanical check (CI/lint) enforces vocabulary | fail | T | Ft | No documented naming policy and no CI/lint vocabulary check (`grep -ni 'naming\|convention\|lint'` in README/CLAUDE/IMPLEMENTATION finds only "calling conventions … as m365", a compatibility note, not an enforced policy). FAIL@T per Absence. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists (command/flag schema) | fail | B | Ft | `agent-guide --json` (main.go:4322-4442, `agentGuideJSON` at 4394) emits a structured *output-contract* (flags list, pagination idiom, JSON envelope, dedupe semantics) — but it is a hand-written prose contract, NOT an `agent-context`/`--schema`/`dump-schema` command that enumerates the actual command tree with per-command flags and types. The rubric's Blocker is specifically a machine-readable command/flag *schema*; that surface does not exist. FAIL@B. |
| 7.2 The machine introspection is versioned (`schema_version`) | na | — | C | `agentGuideJSON` carries no `schema_version` and 7.1's schema surface is absent. N/A (7.1 fails). |
| 7.3 A long-form skill manifest (`SKILL.md`-style) teaches workflows | pass | — | Ft | A shipped skill manifest exists: `.claude/skills/clearing-calendar-with-go365/SKILL.md` teaches a multi-step calendar-clearing workflow driving go365; plus `agent-guide` and an extensive `CLAUDE.md` "Agent-Friendly Output Flags" section. |
| 7.4 Introspection generated/validated against the real implementation | fail | T | Ft | `agentGuideText`/`agentGuideJSON` are hand-maintained constants (main.go:4342, 4394) kept "consistent with CLAUDE.md" by comment only; no codegen or test asserts they match the real cobra command/flag tree. FAIL@T (no generation/validation binding). |

### P8. Async-aware execution — *entire principle N/A (go365 wraps no async API)*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | No command returns a job id / `status: queued`; every Graph call is synchronous request→response. N/A (no async API). |
| 8.2 The poll loop uses exponential backoff + jitter | na | — | C | No poll loop exists (`grep -ni 'poll\|backoff\|jitter\|queued'` returns nothing). N/A. |
| 8.3 A persistent job ledger records jobs across invocations | na | — | Ft | No job ledger; the only persistent store is the idempotency cache (`~/.go365/`, idempotency_lock.go), not a job ledger. N/A. |
| 8.4 A `jobs` command exposes `list`/`get`/`prune` | na | — | Ft | No `jobs` command. N/A. |

### P9. Persistent identity through profiles — *non-auth config bundle*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 If commands force re-specifying a recurring non-auth config bundle, the CLI can persist & reuse it | pass | — | Ft | A recurring non-auth cluster exists — `--site`/`--library` across ~15 drive commands (main.go:3243-3345) and sharepoint (5771, 5880), plus timezone — and it IS persistable: `config set --sharepoint-site` and `--timezone` are stored in `~/.go365/config.json` (config.go:31-37) and used as defaults (`siteName = config.SharePointSite` main.go:5771/5880; timezone fallback main.go:1760, 1885). So the recurring bundle is not force-re-specified; it has a single persisted config. (It's a single global config, not a named multi-profile system — see 9.2.) |
| 9.2 Profile management subcommands exist (`save`/`use`/`list`/`show`/`delete`) | fail | F | Ft | Only `config set` / `config show` exist (main.go:244, 281) — one global config, no *named* profiles and no `save`/`use`/`list`/`delete` over multiple profiles. An agent juggling several tenants/sites cannot name and switch between saved bundles. |
| 9.3 `--profile` is a persistent root flag; precedence flag > env > profile > default | fail | F | C | No `--profile` root flag; config is a single file with no per-invocation selection and no documented flag>env>profile>default precedence chain. |
| 9.4 Profiles surfaced in machine introspection (`agent-context`) | na | — | C | No profile system (9.2 fails) and no machine command/flag introspection (7.1 fails). N/A. |
| 9.5 Stable, documented storage location (`~/.<cli>/`) | pass | — | C | Config stored at a stable `~/.go365/config.json` (config.go:31-37), documented in README.md:187 and IMPLEMENTATION.md:32. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists (`feedback <text>` recorded locally) | fail | B | Ft | No `feedback` command (`grep -ni 'feedback'` in main.go finds nothing; matches are only in `docs/.spacedock-state` workflow files). FAIL@B. |
| 10.2 Feedback can POST upstream when configured, and that's discoverable | na | — | C | No feedback channel exists (10.1 fails). N/A. |
| 10.3 Artifact-producing commands support `--deliver` (stdout/file/webhook) | fail | F | Ft | `drive get` produces a file artifact and offers `--output <path>` (main.go:2384) — a file sink only, not the `--deliver` abstraction with stdout/file/webhook schemes. No webhook or stdout-delivery option; other artifact commands (`drive cat`, `pages cat`) only stream to stdout. |
| 10.4 File sinks write atomically; unknown schemes get a structured refusal | fail | F | C | `drive get` writes directly to `os.Create(outputPath)` and only `os.Remove`s on download error (main.go:2432-2442) — not a temp-file + atomic rename; a crash mid-download leaves a truncated file at the final path. No scheme handling (no `--deliver`), so no structured refusal for unknown schemes. |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | na | — | C | Neither `--deliver` nor `feedback` exists, and 7.1's schema surface is absent. N/A (depends on 7.1). |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 4.2 (B) — Add a `--force`/`--yes` gate to `mail delete` (main.go:667), `calendar cancel` (1154), `calendar delete` (1210), `drive rm` (2960), `drive unshare` (3191): require the flag (or non-TTY headless bypass) before the destructive Graph call. Pairs with 1.3.
- [ ] 6.1 (B) — Rename off-convention verbs, keeping the current names as aliases: add `get` alias for `info` (teams/drive/lists/pages), `list` alias for `ls`, `delete` alias for `rm`, `copy`/`move` for `cp`/`mv`. Cobra `Aliases:` keeps back-compat while making the canonical verb conventional.
- [ ] 1.3 (F) — Same edit as 4.2: introduce one bypass flag name (`--force`) consistently across all destructive commands.
- [ ] 4.3 (F) — Add `--dry-run` to consequential handlers (delete/cancel/move/upload/share/send); print the intended action + affected id and return before the mutating call.
- [ ] 6.3 (F) — After 6.1, converge read verbs so the same operation has one name everywhere (`get` for single-object read; keep `cat` only as a raw-content alias if desired).
- [ ] 9.3 (F) — Add a `--profile` persistent root flag and document flag > env > profile > default precedence (depends on 9.2 landing).
- [ ] 10.4 (F) — Make `drive get` write atomically: download to a temp file in the destination dir, then `os.Rename` into place; on any error remove the temp file (main.go:2432-2442).

### Friction (conformance, lower priority)
- [ ] 7.2 — Once a real schema surface exists (7.1), stamp it with `schema_version`.
- [ ] 9.4 / 10.5 — Once profiles / `--deliver` / `feedback` exist and a schema command exists, surface them there.

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (B) — Add an `agent-context`/`--schema` command that walks the live cobra tree and emits every command + flag (name, type, default, required, help) as JSON. Highest-leverage gap: today an agent must read `agent-guide` prose or the repo. Requires your go-ahead.
- 10.1 (B) — Add a `feedback <text>` command appending JSONL to `~/.go365/feedback.jsonl` (with optional upstream POST for 10.2). Requires your go-ahead.
- 7.4 (T) — Generate/validate `agent-guide` (and any new schema) from the real command tree, or add a test asserting they stay in sync. Requires your go-ahead.
- 6.4 (T) — Document a naming policy and add a CI/lint check that rejects banned verbs/flags on new commands. Requires your go-ahead.
- 9.2 (F) — Add a named-profile subsystem (`config profile save/use/list/show/delete`) over `~/.go365/`, generalizing the single config into named bundles (tenant + site + timezone). Requires your go-ahead.
- 10.3 (F) — Generalize `drive get --output` into a `--deliver` abstraction (stdout/file/webhook) across artifact commands. Requires your go-ahead.
