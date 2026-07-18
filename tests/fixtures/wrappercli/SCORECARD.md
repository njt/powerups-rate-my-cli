# CLI Agent-Nativeness Scorecard

**Target:** tests/fixtures/wrappercli/wrappercli.py
**Date:** 2026-06-26
**Score:** 18 / 25 applicable checks (72%)
**Failing gaps:** 2 Blocker · 2 Friction · 3 Target

> ⚠️ **Suspicious N/A warning:** Principles **P8** (Async-aware execution) and **P9** (Persistent identity through profiles) returned **entirely N/A**. P8 is N/A because the wrapper submits no async jobs. P9 is N/A because the only persistent state is auth (`UPSTREAM_TOKEN` via env) and there is no recurring non-auth config bundle — confirm this is genuinely a thin per-call wrapper and not a missed profile surface.

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command can block on an interactive prompt without a bypass | pass | — | C | Pass by absence: no `input(`/`prompt`/`confirm`/`Scanf` anywhere; both handlers run unattended (wrappercli.py:13-17). |
| 1.2 TTY detection treats non-TTY stdin as headless | pass | — | C | Pass by absence: no prompts exist, so no missing TTY guard. |
| 1.3 A confirmation-bypass flag exists for destructive ops | na | — | C | N/A: no destructive ops (only `get`/`list`). |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | — | C | Pass by absence: no menus/select prompts. |
| 1.5 Bypass convention consistent across subcommands | na | — | C | N/A: 0 bypass flags present. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 The CLI supports structured (JSON) output | pass | — | C | `print(json.dumps(...))` in both handlers (wrappercli.py:14,17); `--json` flag declared (wrappercli.py:22-23). |
| 2.2 Every data-returning command supports `--json` | pass | — | C | Both data commands (`get`, `list`) declare `--json` (wrappercli.py:22-23). |
| 2.3 One consistent flag name (`--json`) | pass | — | C | Only `--json` used; no `--format`/`--output`/`-o` aliases. |
| 2.4 Exit codes: 0 success, non-zero failure, stable taxonomy | pass | — | C | Auth failure exits `2` (wrappercli.py:11); argparse exits non-zero on parse errors; success path exits 0. Not always-0-on-failure. |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | — | C | Data via `print(...)` → stdout; auth error → `file=sys.stderr` (wrappercli.py:9). |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | — | C | Pass by absence: no color libs / ANSI escapes emitted. |
| 2.7 Structured output never emits raw secrets (tokens/JWTs/passwords) | pass | — | C | JSON payloads carry only `id`/`title`/`items`/`truncated` (wrappercli.py:14,17); `UPSTREAM_TOKEN` stays in the env and is never placed into a `json.dumps` field — no `*token*`/`*jwt*`/`*secret*`/`*password*`/`*key*` field reaches the encoder. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent, not bare stack trace) | pass | — | C | Auth error prints a clear message, not a traceback (wrappercli.py:9-11). |
| 3.2 Input validated early, before side effects | pass | — | C | `_client()` checks token before any output/side effect in each handler (wrappercli.py:14,17). |
| 3.3 Enum/choice rejections enumerate the valid set | na | — | C | N/A: no enum/`choices=` inputs. |
| 3.4 Errors include corrective guidance (valid invocation / example) | pass | — | C | Auth error includes corrective guidance: "get one at https://upstream.example/tokens" (wrappercli.py:9). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create operations are idempotent | na | — | Ft | N/A: no create ops; create would be the upstream API's responsibility. |
| 4.2 Destructive operations require an explicit non-default flag | na | — | C | N/A: no destructive ops. |
| 4.3 Consequential operations support `--dry-run` | na | — | C | N/A: no consequential/mutating ops. |
| 4.4 Mutation responses return the affected identifier(s) | na | — | C | N/A: no mutations. |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List-style commands have a bounded default | pass | — | C | `list` defines `--limit` default 20 (wrappercli.py:23). |
| 5.2 List commands support filtering and pagination/cursor | fail | T | Ft | No filter flag and no cursor/page; `list` only has `--limit` (wrappercli.py:23). |
| 5.3 Truncated output signals truncation and hints how to narrow | fail | F | C | Response carries a `truncated` field but it is hardcoded `False` with no narrowing hint and no logic setting it (wrappercli.py:17). |
| 5.4 MCP wrapper: each tool description fits a small audited token budget | na | — | C | N/A: no MCP wrapper/server. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions (`get`, `list`) | pass | — | C | Commands are `get` and `list` — canonical verbs, no banned `info`/`ls`/`show` (wrappercli.py:22-23). |
| 6.2 Flags follow conventions | pass | — | C | Flags `--json`, `--limit`, `--id` positional — no `--skip-*`/`--format=json`/`--no-confirm` (wrappercli.py:22-23). |
| 6.3 Naming is internally consistent across subcommands | pass | — | C | `--json` named identically on both subcommands; consistent style. |
| 6.4 Documented naming policy + mechanical check (CI/lint) | fail | T | Ft | No naming-policy doc and no CI/lint check enforcing vocabulary. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists | fail | B | Ft | Only argparse `--help`; no `agent-context`/`--schema`/`dump-schema` emitting command/flag JSON. |
| 7.2 Machine introspection is versioned (`schema_version`) | na | — | C | N/A: 7.1 fails (no machine introspection). |
| 7.3 Long-form skill manifest teaches workflows | fail | T | Ft | No `SKILL.md`/skills dir teaching workflows for this CLI. |
| 7.4 Introspection generated/validated against real implementation | na | — | Ft | N/A: 7.1 fails (no introspection to keep in sync). |
| 7.5 A `version` command reports the build (version + commit/date) | fail | F | Ft | No `version` command / `--version` surface; only `get`/`list` are registered (wrappercli.py:22-23) ⇒ absent ⇒ FAIL@F. |
| 7.6 `--help`/`-h` at every level prints usage, exits 0, never executes the action | pass | — | C | argparse default `add_help` at root and both `add_parser` subcommands (wrappercli.py:20-23); no `add_help=False`; help dispatches before any handler and exits 0. |

### P8. Async-aware execution

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | — | Ft | N/A: wrapper submits no async jobs (no job id / `status: queued`). |
| 8.2 Poll loop uses exponential backoff + jitter | na | — | C | N/A: no async API / no poll loop. |
| 8.3 Persistent job ledger records jobs across invocations | na | — | Ft | N/A: no async API. |
| 8.4 A `jobs` command exposes `list`/`get`/`prune` | na | — | Ft | N/A: no async API. |

### P9. Persistent identity through profiles

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | na | — | Ft | N/A: only persistent state is auth (`UPSTREAM_TOKEN` via env); no recurring NON-AUTH flag cluster across commands. Auth is explicitly out of P9 scope. |
| 9.2 Profile management subcommands exist | na | — | Ft | N/A: no profiles / 9.1 N/A. |
| 9.3 `--profile` root flag + precedence flag>env>profile>default | na | — | C | N/A: no profiles. |
| 9.4 Profiles surfaced in machine introspection | na | — | C | N/A: no profiles / 7.1 absent. |
| 9.5 Stable, documented storage location | na | — | C | N/A: no profiles. |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 A feedback channel exists (`feedback <text>` recorded locally) | fail | B | Ft | No `feedback` command; nothing writes local JSONL. |
| 10.2 Feedback can POST upstream when configured, discoverable | na | — | C | N/A: 10.1 fails. |
| 10.3 Artifact-producing commands support `--deliver` | na | — | Ft | N/A: no artifact-producing commands (only JSON to stdout). |
| 10.4 File sinks write atomically; unknown schemes get structured refusal | na | — | C | N/A: no `--deliver`. |
| 10.5 `--deliver` + `feedback` surfaced in machine introspection | na | — | C | N/A: depends on 7.1 (absent) and on 10.1/10.3 (absent). |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)
- [ ] 5.3 — Make `truncated` meaningful: set it from real result-vs-limit comparison and, when true, include a narrowing hint (e.g. "use --limit / a filter"). (wrappercli.py:17)

### Friction (conformance, lower priority)
- [ ] (none — 5.3 above is the only failing conformance check)

### Proposals — features, not auto-built (failing `feature` checks)
- 7.1 (Blocker) — Add a machine introspection surface (`agent-context`/`--schema`) emitting the command/flag tree as JSON; requires your go-ahead.
- 10.1 (Blocker) — Add a `feedback <text>` command writing local JSONL; requires your go-ahead.
- 5.2 (Target) — Add filtering + cursor/page pagination to `list`; requires your go-ahead.
- 6.4 (Target) — Add a documented naming policy plus a CI/lint check enforcing the vocabulary; requires your go-ahead.
- 7.3 (Target) — Author a long-form `SKILL.md` teaching agent workflows for this CLI; requires your go-ahead.
- 7.5 (Friction) — Add a `version` command reporting the release version + VCS commit/build date so an agent can detect a stale binary; requires your go-ahead.
