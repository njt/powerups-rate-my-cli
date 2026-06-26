# rate-my-cli rubric

Severity: **B**=Blocker, **F**=Friction, **T**=Target.
Kind: **C**=conformance (localized edit → auto-fixable), **Ft**=feature (subsystem → propose-only).
Absence: resolution when the thing a check looks for is absent — PASS, N/A, or FAIL@severity.
Detection: how to confirm statically. Evaluators read source only; they never run the target CLI.

Verdict per check: `pass | fail | na`. Report every pass-by-absence and every N/A with its
one-line reason. Exclude N/A from the score denominator.

## Tier 1 — Table Stakes

### P1. Non-interactive by default

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 1.1 | No command can block on an interactive prompt without a bypass | B | C | PASS (no prompts ⇒ non-interactive) | Grep prompt calls (`input(`, `readline`, `inquirer`, `prompt(`, `Scanf`, `survey.`, `click.confirm`, `click.prompt`) and check a bypass flag (`--force`/`--yes`/`--no-input`) short-circuits each. |
| 1.2 | TTY detection treats non-TTY stdin as headless (no prompt when not a TTY) | B | C | PASS | Look for `isatty`/`sys.stdin.isatty()`/`process.stdin.isTTY` guarding any prompt; a prompt with no TTY guard fails. |
| 1.3 | A confirmation-bypass flag exists for destructive ops (`--force`/`--yes`) | F | C | N/A (no destructive ops) | Find delete/destroy/prune/reset commands; check each defines `--force`/`--yes`. |
| 1.4 | Interactive menus have a structured flag/file equivalent | F | C | PASS (no menus) | Find select/menu prompts; check a flag/file can supply the value non-interactively. |
| 1.5 | Bypass convention is consistent across subcommands (one flag name) | F | C | N/A (0–1 bypass flag) | Collect all bypass flag names; fail if mixed. |

### P2. Structured, parseable output

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 2.1 | The CLI supports structured (JSON) output | B | C | FAIL@B | Grep for a `--json`/`json.dumps`/`JSON.stringify` path on any data command. |
| 2.2 | Every data-returning command supports `--json` (coverage) | F | C | N/A (none support it ⇒ 2.1 fails) | Count data commands vs those wiring `--json`. |
| 2.3 | One consistent flag name (`--json`, not mixed `--format`/`--output`) | F | C | N/A | Grep flag names: fail if `--format`/`--output`/`-o json` coexist with `--json`. |
| 2.4 | Exit codes: 0 success, non-zero failure, stable taxonomy | F | C | FAIL@B if always 0 on failure | Inspect exit paths (`sys.exit`/`os.Exit`/`process.exit`): fail@B if all exits are 0 even on failure. |
| 2.5 | Data → stdout, diagnostics/errors → stderr | F | C | — | Data prints to stdout and errors/logs to stderr (`sys.stderr`, `console.error`, `fmt.Fprintln(os.Stderr,...)`). |
| 2.6 | ANSI/color suppressed when output isn't a terminal | F | C | — | Color libs (`colorama`, `chalk`, ANSI escapes) guarded by isatty/`NO_COLOR`. |

### P3. Errors that teach, and enumerate

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 3.1 | Failures produce a clear message (not silent, not a bare stack trace) | B | C | — | Error paths print a message (not bare traceback/`panic`). |
| 3.2 | Input validated early, before side effects | F | C | — | Validation occurs before any write/network side effect in the handler. |
| 3.3 | Enum/choice rejections enumerate the valid set | F | C | N/A (no enum inputs) | Enum/choices rejections include the allowed set (look at `choices=` / switch defaults). |
| 3.4 | Errors include corrective guidance (valid invocation / example) | F | C | — | Error text includes a corrective example/usage. |

### P4. Safe retries & explicit mutation boundaries

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 4.1 | Create operations are idempotent (idempotency token or natural key) | B | Ft | N/A (no create ops; often upstream's responsibility) | Create handlers accept an idempotency key or use a natural key (often N/A when create is the upstream API's job). |
| 4.2 | Destructive operations require an explicit, non-default flag | B | C | N/A (no destructive ops) | Destructive handlers require a non-default flag before acting. |
| 4.3 | Consequential operations support `--dry-run` | F | C | N/A | Consequential handlers honor `--dry-run`. |
| 4.4 | Mutation responses return the affected identifier(s) | F | C | N/A (no mutations) | Mutation responses include the affected id. |

### P5. Bounded responses

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 5.1 | List-style commands have a bounded default (limit/page size) | B | C | N/A (no list commands) | List handlers apply a default limit/page size. |
| 5.2 | List commands support filtering and pagination/cursor | F | Ft | N/A | List handlers accept filter + cursor/page. |
| 5.3 | Truncated output signals truncation and hints how to narrow | F | C | N/A | Truncated responses set a `truncated` flag + narrowing hint. |
| 5.4 | MCP wrapper: each tool description fits a small audited token budget | T | C | N/A (no MCP wrapper) | If an MCP server/tool-description surface exists, each description is short and budget-audited (else N/A). |

## Tier 2 — Compounding

### P6. Cross-CLI vocabulary consistency

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 6.1 | Verbs follow universal conventions (`get` not `info`, `list` not `ls`) | B | C | — | Scan command/verb names for banned verbs (`info`,`ls`,`rm`,`new`,`show` where `get`/`list`/`delete`/`create` is conventional). |
| 6.2 | Flags follow conventions (`--force` not `--skip-confirmations`, `--json` not `--format=json`) | B | C | — | Scan flag names for `--skip-*`, `--format=json`, `--no-confirm` aliases. |
| 6.3 | Naming is internally consistent across subcommands | F | C | — | Compare naming across subcommands for internal drift. |
| 6.4 | Documented naming policy + mechanical check (CI/lint) enforces vocabulary | T | Ft | FAIL@T | Look for a documented naming policy + a CI/lint check enforcing it. |

### P7. Three-layer introspection

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 7.1 | Machine-readable introspection exists (`agent-context`-style command/flag schema) | B | Ft | FAIL@B | Look for a machine introspection command (`agent-context`, `--schema`, `dump-schema`) emitting structured command/flag JSON. |
| 7.2 | The machine introspection is versioned (`schema_version`) | F | C | N/A (7.1 fails) | That output carries a `schema_version`. |
| 7.3 | A long-form skill manifest (`SKILL.md`-style) teaches workflows | T | Ft | FAIL@T | A long-form `SKILL.md`/skills dir teaches workflows. |
| 7.4 | Introspection is generated/validated against the real implementation (in sync) | T | Ft | N/A (7.1 fails) | Introspection is generated from / validated against the real command tree (codegen, test). |

(Note: `--help` for humans is assumed present; its absence falls out of 7.1's "only `--help`, nothing structured" Blocker framing.)

### P8. Async-aware execution — *entire principle N/A if the CLI wraps no async API*

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 8.1 | Async-submitting commands offer `--wait` (block until done) | B | Ft | N/A (no async API) | Async-submitting commands (return a job id / `status: queued`) offer `--wait`. |
| 8.2 | The poll loop uses exponential backoff + jitter | F | C | N/A (no poll loop / 8.1 absent) | Poll loop uses exponential backoff + jitter. |
| 8.3 | A persistent job ledger records jobs across invocations | F | Ft | N/A | A persistent job ledger file is written. |
| 8.4 | A `jobs` command exposes `list`/`get`/`prune` over the ledger | F | Ft | N/A | A `jobs` command exposes `list`/`get`/`prune`. |

### P9. Persistent identity through profiles — *covers a recurring **non-auth** config bundle, not auth. Auth/credentials handled upstream or via env are out of scope.*

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 9.1 | If commands force re-specifying a recurring non-auth config bundle, the CLI can persist & reuse it (profiles / named config) | B | Ft | N/A (auth-only state, or no recurring non-auth config) | Detect a recurring NON-AUTH flag cluster across commands with no persistence (profiles/named config); N/A if only auth/credentials persist or there's no recurring non-auth config. |
| 9.2 | Profile management subcommands exist (`save`/`use`/`list`/`show`/`delete`) | F | Ft | N/A (no profiles / 9.1 N/A) | `profile save/use/list/show/delete` subcommands. |
| 9.3 | `--profile` is a persistent root flag; precedence flag > env > profile > default | F | C | N/A (no profiles) | `--profile` root flag + precedence flag>env>profile>default. |
| 9.4 | Profiles surfaced in machine introspection (`agent-context`) | F | C | N/A (no profiles / 7.1 absent) | Profiles appear in machine introspection. |
| 9.5 | Stable, documented storage location (`~/.<cli>/`) | F | C | N/A (no profiles) | Stable documented storage path. |

### P10. Two-way I/O

| id | Assertion | Sev | Kind | Absence | Detection |
|----|-----------|-----|------|---------|-----------|
| 10.1 | A feedback channel exists (`feedback <text>` recorded locally) | B | Ft | FAIL@B | A `feedback <text>` command writing local JSONL. |
| 10.2 | Feedback can POST upstream when configured, and that's discoverable | F | C | N/A (10.1 fails) | Optional upstream POST gated on a configured endpoint, discoverable. |
| 10.3 | Artifact-producing commands support `--deliver` (stdout/file/webhook) | F | Ft | N/A (no artifacts produced) | Artifact-producing commands support `--deliver` (stdout/file/webhook). |
| 10.4 | File sinks write atomically; unknown schemes get a structured refusal | F | C | N/A (no `--deliver`) | File sinks write atomically + unknown schemes get a structured refusal. |
| 10.5 | `--deliver` + `feedback` surfaced in machine introspection | T | C | N/A (depends on 7.1) | Deliver+feedback appear in machine introspection. |
