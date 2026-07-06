# CLI Agent-Nativeness Scorecard

**Target:** tests/fixtures/badcli/badcli.py
**Date:** 2026-06-26
**Score:** 6 / 25 applicable checks (24%)
**Failing gaps:** 9 Blocker · 8 Friction · 2 Target
**Suspicious N/A warning:** Principles P8 (Async-aware execution) and P9 (Persistent identity through profiles) returned entirely N/A — verify these subsystems are genuinely absent rather than missed.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command can block on an interactive prompt without a bypass | fail | B | C | badcli.py:14 `input(...)` in cmd_delete, no `--force`/`--yes`/`--no-input` bypass |
| 1.2 TTY detection treats non-TTY stdin as headless | fail | B | C | badcli.py:14 prompt has no `isatty`/`sys.stdin.isatty()` guard |
| 1.3 A confirmation-bypass flag exists for destructive ops | fail | F | C | badcli.py:12-16 `delete` is destructive, defines no `--force`/`--yes` |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | | C | No select/menu prompts present (only a y/N confirm) — pass by absence |
| 1.5 Bypass convention is consistent across subcommands | na | | C | 0 bypass flags exist ⇒ N/A |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 The CLI supports structured (JSON) output | fail | B | C | No `--json`/`json.dumps` anywhere; all output is `print()` (badcli.py:6,9-10,21) |
| 2.2 Every data-returning command supports `--json` | na | | C | None support `--json` ⇒ 2.1 fails ⇒ N/A |
| 2.3 One consistent flag name (`--json`) | na | | C | No structured-output flags exist at all ⇒ N/A |
| 2.4 Exit codes: 0 success, non-zero failure, stable taxonomy | fail | B | C | badcli.py:21 `sys.exit(0)` on the invalid-visibility failure path |
| 2.5 Data → stdout, diagnostics/errors → stderr | fail | F | C | badcli.py:20 error printed to stdout (`print(...)`), not stderr |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | | C | No color libs / ANSI escapes used — nothing to suppress, pass by absence |
| 2.7 Structured output never emits raw secrets (tokens/JWTs/passwords) | na | | C | No `--json`/structured-output path exists at all (badcli.py all `print()`) ⇒ no encoder that could leak a secret ⇒ N/A |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent, not a bare stack trace) | pass | | C | badcli.py:20 prints "error: invalid visibility" message (not a bare traceback) |
| 3.2 Input validated early, before side effects | pass | | C | badcli.py:19-21 validation precedes the create side effect; no earlier writes |
| 3.3 Enum/choice rejections enumerate the valid set | fail | F | C | badcli.py:20 "error: invalid visibility" does not list the allowed set (public/private) |
| 3.4 Errors include corrective guidance | fail | F | C | badcli.py:20 error gives no corrective example/usage |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent | na | | Ft | badcli.py:18-22 create is a local stub with no idempotency surface; treated as upstream's responsibility ⇒ N/A |
| 4.2 Destructive operations require an explicit, non-default flag | fail | B | C | badcli.py:12-16 `delete` acts after only an interactive y/N; no required non-default flag |
| 4.3 Consequential operations support `--dry-run` | fail | F | C | No `--dry-run` on `delete`/`create` (badcli.py:12,18) |
| 4.4 Mutation responses return the affected identifier(s) | fail | F | C | badcli.py:16 prints "deleted" with no id returned |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default | fail | B | C | badcli.py:9 `ls` loops `range(100)` with no default limit/page size |
| 5.2 List commands support filtering and pagination/cursor | fail | F | Ft | badcli.py:8-10 `ls` accepts no filter or cursor/page args |
| 5.3 Truncated output signals truncation and hints how to narrow | na | | C | `ls` never truncates (emits a fixed range, no limit applied) ⇒ N/A |
| 5.4 MCP wrapper: each tool description fits a small token budget | na | | C | No MCP server/tool-description surface exists ⇒ N/A |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions (`get` not `info`, `list` not `ls`) | fail | B | C | badcli.py:5 `info` (should be `get`); badcli.py:8 `ls` (should be `list`) |
| 6.2 Flags follow conventions | pass | | C | Only `--visibility` exists; no `--skip-*`/`--format=json`/`--no-confirm` aliases — pass by absence |
| 6.3 Naming is internally consistent across subcommands | pass | | C | `--visibility` named identically across info/create; no internal drift |
| 6.4 Documented naming policy + mechanical check enforces vocabulary | fail | T | Ft | No naming policy doc or CI/lint check present ⇒ FAIL@T |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists | fail | B | Ft | No `agent-context`/`--schema`/`dump-schema`; only argparse `--help` ⇒ FAIL@B |
| 7.2 The machine introspection is versioned | na | | C | 7.1 fails ⇒ N/A |
| 7.3 A long-form skill manifest teaches workflows | fail | T | Ft | No SKILL.md/skills dir for the target CLI ⇒ FAIL@T |
| 7.4 Introspection is generated/validated against the real implementation | na | | Ft | 7.1 fails ⇒ N/A |
| 7.5 A `version` command reports the build (version + commit/date) | fail | F | Ft | No `version` command/`--version` surface; argparse defines none (badcli.py:24-31) ⇒ absent ⇒ FAIL@F |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | | Ft | CLI wraps no async API (no job id / queued status) ⇒ N/A |
| 8.2 The poll loop uses exponential backoff + jitter | na | | C | No poll loop / no async API ⇒ N/A |
| 8.3 A persistent job ledger records jobs across invocations | na | | Ft | No async jobs / no ledger ⇒ N/A |
| 8.4 A `jobs` command exposes `list`/`get`/`prune` | na | | Ft | No async jobs ⇒ N/A |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 CLI can persist & reuse a recurring non-auth config bundle | na | | Ft | No recurring non-auth flag cluster across commands; no auth state either ⇒ N/A |
| 9.2 Profile management subcommands exist | na | | Ft | No profiles / 9.1 N/A ⇒ N/A |
| 9.3 `--profile` root flag + precedence | na | | C | No profiles ⇒ N/A |
| 9.4 Profiles surfaced in machine introspection | na | | C | No profiles / 7.1 absent ⇒ N/A |
| 9.5 Stable, documented storage location | na | | C | No profiles ⇒ N/A |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists | fail | B | Ft | No `feedback <text>` command writing local JSONL ⇒ FAIL@B |
| 10.2 Feedback can POST upstream when configured | na | | C | 10.1 fails ⇒ N/A |
| 10.3 Artifact-producing commands support `--deliver` | na | | Ft | No artifact-producing commands (output is console text only) ⇒ N/A |
| 10.4 File sinks write atomically; unknown schemes refused | na | | C | No `--deliver` ⇒ N/A |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | na | | C | No `--deliver`/`feedback`; depends on 7.1 (absent) ⇒ N/A |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 1.1 — Add a `--force`/`--yes` bypass flag that short-circuits the `delete` confirm  (badcli.py:14)
- [ ] 1.2 — Guard the `delete` prompt with `sys.stdin.isatty()`; treat non-TTY as headless  (badcli.py:14)
- [ ] 2.1 — Add a `--json` path emitting `json.dumps(...)` for data commands (`info`, `ls`)  (badcli.py:6,9-10)
- [ ] 2.4 — Return a non-zero exit on the invalid-visibility failure path  (badcli.py:21)
- [ ] 4.2 — Require an explicit non-default `--force` flag before `delete` acts  (badcli.py:12-16)
- [ ] 5.1 — Apply a default limit/page size to `ls`  (badcli.py:9)
- [ ] 6.1 — Rename `info`→`get` and `ls`→`list`  (badcli.py:5,8,27,28)

### Friction (conformance, lower priority)
- [ ] 1.3 — Define `--force`/`--yes` on the destructive `delete` command (badcli.py:12)
- [ ] 2.5 — Route the create error to stderr (`print(..., file=sys.stderr)`) (badcli.py:20)
- [ ] 3.3 — Enumerate the valid set (public, private) in the rejection message (badcli.py:20)
- [ ] 3.4 — Add corrective guidance / a valid-invocation example to the error (badcli.py:20)
- [ ] 4.3 — Add `--dry-run` to `delete` and `create` (badcli.py:12,18)
- [ ] 4.4 — Return the affected id in the `delete` response (badcli.py:16)

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 — Add a machine-readable introspection command (`agent-context`/`--schema`) emitting the command/flag tree as JSON; requires your go-ahead.
- 10.1 — Add a `feedback <text>` command writing local JSONL; requires your go-ahead.
- 5.2 — Add filtering + pagination/cursor to `list`; requires your go-ahead.
- 6.4 — Document a naming policy and add a CI/lint check enforcing the vocabulary; requires your go-ahead.
- 7.3 — Author a long-form SKILL.md manifest teaching workflows; requires your go-ahead.
- 7.5 — Add a `version` command reporting the release version + VCS commit/build date so an agent can detect a stale binary; requires your go-ahead.
