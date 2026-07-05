# CLI Agent-Nativeness Scorecard

**Target:** ~/Source/azdo
**Date:** 2026-07-05
**Score:** 15 / 29 applicable checks (52%)
**Failing gaps:** 7 Blocker · 5 Friction · 2 Target
**Suspicious-N/A warning:** P8 (Async-aware execution) is entirely N/A — azdo wraps only synchronous Azure DevOps REST calls, so no command submits async work. This is expected for this target, not a hidden gap.

<!-- Roll-up arithmetic (recomputed from the body tables):
  pass = 15, fail = 14, na = 16, total = 45.
  applicable = pass + fail = 29. score = 15/29 = 51.7% ≈ 52%.
  failing by severity: Blocker = 7 (1.1, 1.2, 4.2, 5.1, 7.1, 9.1, 10.1),
                       Friction = 5 (1.3, 3.2, 4.3, 5.2, 5.3),
                       Target = 2 (6.4, 7.3).  7+5+2 = 14 fails. ✓ -->

## Recon summary

- **Framework:** Go + cobra (`cmd/azdo/main.go` → `internal/cmd/root.go`). Persistent root flags: `--org/-O`, `--project/-P`, `--repo/-R`, `--json`, `--no-prompt` (`root.go:31-35`).
- **Command tree:** `auth` (login/logout/status/token), `pr` (18 subcommands), `repo` (list/view/clone/browse/create), `branch` (list/view/browse), `workitem` (list/view/create/edit/close/reopen/comment/browse), `search` (code/workitems), `config` (get/set/list), `alias` (set/list/delete), `browse`, `api`, `completion`, `version`.
- **Output:** single `output.Printer` (`internal/output/format.go`), `--json` root flag, human/table/JSON formats; data→stdout, errors→stderr.
- **Errors:** `fmt.Errorf` returned from `RunE`, printed to stderr and `os.Exit(1)` by `Execute()` (`root.go:84-88`); `APIError` wraps HTTP status/message (`internal/api/errors.go`).
- **Config/auth:** non-auth config in `~/.config/azdo/config.yaml` (`internal/config/config.go`); context (org/project/repo) resolved flag > config default > git-remote autodetect (`internal/config/context.go`). Auth PAT stored in OS keyring or `AZDO_TOKEN` env (`internal/auth/`). **Auth state is out of P9 scope.**
- **Thin wrapper?** Yes — mostly a synchronous REST wrapper over Azure DevOps (`internal/api/`). No async/jobs, **no MCP wrapper, no codegen/schema, no feedback channel, no `--deliver`, no `--dry-run`** anywhere (confirmed by tree-wide grep).

## Per-principle results

### P1. Non-interactive by default

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 1.1 No command blocks on an interactive prompt without a bypass | fail | B | C | `pr comment` has a prompt with no bypass (see 1.2). `pr create`'s title prompt does gate on `!noPrompt` (`pr.go:333`) and `auth login` honors `--no-prompt`, but `pr comment` does not, so at least one prompt is unbypassable. |
| 1.2 TTY detection treats non-TTY stdin as headless | fail | B | C | `pr comment` reads stdin via `bufio.NewReader(os.Stdin)` with **no isatty guard and no `--no-prompt` check** (`pr.go:601-606`); under an agent with a non-TTY stdin it blocks. Contrast `auth`, which does check TTY (`internal/auth/auth.go:52-53`, `isTerminal`). |
| 1.3 Confirmation-bypass flag for destructive ops | fail | F | C | Destructive ops define no `--force`/`--yes`: `pr close` (`pr.go:409`), `pr merge`/`--delete-branch` (`pr.go:461`), `workitem close` (`workitem.go:259`), `alias delete` (`alias.go:65`). |
| 1.4 Interactive menus have a structured flag/file equivalent | pass | | C | No select/menu prompts exist; the only prompts are free-text (title, comment), each with a flag/arg equivalent (`--title`, `pr comment <id> <body>`). Pass by absence of menus. |
| 1.5 Bypass convention consistent (one flag name) | pass | | C | Exactly one bypass flag: `--no-prompt` (root, `root.go:35`). Single name ⇒ consistent. |

### P2. Structured, parseable output

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 2.1 CLI supports structured (JSON) output | pass | | C | `--json` persistent root flag (`root.go:34`); `printJSON` (`format.go:52-63`). |
| 2.2 Every data-returning command supports `--json` | pass | | C | `--json` is inherited by all commands; each data handler branches on `FormatJSON` (`pr.go:221`, `repo.go:112`, `workitem.go:134`, `branch.go:60`, `search.go:86`). `api` always emits JSON (`api.go:57-64`). |
| 2.3 One consistent flag name (`--json`) | pass | | C | Only `--json`; no competing `--format`/`--output`/`-o json`. (`search --top` is a result cap, not an output selector.) |
| 2.4 Exit codes: 0 success, non-zero failure | pass | | C | `RunE` errors bubble to `Execute()` which prints to stderr and `os.Exit(1)` (`root.go:84-88`). Not always-0. |
| 2.5 Data → stdout, diagnostics/errors → stderr | pass | | C | JSON/data → stdout (`Printer.Out=os.Stdout`, `format.go:30`); errors → stderr (`root.go:86`; `Printer.Error`/`Warning` use `ErrOut`, `format.go:97-105`). `Success` prints to stdout (`format.go:92-95`) but is suppressed under `--json` (the JSON object is emitted instead), so machine output stays clean. |
| 2.6 ANSI/color suppressed when output isn't a terminal | pass | | C | `NO_COLOR` honored (`color.go:22-24`); `github.com/fatih/color v1.18.0` (go.mod) auto-sets `NoColor` when stdout is not a TTY via its internal isatty check. |

### P3. Errors that teach, and enumerate

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 3.1 Failures produce a clear message (not silent, not a bare stack) | pass | | C | Errors surface as messages via cobra + `Execute` (`root.go:86`); `APIError.Error()` formats status+message (`api/errors.go:14-19`). No `panic` in command paths. |
| 3.2 Input validated early, before side effects | fail | F | C | `pr create` runs side effects — `git rev-parse` and a `GetRepository` network call (`pr.go:319-332`) — **before** validating that a title exists (`pr.go:339`). A titleless `--no-prompt` invocation does I/O then fails. |
| 3.3 Enum/choice rejections enumerate the valid set | pass | | C | `pr review` with no vote flag lists every valid choice (`pr.go:525`). Flag help enumerates allowed state/status values (`pr.go:142,184,188`). |
| 3.4 Errors include corrective guidance | pass | | C | Not-logged-in error prints the exact fix command (`repo.go:81`: "Run: azdo auth login --org %s"); no-org error names the flag + config key (`repo.go:76`). |

### P4. Safe retries & explicit mutation boundaries

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 4.1 Create ops idempotent (idempotency token / natural key) | na | | Ft | Create handlers (`pr create`, `repo create`, `workitem create`) pass straight to the Azure DevOps REST API with no idempotency layer; idempotency is upstream's responsibility. N/A per Absence rule. |
| 4.2 Destructive ops require an explicit non-default flag | fail | B | C | `pr close`/abandon (`pr.go:409`), `workitem close` (`workitem.go:259`), and `alias delete` (`alias.go:65`) mutate on a bare positional id with no confirming flag. `pr merge --delete-branch` does gate branch deletion behind a non-default flag (`pr.go:169,475`), but the abandon/close/delete paths do not. |
| 4.3 Consequential ops support `--dry-run` | fail | F | C | No `--dry-run` flag anywhere (tree-wide grep: 0 hits), despite consequential ops (`pr merge`, `pr close`, `workitem close`, `repo create`). |
| 4.4 Mutation responses return affected identifier(s) | pass | | C | Every mutation echoes the id: `pr create`→"#%d" (`pr.go:373`), `pr merge`→id (`pr.go:490`), `workitem create`→"#%d" (`workitem.go:215`); JSON paths return the full object incl. id. |

### P5. Bounded responses

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 5.1 List commands have a bounded default | fail | B | C | `repo list` (`repo.go:96` → `ListRepositories`, `api/git.go:11` — no `$top`) and `branch list` (`branch.go:44` → `ListBranches`/`ListBranchStats` — no `$top`) return the full server set with **no limit**. `pr list` (30), `workitem list` (30), and `search` (100) are bounded; the two unbounded lists fail. |
| 5.2 List commands support filtering and pagination/cursor | fail | F | Ft | Filtering is present (`pr list` state/author/reviewer/base `pr.go:142-145`; `workitem list` type/state/assignee). But **no pagination/cursor** — Azure DevOps `continuationToken` is never read or exposed (grep: 0 hits); `--limit` caps only the first page. |
| 5.3 Truncated output signals truncation + narrowing hint | fail | F | C | A list capped at its default limit emits no `truncated` flag or narrowing hint (e.g. `pr.go:224-233` prints rows and stops silently); callers cannot distinguish a full 30-row result from a truncated one. |
| 5.4 MCP wrapper: tool descriptions within token budget | na | | C | No MCP server or tool-description surface (grep `mcp`: 0 hits). N/A. |

### P6. Cross-CLI vocabulary consistency

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 6.1 Verbs follow universal conventions | pass | | C | Conventional verbs: `list`, `view`, `create`, `edit`, `close`, `delete`, `merge`, `clone`. No banned `info`/`ls`/`rm`/`new`. `view` is used consistently (mirrors the `gh` convention the tool targets, `requirements.md:3`), with no drift toward `get`/`show`. |
| 6.2 Flags follow conventions | pass | | C | `--json` (not `--format=json`), `--limit`, `--web`, `--draft`, `--body-file`; no `--skip-*`/`--no-confirm`. `--no-prompt` is a recognized convention. |
| 6.3 Naming internally consistent across subcommands | pass | | C | Consistent verb/flag set across `pr`/`repo`/`workitem`/`branch`. Minor nit: `search` uses `--top`/`-n` for its cap while lists use `--limit`/`-L` (`search.go:64` vs `pr.go:146`) — small drift, not systemic ⇒ still pass. |
| 6.4 Documented naming policy + mechanical (CI/lint) check | fail | T | Ft | `requirements.md` states a philosophy ("mirror gh") but there is no documented allowed-verb/flag policy and **no CI/lint check** enforcing vocabulary (Makefile is build/test only). Absence → fail@T. |

### P7. Three-layer introspection

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 7.1 Machine-readable introspection exists | fail | B | Ft | Only cobra `--help` and shell `completion` (`root.go:50-81`). No `agent-context`/`--schema`/`dump-schema` emitting structured command/flag JSON (grep: 0 hits). Absence → fail@B. |
| 7.2 Machine introspection is versioned (`schema_version`) | na | | C | N/A — 7.1 fails, nothing to version. |
| 7.3 Long-form skill manifest (`SKILL.md`-style) | fail | T | Ft | No `SKILL.md` or skills dir teaching agent workflows; `docs/` holds design/impl plans and `requirements.md` is a human spec. Absence → fail@T. |
| 7.4 Introspection generated/validated against real implementation | na | | Ft | N/A — 7.1 fails, no introspection surface to keep in sync. |

### P8. Async-aware execution — *entire principle N/A*

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 8.1 Async-submitting commands offer `--wait` | na | | Ft | No command returns a job id / `status: queued`; `pr merge` completes synchronously via PATCH (`api/git.go:218`). `pr review --wait` is a *vote value* (−5, "waiting for author", `pr.go:174,518`), not async polling. N/A. |
| 8.2 Poll loop uses exponential backoff + jitter | na | | C | No poll loop. N/A. |
| 8.3 Persistent job ledger | na | | Ft | No async jobs. N/A. |
| 8.4 `jobs` command (`list`/`get`/`prune`) | na | | Ft | No async subsystem. N/A. |

### P9. Persistent identity through profiles (non-auth config bundle)

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 9.1 Persist & reuse a recurring non-auth config bundle | fail | B | Ft | The recurring **non-auth** cluster `--org`/`--project`/`--repo` threads through nearly every command (`root.go:31-33`). It can be defaulted globally (`default_org`/`default_project` in `config.yaml`, `config.go:11-13`) and autodetected from the git remote (`context.go:73-101`), but there is **no named-profile mechanism** to switch between multiple org/project bundles — only a single global default. Users juggling multiple projects must re-specify the bundle. Fail@B (non-auth config; keyring auth is out of scope). |
| 9.2 Profile management subcommands | na | | Ft | N/A — no profile system (9.1's gap). `config get/set/list` manages single scalar defaults, not named profiles. |
| 9.3 `--profile` root flag + precedence | na | | C | N/A — no `--profile` flag. (Flag>config>git-detect precedence *is* implemented for org/project in `context.go:73-101`, but there is no profile layer.) |
| 9.4 Profiles surfaced in machine introspection | na | | C | N/A — no profiles and no machine introspection (7.1 fails). |
| 9.5 Stable documented storage location | na | | C | N/A per the profile framing. (Config does have a stable documented path `~/.config/azdo/config.yaml`, `config.go:56-73`, `requirements.md:43` — but with no profiles, the profile-storage assertion is N/A.) |

### P10. Two-way I/O

| Check | Verdict | Sev | Kind | Evidence |
|-------|---------|-----|------|----------|
| 10.1 Feedback channel exists (`feedback <text>`) | fail | B | Ft | No `feedback` command and no local JSONL sink (grep `feedback`: 0 hits). Absence → fail@B. |
| 10.2 Feedback can POST upstream when configured | na | | C | N/A per Absence rule (10.1 fails). |
| 10.3 Artifact-producing commands support `--deliver` | na | | Ft | No command produces a deliverable artifact beyond printing to stdout (`pr diff` shells to `git diff`→stdout, `pr.go:743-749`). N/A. |
| 10.4 File sinks write atomically; unknown schemes refused | na | | C | N/A — no `--deliver`/file-sink mechanism. (Config `Save` uses `os.WriteFile`, `config.go:111`, but that is internal config, not a deliver sink.) |
| 10.5 `--deliver` + `feedback` in machine introspection | na | | C | N/A — neither exists, and there is no machine introspection (7.1 fails). |

## Remediation plan

### Auto-fixable now (failing `conformance` checks, Blockers first)

- [ ] **1.2 / 1.1 (B)** — In `pr comment`, guard the stdin prompt with a TTY + `--no-prompt` check like `auth` does; if stdin is not a terminal (or `--no-prompt`) and no `<body>` arg is given, return `fmt.Errorf("comment body is required")` instead of blocking on `bufio.NewReader(os.Stdin).ReadString`. (`internal/cmd/pr.go:601-606`)
- [ ] **5.1 (B)** — Add a `--limit` (default e.g. 30) to `repo list` and `branch list` and thread `$top` through `ListRepositories`/`ListBranches`/`ListBranchStats`. (`internal/cmd/repo.go:96`, `internal/cmd/branch.go:44`, `internal/api/git.go:11,50,64`)
- [ ] **4.2 (B)** — Require a `--force`/`--yes` (or confirm-with-bypass) on `pr close`, `workitem close`, `alias delete` so a destructive action needs an explicit non-default signal. (`internal/cmd/pr.go:409`, `internal/cmd/workitem.go:259`, `internal/cmd/alias.go:65`)
- [ ] **1.3 (F)** — Reuse that same `--force`/`--yes` flag name consistently across all destructive ops.
- [ ] **3.2 (F)** — In `pr create`, validate required inputs (title unless prompting) **before** the `git rev-parse`/`GetRepository` side effects. (`internal/cmd/pr.go:319-341`)
- [ ] **4.3 (F)** — Add `--dry-run` to consequential handlers (`pr merge`, `pr close`, `workitem close`, `repo create`) that prints the resolved intended action and returns without calling the API.
- [ ] **5.3 (F)** — When a list returns exactly `limit` rows, emit `truncated: true` (JSON) + a stderr narrowing hint. (`internal/cmd/pr.go:224`, `workitem.go:138`, etc.)
- [ ] **Dead `--top` flag (conformance nit)** — `search code`/`search workitems` declare `--top`/`-n` (`search.go:64-65`) but the handlers call `SearchCode`/`SearchWorkItems`, which hardcode `Top: 100` and ignore the flag (`api/search.go:114-128,146-161`). Route through `SearchCodeWithOptions`/`SearchWorkItemsWithOptions`, which already honor it.

### Friction (conformance, lower priority)

- [ ] **6.3 nit** — Unify the result-cap flag name: `search` uses `--top`/`-n`, lists use `--limit`/`-L`. Pick one (`--limit`).

### Proposals — features, not auto-built (failing `feature` checks, by severity)

- **7.1 (B) machine introspection** — Add an `agent-context` (or `--schema`) command that walks the cobra tree and emits structured JSON of commands/flags/args/enum-choices. Foundational for 7.2/7.4/9.4/10.5. Requires your go-ahead.
- **9.1 (B) profiles** — Add a named-profile system for the recurring `--org`/`--project`/`--repo` bundle (`profile save/use/list/show/delete`, a `--profile` root flag with flag>env>profile>git>default precedence, stored under `~/.config/azdo/`). Auth stays in the keyring. Requires your go-ahead.
- **10.1 (B) feedback channel** — Add a `feedback <text>` command appending JSONL to `~/.config/azdo/feedback.jsonl`, with an optional configured upstream POST (10.2). Requires your go-ahead.
- **6.4 (T) naming policy + CI check** — Document an allowed verb/flag vocabulary and add a lint/test that fails CI on off-convention names. Requires your go-ahead.
- **7.3 (T) skill manifest** — Author a long-form `SKILL.md` teaching agent workflows (auth → context resolution → PR lifecycle → work items). Requires your go-ahead.
- **5.2 pagination (Ft)** — Read/expose Azure DevOps `continuationToken` for true cursor pagination beyond the first page. Requires your go-ahead.
