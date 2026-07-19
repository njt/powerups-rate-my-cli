# CLI Agent-Nativeness Scorecard

**Target:** tests/fixtures/helptrapcli/helptrapcli.py
**Date:** 2026-07-19
**Score:** 25 / 31 applicable checks (81%)
**Failing gaps:** 3 Blocker · 1 Friction · 2 Target
> ⚠️ Suspicious N/A: principles **P8** (async-aware execution) and **P9** (profiles) returned entirely N/A. Confirm the CLI genuinely wraps no async API and has no recurring non-auth config bundle.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | pass | — | C | No `input(`/`click.confirm`/`prompt(`/`Scanf` etc. anywhere; CLI is non-interactive by absence. |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | No prompts exist to guard; pass by absence. |
| 1.3 Confirmation-bypass flag exists for destructive ops | pass | — | C | `delete` defines `--force` and refuses without it (helptrapcli.py:21-22, :40). |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | — | C | No select/menu prompts; pass by absence. |
| 1.5 Bypass convention consistent across subcommands | na | — | C | Only one bypass flag (`--force`); 0–1 bypass flag ⇒ N/A. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | — | C | `--json` flag on every command; all output via `json.dumps` (helptrapcli.py:8,11-12,18,24-25). |
| 2.2 Every data-returning command supports `--json` (coverage) | pass | — | C | get/list/create/delete all declare `--json` (helptrapcli.py:34,36,38,40). |
| 2.3 One consistent flag name | pass | — | C | Only `--json`; no `--format`/`--output`/`-o json` present. |
| 2.4 Exit codes: 0 success, non-zero failure, stable taxonomy | pass | — | C | `sys.exit(4)` enum reject, `sys.exit(3)` missing force, `sys.exit(2)` unknown command; 0 on success (helptrapcli.py:17,22,31). |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | Data via `print(json.dumps(...))`; errors via `file=sys.stderr` (helptrapcli.py:16,21,30). |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | — | C | No color libs / ANSI escapes used; nothing to suppress. |
| 2.7 Structured output never emits raw secrets (tokens/JWTs/passwords) | pass | — | C | JSON payloads carry only `id`/`visibility`/`posts`/`truncated`/`hint`/`existing`/`deleted`/`would_delete` (helptrapcli.py:8,12,18,24-25); no `*token*`/`*jwt*`/`*secret*`/`*password*`/`*key*` field reaches `json.dumps`. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (no bare stack trace) | pass | — | C | Explicit error strings on stderr; no bare traceback/panic (helptrapcli.py:16,21,30). |
| 3.2 Input validated early, before side effects | pass | — | C | `create` validates `--visibility` and `delete` checks `--force` before emitting any result (helptrapcli.py:15-17,21-22). |
| 3.3 Enum/choice rejections enumerate the valid set | pass | — | C | `must be one of: {', '.join(VIS)} (got: ...)` (helptrapcli.py:16). |
| 3.4 Errors include corrective guidance | pass | — | C | Unknown-command error names the valid commands (helptrapcli.py:30); "refusing to delete without --force" (helptrapcli.py:21). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent | pass | — | Ft | `create` returns `{"existing": False}`, signalling natural-key idempotency semantics (helptrapcli.py:18). |
| 4.2 Destructive operations require an explicit, non-default flag | pass | — | C | `delete` requires `--force` (default off) before acting (helptrapcli.py:21-22,40). |
| 4.3 Consequential operations support `--dry-run` | pass | — | C | `delete` honors `--dry-run`, returns `status: dry_run` (helptrapcli.py:23-24,40). |
| 4.4 Mutation responses return the affected identifier(s) | pass | — | C | create returns `id`; delete returns `deleted: <id>` / `would_delete: <id>` (helptrapcli.py:18,24-25). |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default | pass | — | C | `list` `--limit` default=20 (helptrapcli.py:36). |
| 5.2 List commands support filtering and pagination/cursor | pass | — | Ft | `list` accepts `--cursor` plus `--limit` (helptrapcli.py:36). |
| 5.3 Truncated output signals truncation + narrowing hint | pass | — | C | `{"truncated": True, "hint": "use --limit / --cursor"}` (helptrapcli.py:12). |
| 5.4 MCP wrapper tool descriptions fit token budget | na | — | C | No MCP server/tool-description surface exists ⇒ N/A. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | — | C | Commands are get/list/create/delete — all conventional (helptrapcli.py:29). |
| 6.2 Flags follow conventions | pass | — | C | `--force`/`--json`/`--dry-run`/`--limit`/`--cursor`/`--visibility`; no `--skip-*`/`--format=json`/`--no-confirm`. |
| 6.3 Naming is internally consistent across subcommands | pass | — | C | `--json` uniform across all subcommands; no internal drift. |
| 6.4 Documented naming policy + mechanical (CI/lint) check | fail | T | Ft | No documented naming policy and no CI/lint vocabulary check; absence ⇒ FAIL@T. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists (`agent-context`-style schema) | fail | B | Ft | No `agent-context`/`--schema`/`dump-schema` emitting command/flag JSON; absence ⇒ FAIL@B. |
| 7.2 Machine introspection is versioned (`schema_version`) | na | — | C | 7.1 fails (no introspection surface) ⇒ N/A. |
| 7.3 Long-form skill manifest (`SKILL.md`-style) teaches workflows | fail | T | Ft | No `SKILL.md`/skills dir for the target CLI; absence ⇒ FAIL@T. |
| 7.4 Introspection generated/validated against implementation | na | — | Ft | 7.1 fails (no introspection) ⇒ N/A. |
| 7.5 A `version` command reports the build (version + commit/date) | fail | F | Ft | No `version` command / `--version` surface; only `get`/`list`/`create`/`delete` are dispatched (helptrapcli.py:29) ⇒ absent ⇒ FAIL@F. |
| 7.6 `--help`/`-h` at every level prints usage, exits 0, never executes the action | fail | B | C | Root dispatch never checks `-h`/`--help` — `--help` falls into the unknown-command branch (exit 2, no usage; helptrapcli.py:28-31). Subcommand parsers set `add_help=False` and parse via `parse_known_args` (helptrapcli.py:32,41), so `--help` is discarded into extras and the handler executes: `delete X --force --help` deletes. Named argparse suppression tells present; catastrophic never-executes violation. |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | No async API — no job id / `status: queued` returned anywhere ⇒ N/A. |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | No poll loop / no async API ⇒ N/A. |
| 8.3 Persistent job ledger records jobs across invocations | na | — | Ft | No job ledger written ⇒ N/A. |
| 8.4 `jobs` command exposes `list`/`get`/`prune` | na | — | Ft | No `jobs` command / no async API ⇒ N/A. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | na | — | Ft | No recurring non-auth flag cluster across commands (`--visibility` is create-only); no auth state either ⇒ N/A. |
| 9.2 Profile management subcommands exist | na | — | Ft | No profiles (9.1 N/A) ⇒ N/A. |
| 9.3 `--profile` persistent root flag + precedence | na | — | C | No profiles ⇒ N/A. |
| 9.4 Profiles surfaced in machine introspection | na | — | C | No profiles / 7.1 absent ⇒ N/A. |
| 9.5 Stable, documented storage location | na | — | C | No profiles ⇒ N/A. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists (`feedback <text>` recorded locally) | fail | B | Ft | No `feedback` command writing local JSONL; absence ⇒ FAIL@B. |
| 10.2 Feedback can POST upstream when configured, discoverable | na | — | C | 10.1 fails ⇒ N/A. |
| 10.3 Artifact-producing commands support `--deliver` | na | — | Ft | No artifact-producing commands (output is JSON data, not files/reports) ⇒ N/A. |
| 10.4 File sinks write atomically; unknown schemes structured refusal | na | — | C | No `--deliver` ⇒ N/A. |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | na | — | C | Depends on 7.1 (absent) ⇒ N/A. |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- 7.6 (Blocker) — Restore help at every level: replace the hand-rolled command lookup + `add_help=False`/`parse_known_args` parsers with real argparse subparsers (default `add_help`, `parse_args`), or route `-h`/`--help` to usage output (exit 0) *before* dispatching any handler. Localized edit to `main()`.

### Friction (conformance, lower priority)
- (none)

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (Blocker) — Add machine-readable introspection: an `agent-context`/`--schema` command emitting the full command/flag tree as JSON (ideally versioned with `schema_version` and generated from the real parser). Subsystem work; requires your go-ahead.
- 10.1 (Blocker) — Add a `feedback <text>` command that records feedback locally as JSONL (optionally POST upstream when an endpoint is configured). Subsystem work; requires your go-ahead.
- 7.5 (Friction) — Add a `version` command reporting the release version + VCS commit/build date so an agent can detect a stale binary. Requires your go-ahead.
- 6.4 (Target) — Document a naming policy and add a mechanical CI/lint check that enforces the verb/flag vocabulary. Requires your go-ahead.
- 7.3 (Target) — Author a long-form `SKILL.md`-style manifest teaching agent workflows for this CLI. Requires your go-ahead.
